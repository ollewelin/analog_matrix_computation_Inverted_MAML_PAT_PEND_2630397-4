#!/usr/bin/env python3
"""
capture_t120_la_traces.py - Live bare-metal capture from the Efinix Logic Analyzer (la0)
in FPGA_code/T120F324_LA using Efinix's official efx_dbg JtagManager API.
"""

import os
import sys
import math
import time
import json
from pathlib import Path

EFINITY_HOME = Path("/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2")
sys.path.insert(0, str(EFINITY_HOME / "debugger" / "bin"))
sys.path.insert(0, str(EFINITY_HOME / "pgm" / "bin"))
sys.path.insert(0, str(EFINITY_HOME / "lib"))

from efx_dbg.jtag import JtagManager
from efx_dbg.define import DebugProfileBuilder, LogicNCaptureMode
from efx_dbg.util import get_compare_param

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LA_DIR = REPO_ROOT / "FPGA_code" / "T120F324_LA"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
PROFILE_PATH = LA_DIR / "debug_profile.json"


def unpack_sample(bseq, probes_meta):
    """
    Unpack a single BitSequence sample row from LogicNController.read() into a dict of probe values.
    Follows LogicNController.export_vcd() bit ordering:
      seq = repr(bseq)
      end = len(seq)
      for idx, (name, width, _, _) in enumerate(probes):
          value = seq[end - width:end]
          end -= width
    """
    seq = repr(bseq)
    end = len(seq)
    row = {}
    for name, width, _, _ in probes_meta:
        bits_str = seq[end - width : end]
        row[name] = int(bits_str, 2)
        end -= width
    return row


def configure_and_capture(jm, dbg_sesh, spec, core_name, trig_rules, cap_rule=None, trig_pos=128, timeout_s=5.0):
    """
    Configure trigger and capture-enable conditions on la0, run trigger, wait for FULL,
    and read back the 2048-sample hardware trace.
    Pattern codes for 1-bit probes:
      1 = '0' (logical zero)
      2 = '1' (logical one)
      3 = 'X' (don't care)
      4 = 'R' (0-to-1 rising edge)
      5 = 'F' (1-to-0 falling edge)
      6 = 'B' (both edges)
    """
    ctrl = dbg_sesh.get_controller_by_name(core_name)
    with ctrl._engine.get_jtag_engine(ctrl.name) as jtag_engine:
        ctrl.soft_reset(jtag_engine)

    num_probes = len(spec.probes)
    probes_trig_en = [False] * num_probes
    probes_capture_en = [False] * num_probes

    probe_name_to_id = {p.name: idx for idx, p in enumerate(spec.probes)}

    # 1. Configure trigger conditions
    for pname, pttrn, val_str, radix in trig_rules:
        pid = probe_name_to_id[pname]
        pobj = spec.get_probe(pid)
        cmpr, mask = get_compare_param(val_str, radix, pobj.width)
        ctrl.set_probe_regs(
            probe_id=pid,
            pattr={
                "trig_pttrn": pttrn,
                "trig_cmpr": cmpr,
                "trig_mask": mask,
            },
        )
        tid = spec.get_trigger_idx(pid)
        probes_trig_en[tid] = True

    # 2. Configure capture condition (if Basic capture mode)
    if cap_rule is not None:
        pname, pttrn, val_str, radix = cap_rule
        pid = probe_name_to_id[pname]
        pobj = spec.get_probe(pid)
        cmpr, mask = get_compare_param(val_str, radix, pobj.width)
        ctrl.set_probe_capture_regs(
            probe_id=pid,
            pattr={
                "cap_pttn": pttrn,
                "cap_cmpr": cmpr,
                "cap_mask": mask,
            },
        )
        cid = spec.get_capture_idx(pid)
        probes_capture_en[cid] = True

    window_depth = spec.data_depth  # 2048
    num_window = 1

    ctrl.select_probes(probes_trig_en)
    ctrl.enable_capture_condition_probes(probes_capture_en)
    ctrl.set_property("trig_pos", trig_pos)
    ctrl.set_property("tu_pttrn", "AND")
    ctrl.set_property("cu_pttrn", "AND")
    ctrl.set_property("num_window", num_window)
    ctrl.set_property("window_depth", window_depth)
    ctrl.set_trigger_skip_count(1)
    ctrl.set_window_regs(int(math.log2(window_depth)), num_window)

    # Start trigger
    imdt = len(trig_rules) == 0
    ctrl.run_trig(imdt=imdt)

    t0 = time.time()
    last_status = None
    while time.time() - t0 < timeout_s:
        status = ctrl.get_la_status()
        last_status = status
        if status["state"] == "FULL":
            break
        time.sleep(0.02)

    if not last_status or last_status["state"] != "FULL":
        print(f"    [!] Timeout waiting for FULL (last status: {last_status}), resetting core...")
        ctrl.stop_trig()
        with ctrl._engine.get_jtag_engine(ctrl.name) as jtag_engine:
            ctrl.soft_reset(jtag_engine)
        return None, last_status

    capture_buf = ctrl.read()
    return capture_buf, last_status


def main():
    print(f"[*] Loading debug profile: {PROFILE_PATH}")
    profile, warnings = DebugProfileBuilder.from_file(str(PROFILE_PATH))
    if warnings:
        print(f"[!] Profile warnings: {warnings}")

    os.environ.setdefault("EFINITY_USER_DIR", os.path.expanduser("~/.efinity"))
    os.makedirs(os.environ["EFINITY_USER_DIR"], exist_ok=True)

    jm = JtagManager()
    devices = JtagManager.list_usb_devices()
    print(f"[*] Detected USB devices: {devices}")

    url = "ftdi://0x0403:0x6010:1:4/2"
    for vid, pid, sernum, iface, desc in devices:
        if vid == 0x0403 and pid == 0x6010 and sernum:
            url = f"ftdi://0x{vid:04x}:0x{pid:04x}:{sernum}/2"
            break

    print(f"[*] Configuring JTAG session on {url} (USER1, tap=efx, freq=6 MHz)...")
    jtag_sesh = jm.config_jtag(url=url, freq=6e6, tap="efx", user="USER1")
    dbg_sesh = jm.config_debug(jtag_sesh, profile)

    ctrl = dbg_sesh.get_controller_by_name("la0")
    hw_uuid = ctrl.read_uuid()
    spec = profile.get_core_spec("la0")
    exp_uuid = spec.get_uuid()
    print(f"[+] Connected to Efinix Logic Analyzer 'la0'!")
    print(f"    Hardware UUID : {hw_uuid}")
    print(f"    Profile  UUID : {exp_uuid}")
    assert hw_uuid == exp_uuid, f"UUID Mismatch: {hw_uuid} != {exp_uuid}"
    print(f"    UUID Match    : VERIFIED (True)")

    probes_meta = spec.get_probes(trig_en=False)
    out_vcd_dir = LA_DIR / "outflow"
    out_vcd_dir.mkdir(parents=True, exist_ok=True)

    captures_summary = {
        "hw_uuid": hw_uuid,
        "profile_uuid": exp_uuid,
        "data_depth": spec.data_depth,
        "capture_control": spec.capture_control,
        "probes": [{"id": idx, "name": name, "width": width} for name, width, _, idx in probes_meta],
        "traces": {},
    }

    # Seed deterministic Weight Pattern A (+W) and ensure autonomous run_mode = 3 is active
    import socket, struct
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    def udp_cmd(payload):
        for _ in range(5):
            try:
                sock.sendto(payload, ("192.168.1.50", 5000))
                d, _ = sock.recvfrom(4096)
                return d
            except socket.timeout:
                pass
        return None

    # Mode 4 = Seed Pattern A (+W), then set run_mode = 3
    udp_cmd(struct.pack("<IBBH", 0x4D414D4C, 0x19, 4, 0x00FF))
    udp_cmd(struct.pack("<IBBBHBHBbB", 0x4D414D4C, 0x11, 3, 3, 500, 25, 100, 10, 0, 14))
    time.sleep(0.05)

    # Define the 6 bare-metal test captures
    test_configs = [
        {
            "key": "trace1_hadamard_ON_mat3_ce10mhz",
            "title": "Hadamard ON — Weight Pattern A (+W) @ 10 MHz Capture Enable (ce_10mhz_1shot == 1)",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 2, "0", 2),   # '1' (Hadamard ON)
                ("hadamard_mat3_on", 2, "0", 2),    # '1' (Matrix 3 active)
            ],
            "cap_rule": ("ce_10mhz_1shot", 2, "0", 2),  # '1' (10 MHz one-shot -> 204.8 us window)
            "trig_pos": 256,
            "dt_us": 0.10,
        },
        {
            "key": "trace2_hadamard_OFF_tristate_ce10mhz",
            "title": "Hadamard OFF (Tri-State 0x8000) @ 10 MHz Capture Enable (ce_10mhz_1shot == 1)",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 1, "0", 2),   # '0' (Hadamard OFF)
                ("h_step_idx", 1, "0010", 2),       # '== 2' (Confirm still OFF at step 2)
            ],
            "cap_rule": ("ce_10mhz_1shot", 2, "0", 2),  # '1' (10 MHz one-shot -> 204.8 us window)
            "trig_pos": 256,
            "dt_us": 0.10,
        },
        {
            "key": "trace3_hadamard_ON_mat3_and_mat8_ce2mhz",
            "title": "Hadamard ON (Matrix 3 + 20 us Gap + Matrix 8) @ 2 MHz Capture Enable (ce_2mhz_1shot == 1)",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 2, "0", 2),   # '1' (Hadamard ON)
                ("hadamard_mat3_on", 2, "0", 2),    # '1' (Start on Matrix 3 burst)
            ],
            "cap_rule": ("ce_2mhz_1shot", 2, "0", 2),   # '1' (2 MHz one-shot -> 1.024 ms window)
            "trig_pos": 128,
            "dt_us": 0.50,
        },
        {
            "key": "trace4_hadamard_ON_adc_done_500khz",
            "title": "Hadamard ON (Matrix 3 + Matrix 8) @ 500 kHz ADC Sample Done (adc_done_1shot == 1)",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 2, "0", 2),   # '1' (Hadamard ON)
            ],
            "cap_rule": ("adc_done_1shot", 2, "0", 2),  # '1' (500 kHz ADC done one-shot -> 4.096 ms window)
            "trig_pos": 128,
            "dt_us": 2.00,
        },
        {
            "key": "trace5_full_50mhz_spi_timing",
            "title": "Full 50 MHz Capture (Capture Mode = Always, 20 ns Resolution, 40.96 us Window)",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 2, "0", 2),   # '1' (Hadamard ON)
                ("hadamard_mat3_on", 2, "0", 2),    # '1' (Matrix 3 active)
            ],
            "cap_rule": None,  # Always capture at 50 MHz
            "trig_pos": 512,
            "dt_us": 0.02,
        },
        {
            "key": "trace6_hadamard_ON_patternB_negW_ce10mhz",
            "title": "Hadamard ON — Weight Pattern B (-W, All Weights Flipped) @ 10 MHz Capture Enable (ce_10mhz_1shot == 1)",
            "pre_hook": "flip_to_B",
            "trig_rules": [
                ("hadamard_burst_act", 2, "0", 2),  # '1' (Burst active)
                ("hadamard_on_n_off", 2, "0", 2),   # '1' (Hadamard ON)
                ("hadamard_mat3_on", 2, "0", 2),    # '1' (Matrix 3 active)
            ],
            "cap_rule": ("ce_10mhz_1shot", 2, "0", 2),  # '1' (10 MHz one-shot -> 204.8 us window)
            "trig_pos": 256,
            "dt_us": 0.10,
        },
    ]

    for cfg in test_configs:
        key = cfg["key"]
        if cfg.get("pre_hook") == "flip_to_B":
            print("\n[*] Flipping all 126 weight signs to Pattern B (-W = -W_A) via UDP 0x19 mode 8...")
            udp_cmd(struct.pack("<IBBH", 0x4D414D4C, 0x19, 8, 0x00FF))
            udp_cmd(struct.pack("<IBBBHBHBbB", 0x4D414D4C, 0x11, 3, 3, 500, 25, 100, 10, 0, 14))
            time.sleep(0.05)

        print(f"\n[*] Running Capture: {cfg['title']} ...")
        buf, status = configure_and_capture(
            jm,
            dbg_sesh,
            spec,
            "la0",
            trig_rules=cfg["trig_rules"],
            cap_rule=cfg["cap_rule"],
            trig_pos=cfg["trig_pos"],
            timeout_s=5.0,
        )
        if buf is None:
            print(f"    [!] Capture {key} did not trigger!")
            continue

        vcd_path = out_vcd_dir / f"{key}.vcd"
        with open(vcd_path, "w") as fp:
            ctrl.export_vcd(fp, buf, spec.data_depth)
        print(f"    [+] Exported VCD ({len(buf)} samples) -> {vcd_path}")

        rows = [unpack_sample(bseq, probes_meta) for bseq in buf]
        captures_summary["traces"][key] = {
            "title": cfg["title"],
            "trig_pos": cfg["trig_pos"],
            "dt_us": cfg["dt_us"],
            "vcd_path": str(vcd_path),
            "num_samples": len(rows),
            "rows": rows,
        }

        # Print quick summary statistics for ADC_45 and Hadamard signals
        ch1_vals = [r["adc45_ch1_raw"] for r in rows]
        ch2_vals = [r["adc45_ch2_raw"] for r in rows]
        ch0_vals = [r["adc45_ch0_raw"] for r in rows]
        m8_vals = [r["adc49_ch2_raw"] for r in rows]
        h_on_vals = set(r["hadamard_on_n_off"] for r in rows)
        m3_on_vals = set(r["hadamard_mat3_on"] for r in rows)
        m8_on_vals = set(r["hadamard_mat8_on"] for r in rows)
        h_steps = sorted(set(r["h_step_idx"] for r in rows))
        print(
            f"    [+] Summary: hadamard_on_n_off={h_on_vals}, mat3_on={m3_on_vals}, mat8_on={m8_on_vals}, "
            f"h_step_idx={h_steps[0]}..{h_steps[-1]}"
        )
        print(
            f"        adc45_ch1_raw (M3+): min={min(ch1_vals)}, max={max(ch1_vals)}, span={max(ch1_vals)-min(ch1_vals)} LSB"
        )
        print(
            f"        adc45_ch2_raw (M3-): min={min(ch2_vals)}, max={max(ch2_vals)}, span={max(ch2_vals)-min(ch2_vals)} LSB"
        )
        print(
            f"        adc49_ch2_raw (M8) : min={min(m8_vals)}, max={max(m8_vals)}, span={max(m8_vals)-min(m8_vals)} LSB"
        )

    # Restore Weight Pattern A (+W) and autonomous run_mode = 3
    udp_cmd(struct.pack("<IBBH", 0x4D414D4C, 0x19, 4, 0x00FF))
    udp_cmd(struct.pack("<IBBBHBHBbB", 0x4D414D4C, 0x11, 3, 3, 500, 25, 100, 10, 0, 14))
    sock.close()

    json_out = DOCS_DIR / "t120_la_bare_metal_captures.json"
    with open(json_out, "w") as fp:
        json.dump(captures_summary, fp, indent=2)
    print(f"\n[+] Saved all bare-metal Logic Analyzer captures to {json_out}")

    jm.unconfig_debug(dbg_sesh)
    jm.unconfig_jtag(jtag_sesh)
    print("[+] JTAG session cleanly closed.")


if __name__ == "__main__":
    main()

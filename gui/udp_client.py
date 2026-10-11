"""
UDP Ethernet Client & Physics Digital Twin Fallback for the Inverted MAML Platform.
Communicates with Efinix Trion T120F324 RISC-V Master SoC at 192.168.1.50:5000
using the binary 'MAML' (0x4D414D4C) protocol defined in maml_platform.h and
legacy ASCII commands.
"""

from __future__ import annotations
import math
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

MAML_UDP_MAGIC = 0x4D414D4C

# Binary UDP opcodes (matching FPGA_code/sw/t120_master/include/maml_platform.h)
MAML_CMD_GET_TELEMETRY  = 0x10
MAML_CMD_SET_CONFIG     = 0x11
MAML_CMD_SET_HEATERS    = 0x12
MAML_CMD_SET_LEDS       = 0x13
MAML_CMD_SET_DAC_MODE   = 0x14
MAML_CMD_CENTER_COMP    = 0x15
MAML_CMD_SEED_WEIGHTS   = 0x16
MAML_CMD_CELL_DIAG      = 0x17
MAML_CMD_STEP_OUTER     = 0x18
MAML_CMD_DIAG_HADAMARD  = 0x19

# Matrix IDs matching maml_platform.h (0=M3, 1=M8, 2=M33)
MAT_M3  = 0
MAT_M8  = 1
MAT_M33 = 2


@dataclass
class HadamardDiagResult:
    mode: int
    en_mask: int
    settle_cycles: int
    ack_ok: int
    ack_miss: int
    lat_last: int
    lat_min: int
    lat_max: int
    t20_word_cnt: int
    t20_sync_err: int
    perm: List[int]
    h_words: List[int]
    cap45: List[List[int]]
    cap49: List[List[int]]
    fwht45: List[List[int]]
    fwht49: List[List[int]]
    adc45_hiz: List[int]
    adc49_hiz: List[int]


@dataclass
class CellProbeResult:
    matrix_id: int
    row: int
    col: int
    adc45_pos: List[int]
    adc45_neg: List[int]
    adc45_zero: List[int]
    adc49_pos: List[int]
    adc49_neg: List[int]
    adc49_zero: List[int]


@dataclass
class MamlTelemetry:
    mode: int = 0                    # 0=IDLE, 1=TRAIN_BASE(Ref40), 2=OPERATIONAL(Ref42)
    jumper_mode: int = 3             # 1=OFF, 2=Bypass 2nd Sigmoid, 3=Use 2nd Sigmoid
    heater_armed: bool = False
    heater_wdog_ok: bool = True
    led_switches: int = 0            # bit0=COMP_LED_ON, bit1=MAT33_LED_ON
    heater_duty: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    hadamard_khz: int = 500
    settle_cycles: int = 100
    max_meas_win_pct: int = 25
    inner_loop_n: int = 100
    seed_pct: int = 28
    seed_mode: int = 1
    w_hid_mag: int = 14
    trim_hid_mag: int = 0
    outer_epoch: int = 0
    inner_step: int = 0
    stratum_idx: int = 0
    refresh_cnt: int = 0
    enob_q8: int = 1840              # ~7.19 bits in Q8.8
    mse_q14: int = 180
    enob_uncomp_q8: int = 1080       # ~4.22 bits in Q8.8
    enob_comp_q8: int = 1980         # ~7.73 bits in Q8.8
    basin_loss_q14: List[int] = field(default_factory=lambda: [2400, 2650, 2200, 2800])
    basin_dist_q14: List[int] = field(default_factory=lambda: [3200, 3500, 2900, 3800])
    basin_hess_dot: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    adc45_sig: List[int] = field(default_factory=lambda: [0] * 6)
    adc49_sig: List[int] = field(default_factory=lambda: [0] * 6)
    ref_x: List[int] = field(default_factory=lambda: [180, -140, 210, -95, 130, -195])
    z_target: List[int] = field(default_factory=lambda: [0] * 6)
    sigma2_slope: List[int] = field(default_factory=lambda: [0] * 6)
    t20_h_ack_ok: int = 0
    t20_h_ack_miss: int = 0
    t20_h_lat_last: int = 0
    connected_hw: bool = False
    status_text: str = "Digital Twin Active (Ready)"

    @property
    def enob_bits(self) -> float:
        return self.enob_q8 / 256.0

    @property
    def enob_uncomp_bits(self) -> float:
        return self.enob_uncomp_q8 / 256.0

    @property
    def enob_comp_bits(self) -> float:
        return self.enob_comp_q8 / 256.0

    @property
    def step_period_us(self) -> float:
        return 1000.0 / max(50, self.hadamard_khz)

    @property
    def full_refresh_period_ms(self) -> float:
        # 10 strata * 17 Hadamard steps (16 active + 1 Hi-Z trailing) * step_period_us
        return (10.0 * 17.0 * self.step_period_us) / 1000.0


class MamlUdpClient:
    """Thread-safe UDP client communicating with T120 v2.0-MAML firmware on Port 5000."""

    # Exact struct format for maml_telemetry_pkt_t (298 bytes, #pragma pack(1))
    TELEM_FMT = "<IBBBBB4BBBBBBBBHBBBBHHIIBBHIHH6h6h6h6h6h48b42b36bbbhhI4h4h4I4hHIIH"
    TELEM_SIZE = struct.calcsize(TELEM_FMT)

    # Exact struct format for maml_cell_probe_resp_t (80 bytes, #pragma pack(1))
    PROBE_FMT = "<IBBBB6h6h6h6h6h6h"
    PROBE_SIZE = struct.calcsize(PROBE_FMT)

    # Exact struct format for maml_hadamard_diag_resp_t (866 bytes, #pragma pack(1))
    HAD_DIAG_FMT = "<IBBH16B16HIIHHHHHH6h6h96h96h96h96h"
    HAD_DIAG_SIZE = struct.calcsize(HAD_DIAG_FMT)

    def __init__(self, host: str = "192.168.1.50", port: int = 5000, timeout: float = 0.25):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.use_simulator = False
        self._lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)

        # Digital twin state
        self.sim_telemetry = MamlTelemetry()
        self.sim_comp_centered = False
        self.sim_osc_10hz = False
        self.sim_ovr_en = False
        self.sim_ovr_bank = 0
        self.sim_ovr_ch = 0
        self.sim_ovr_val = 128

        # Fixed physical fabrication mismatch profile for fallback
        rng = np.random.default_rng(26303974)
        self.sim_m33_gain = 1.0 + rng.normal(0.0, 0.085, size=(6, 6))
        self.sim_m33_offset = rng.normal(0.0, 14.0, size=(6, 6))
        self.sim_m3_gain = 1.0 + rng.normal(0.0, 0.055, size=(8, 6))
        self.sim_m3_offset = rng.normal(0.0, 9.0, size=(8, 6))
        self.sim_m8_gain = 1.0 + rng.normal(0.0, 0.055, size=(7, 6))
        self.sim_m8_offset = rng.normal(0.0, 9.0, size=(7, 6))

        # 4 inner-loop valley positions in 2D projected weight space (u1, u2)
        self.valley_coords = np.array([
            [-1.35,  1.15],
            [ 1.40,  1.20],
            [-1.25, -1.30],
            [ 1.30, -1.10],
        ], dtype=np.float64)
        self.base_w0_coord = np.array([0.0, 0.0], dtype=np.float64)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _send_binary(self, opcode: int, payload: bytes = b"") -> Optional[bytes]:
        if self.use_simulator:
            return None
        pkt = struct.pack("<IB", MAML_UDP_MAGIC, opcode) + payload
        with self._lock:
            try:
                self.sock.sendto(pkt, (self.host, self.port))
                data, _ = self.sock.recvfrom(1500)
                if len(data) >= 5:
                    magic, msg_type = struct.unpack("<IB", data[:5])
                    if magic == MAML_UDP_MAGIC:
                        return data
            except OSError:
                return None
        return None

    def send_ascii(self, cmd: str) -> str:
        with self._lock:
            try:
                self.sock.sendto(cmd.encode("ascii"), (self.host, self.port))
                data, _ = self.sock.recvfrom(1500)
                return data.decode("ascii", errors="replace").strip()
            except OSError as exc:
                return f"[Offline / Digital Twin] {cmd} ({exc})"

    def query_version(self) -> str:
        return self.send_ascii("VERSION")

    def jump_t20_app(self) -> str:
        return self.send_ascii("JUMP_APP")

    def jump_t20_golden(self) -> str:
        return self.send_ascii("JUMP_GOLDEN")

    def _parse_hw_telemetry(self, raw: bytes) -> Optional[MamlTelemetry]:
        if len(raw) < self.TELEM_SIZE:
            return None
        u = struct.unpack(self.TELEM_FMT, raw[:self.TELEM_SIZE])
        if u[0] != MAML_UDP_MAGIC or u[1] != 0x90:
            return None

        run_mode = u[2]
        jumper_mode = u[3]
        heater_armed = bool(u[4])
        heater_wdog_ok = bool(u[5])
        heater_duty = [int(d * 100 // 255) for d in u[6:10]]
        comp_led_on = u[10]
        mat33_led_on = u[11]
        led_switches = (1 if comp_led_on else 0) | (2 if mat33_led_on else 0)

        hadamard_khz = u[17]
        max_meas_duty_pct = u[18]
        seed_mode = u[19]
        seed_swing_pct = u[20]
        inner_loop_n = u[22]
        cur_inner_step = u[23]
        outer_loop_epoch = u[24]
        total_refresh_cycles = u[25]
        cur_stratum_slot = u[26]
        settle_cycles = u[28]

        loss_total_milli = u[29]
        bit_prec_comp_centi = u[30]
        bit_prec_uncomp_centi = u[31]

        x_ref = list(u[32:38])
        z_target = list(u[38:44])
        adc45_sig = list(u[44:50])
        adc49_sig = list(u[50:56])
        sigma2_slope = list(u[56:62])

        # w_m3: 62..110 (48), w_m8: 110..152 (42), w_m33: 152..188 (36)
        trim_dac_38 = u[188]
        hid_trim_offset = u[189]
        w0_coord_x = u[190]
        w0_coord_y = u[191]
        w0_loss_milli = u[192]
        basin_coord_x = list(u[193:197])
        basin_coord_y = list(u[197:201])
        basin_loss_milli = list(u[201:205])
        basin_hess_dot = list(u[205:209])
        basin_spread_milli = u[209]
        t20_h_ack_ok = u[210]
        t20_h_ack_miss = u[211]
        t20_h_lat_last = u[212]

        enob_comp_q8 = int((bit_prec_comp_centi / 100.0) * 256.0)
        enob_uncomp_q8 = int((bit_prec_uncomp_centi / 100.0) * 256.0)
        enob_q8 = enob_uncomp_q8 if self.sim_comp_centered else enob_comp_q8

        basin_dist_q14 = []
        for k in range(4):
            dx = (basin_coord_x[k] - w0_coord_x) / 256.0
            dy = (basin_coord_y[k] - w0_coord_y) / 256.0
            dist = math.hypot(dx, dy)
            basin_dist_q14.append(int(min(16384, max(80, dist * 2100.0))))
            self.valley_coords[k] = np.array([basin_coord_x[k] / 256.0, basin_coord_y[k] / 256.0])
        self.base_w0_coord = np.array([w0_coord_x / 256.0, w0_coord_y / 256.0])

        t = MamlTelemetry(
            mode=run_mode,
            jumper_mode=jumper_mode,
            heater_armed=heater_armed,
            heater_wdog_ok=heater_wdog_ok,
            led_switches=led_switches,
            heater_duty=heater_duty,
            hadamard_khz=hadamard_khz,
            settle_cycles=settle_cycles,
            max_meas_win_pct=max_meas_duty_pct,
            inner_loop_n=inner_loop_n,
            seed_pct=seed_swing_pct,
            seed_mode=seed_mode,
            w_hid_mag=abs(hid_trim_offset) if hid_trim_offset else 12,
            trim_hid_mag=trim_dac_38,
            outer_epoch=outer_loop_epoch,
            inner_step=cur_inner_step,
            stratum_idx=cur_stratum_slot,
            refresh_cnt=total_refresh_cycles,
            enob_q8=enob_q8,
            mse_q14=int(min(65535, loss_total_milli // 10)),
            enob_uncomp_q8=enob_uncomp_q8,
            enob_comp_q8=enob_comp_q8,
            basin_loss_q14=[int(min(16384, b // 10)) for b in basin_loss_milli],
            basin_dist_q14=basin_dist_q14,
            basin_hess_dot=basin_hess_dot,
            adc45_sig=adc45_sig,
            adc49_sig=adc49_sig,
            ref_x=x_ref,
            z_target=z_target,
            sigma2_slope=sigma2_slope,
            t20_h_ack_ok=t20_h_ack_ok,
            t20_h_ack_miss=t20_h_ack_miss,
            t20_h_lat_last=t20_h_lat_last,
            connected_hw=True,
            status_text=(
                f"LIVE HW ({self.host}:{self.port}) — Settle={settle_cycles*20}ns | "
                f"H-ACK OK={t20_h_ack_ok} MISS={t20_h_ack_miss} LAT={t20_h_lat_last}"
            ),
        )
        self.sim_telemetry = t
        return t

    def _step_digital_twin(self, force_outer: bool = False) -> None:
        t = self.sim_telemetry
        t.refresh_cnt += 1
        t.stratum_idx = (t.stratum_idx + 1) % 10

        if t.stratum_idx == 0:
            rng = np.random.default_rng(t.refresh_cnt + 101)
            t.ref_x = [int(v) for v in rng.integers(-220, 221, size=6)]

        heat_warp = 0.0
        if t.heater_armed:
            heat_warp = sum(t.heater_duty) / 400.0

        if t.mode in (1, 2) or force_outer:
            t.inner_step += 5
            if t.inner_step >= max(1, t.inner_loop_n) or force_outer:
                t.inner_step = 0
                t.outer_epoch += 1
                pull_rate = 0.085 if not force_outer else 0.14
                target_radius = 0.16 + 0.18 * heat_warp + 0.004 * (t.w_hid_mag + abs(t.trim_hid_mag))
                for k in range(4):
                    vec = self.valley_coords[k] - self.base_w0_coord
                    dist = float(np.linalg.norm(vec))
                    if dist > target_radius:
                        new_dist = max(target_radius, dist * (1.0 - pull_rate))
                        self.valley_coords[k] = self.base_w0_coord + vec * (new_dist / (dist + 1e-9))
                    theta = 0.03 * (1.0 if k % 2 == 0 else -1.0)
                    c, s = math.cos(theta), math.sin(theta)
                    x0, y0 = self.valley_coords[k]
                    self.valley_coords[k] = np.array([c * x0 - s * y0, s * x0 + c * y0])

        for k in range(4):
            d = float(np.linalg.norm(self.valley_coords[k] - self.base_w0_coord))
            t.basin_dist_q14[k] = int(min(16384, max(120, d * 2100.0)))
            base_loss = 180.0 + 1150.0 * (d ** 2) + 320.0 * heat_warp
            if self.sim_comp_centered or t.jumper_mode == 1:
                base_loss *= 3.2
            t.basin_loss_q14[k] = int(min(16384, max(60, base_loss)))

        mean_dist = float(np.mean([np.linalg.norm(v) for v in self.valley_coords]))
        if self.sim_comp_centered or t.jumper_mode == 1:
            err_rms = 115.0 + 45.0 * heat_warp
        else:
            err_rms = 14.0 + 38.0 * mean_dist + 18.0 * heat_warp
            if t.jumper_mode == 2:
                err_rms *= 1.15

        rng_adc = np.random.default_rng((t.refresh_cnt * 17 + t.stratum_idx) & 0xFFFFFFFF)
        for ch in range(6):
            ideal = int(t.ref_x[ch] * 3.8)
            noise45 = int(rng_adc.normal(0.0, err_rms * 0.8))
            noise49 = int(rng_adc.normal(0.0, err_rms))
            t.adc45_sig[ch] = max(-2048, min(2047, ideal + noise45))
            t.adc49_sig[ch] = max(-2048, min(2047, ideal + noise49))

        t.mse_q14 = int(min(16384, max(4, err_rms * 4.2)))
        enob = max(1.5, min(11.2, 9.6 - math.log2(1.0 + err_rms * 0.18)))
        t.enob_q8 = int(enob * 256.0)
        if not self.sim_comp_centered and t.jumper_mode != 1:
            t.enob_comp_q8 = t.enob_q8

    def poll_telemetry(self) -> MamlTelemetry:
        raw = self._send_binary(MAML_CMD_GET_TELEMETRY)
        if raw is not None:
            parsed = self._parse_hw_telemetry(raw)
            if parsed is not None:
                return parsed

        # Fallback to physics digital twin
        self._step_digital_twin()
        self.sim_telemetry.connected_hw = False
        self.sim_telemetry.status_text = "Physics Digital Twin Mode (Hardware Offline or Sim Selected)"
        return self.sim_telemetry

    def set_config(
        self,
        mode: int,
        jumper_mode: int,
        led_switches: int,
        max_meas_win_pct: int,
        hadamard_khz: int,
        inner_loop_n: int,
        seed_pct: int,
        seed_mode: int,
        w_hid_mag: int,
        trim_hid_mag: int,
    ) -> None:
        t = self.sim_telemetry
        t.mode = mode
        t.jumper_mode = jumper_mode
        t.led_switches = led_switches
        t.max_meas_win_pct = 100 if mode == 1 else max_meas_win_pct
        t.hadamard_khz = max(50, min(500, hadamard_khz))
        t.settle_cycles = (50000 // t.hadamard_khz)
        t.inner_loop_n = max(1, min(500, inner_loop_n))
        t.seed_pct = max(0, min(100, seed_pct))
        t.seed_mode = seed_mode
        t.w_hid_mag = 0 if mode == 2 else w_hid_mag
        t.trim_hid_mag = trim_hid_mag

        # Matches MAML_CMD_SET_CONFIG in maml_platform.c (req_len >= 15):
        # req[5]=run_mode, req[6]=jumper_mode, req[7..8]=hadamard_freq_khz,
        # req[9]=max_meas_duty_pct, req[10..11]=inner_loop_n, req[12]=num_strata_m,
        # req[13]=trim_dac_38, req[14]=g_hid_amp_dac
        payload = struct.pack(
            "<BBHBHBbb",
            t.mode,
            t.jumper_mode,
            t.hadamard_khz,
            t.max_meas_win_pct,
            t.inner_loop_n,
            10,
            max(-127, min(127, int(t.trim_hid_mag))),
            max(1, min(64, int(t.w_hid_mag))),
        )
        self._send_binary(MAML_CMD_SET_CONFIG, payload)

        # Also sync LED switches
        comp_led = 1 if (led_switches & 1) else 0
        mat33_led = 1 if (led_switches & 2) else 0
        self._send_binary(MAML_CMD_SET_LEDS, struct.pack("<BB", comp_led, mat33_led))

    def set_heaters(self, armed: bool, duty_0_100: List[int]) -> None:
        t = self.sim_telemetry
        t.heater_armed = bool(armed)
        t.heater_duty = [int(max(0, min(100, d))) if armed else 0 for d in duty_0_100[:4]]
        duty_u8 = [int(d * 255 // 100) for d in t.heater_duty]
        payload = struct.pack("<5B", 1 if t.heater_armed else 0, *duty_u8)
        self._send_binary(MAML_CMD_SET_HEATERS, payload)

    def set_dac_mode(self, osc_10hz_en: bool, ovr_en: bool, bank: int, ch: int, val: int) -> None:
        self.sim_osc_10hz = osc_10hz_en
        self.sim_ovr_en = ovr_en
        bank_byte = 0xFF if bank >= 4 else (bank & 0x3)
        self.sim_ovr_bank = bank & 0x3
        self.sim_ovr_ch = ch & 0x7
        self.sim_ovr_val = max(0, min(255, val))
        payload = struct.pack(
            "<5B",
            1 if osc_10hz_en else 0,
            1 if ovr_en else 0,
            bank_byte,
            self.sim_ovr_ch,
            self.sim_ovr_val,
        )
        raw = self._send_binary(MAML_CMD_SET_DAC_MODE, payload)
        if raw is not None:
            self._parse_hw_telemetry(raw)

    def center_compensation_weights(self) -> None:
        """Sets all compensation weights (M3 & M8) to differential center 128 (0.0 weight)."""
        self.sim_comp_centered = True
        raw = self._send_binary(MAML_CMD_CENTER_COMP)
        if raw is not None:
            self._parse_hw_telemetry(raw)
        else:
            self._step_digital_twin()

    def seed_weights(self, seed_mode: int = 1, swing_pct: int = 28) -> None:
        self.sim_comp_centered = False
        payload = struct.pack("<BB", seed_mode & 0x7, max(0, min(100, swing_pct)))
        raw = self._send_binary(MAML_CMD_SEED_WEIGHTS, payload)
        if raw is not None:
            self._parse_hw_telemetry(raw)
        else:
            self._step_digital_twin()

    def restore_compensation_weights(self) -> None:
        self.seed_weights(self.sim_telemetry.seed_mode, self.sim_telemetry.seed_pct)

    def step_outer_loop(self) -> MamlTelemetry:
        self.sim_comp_centered = False
        raw = self._send_binary(MAML_CMD_STEP_OUTER)
        if raw is not None:
            parsed = self._parse_hw_telemetry(raw)
            if parsed is not None:
                return parsed
        self._step_digital_twin(force_outer=True)
        return self.sim_telemetry

    def probe_cell(self, matrix_id: int, row: int, col: int) -> Optional[CellProbeResult]:
        payload = struct.pack("<BBB", matrix_id, row, col)
        raw = self._send_binary(MAML_CMD_CELL_DIAG, payload)
        if raw is not None and len(raw) >= self.PROBE_SIZE:
            u = struct.unpack(self.PROBE_FMT, raw[:self.PROBE_SIZE])
            if u[0] == MAML_UDP_MAGIC and u[1] == 0x97:
                return CellProbeResult(
                    matrix_id=u[2],
                    row=u[3],
                    col=u[4],
                    adc45_pos=list(u[5:11]),
                    adc45_neg=list(u[11:17]),
                    adc45_zero=list(u[17:23]),
                    adc49_pos=list(u[23:29]),
                    adc49_neg=list(u[29:35]),
                    adc49_zero=list(u[35:41]),
                )
        return None

    def probe_cell_xw(
        self,
        matrix_id: int,
        row: int,
        col: int,
        x_amp: int = 96,
        w_fixed: int = 64,
        sweep_input: bool = True,
        hold: bool = False,
    ) -> Optional[CellProbeResult]:
        """
        Locks cell (matrix_id, row, col) at fixed weight W = w_fixed (-127..+127)
        and steps Input row DAC_2[row] across X = 0 (adc_zero), X = +x_amp (adc_pos),
        and X = -x_amp (adc_neg).
        """
        x_clamped = max(-127, min(127, int(x_amp)))
        w_clamped = max(-127, min(127, int(w_fixed)))
        mode_flag = (0x01 if sweep_input else 0x00) | (0x02 if hold else 0x00)
        payload = struct.pack("<BBBbbB", matrix_id & 0xFF, row & 0xFF, col & 0xFF, x_clamped, w_clamped, mode_flag)
        raw = self._send_binary(MAML_CMD_CELL_DIAG, payload)
        if raw is not None and len(raw) >= self.PROBE_SIZE:
            u = struct.unpack(self.PROBE_FMT, raw[:self.PROBE_SIZE])
            if u[0] == MAML_UDP_MAGIC and u[1] == 0x97:
                return CellProbeResult(
                    matrix_id=u[2],
                    row=u[3],
                    col=u[4],
                    adc45_pos=list(u[5:11]),
                    adc45_neg=list(u[11:17]),
                    adc45_zero=list(u[17:23]),
                    adc49_pos=list(u[23:29]),
                    adc49_neg=list(u[29:35]),
                    adc49_zero=list(u[35:41]),
                )
        return None

    def run_single_cell_multiplier_curve(
        self,
        matrix_id: int,
        row: int,
        col: int,
        x_amp: int = 96,
        weights: Optional[List[int]] = None,
    ) -> List[dict]:
        """
        Sweeps fixed weight W across `weights` (default [-96, -48, 0, +48, +96]) while moving
        input row DAC_2[row] up (+x_amp) and down (-x_amp) by the same amount at each weight.
        """
        if weights is None:
            weights = [-96, -48, 0, +48, +96]
        results: List[dict] = []
        for w in weights:
            res = self.probe_cell_xw(matrix_id, row, col, x_amp=x_amp, w_fixed=w, sweep_input=True, hold=False)
            if res is not None:
                if matrix_id == MAT_M3:
                    v_neg = res.adc45_neg[col]
                    v_zero = res.adc45_zero[col]
                    v_pos = res.adc45_pos[col]
                    adc_name = f"ADC_45[C{col+1}]"
                else:
                    v_neg = res.adc49_neg[col]
                    v_zero = res.adc49_zero[col]
                    v_pos = res.adc49_pos[col]
                    adc_name = f"ADC_49[C{col+1}]"
                results.append({
                    "w": w,
                    "x_amp": x_amp,
                    "adc_name": adc_name,
                    "out_x_neg": v_neg,
                    "out_x_zero": v_zero,
                    "out_x_pos": v_pos,
                    "delta_up_down": v_pos - v_neg,
                })
        return results

    def diag_hadamard(self, mode: int = 0, en_mask: int = 0x7FFF) -> Optional[HadamardDiagResult]:
        payload = struct.pack("<BH", mode & 0xFF, en_mask & 0xFFFF)
        raw = self._send_binary(MAML_CMD_DIAG_HADAMARD, payload)
        if raw is not None and len(raw) >= self.HAD_DIAG_SIZE:
            u = struct.unpack(self.HAD_DIAG_FMT, raw[:self.HAD_DIAG_SIZE])
            if u[0] == MAML_UDP_MAGIC and u[1] == 0x99:
                idx = 4
                perm = list(u[idx : idx + 16]); idx += 16
                h_words = list(u[idx : idx + 16]); idx += 16
                ack_ok = u[idx]; ack_miss = u[idx + 1]; idx += 2
                lat_last = u[idx]; lat_min = u[idx + 1]; lat_max = u[idx + 2]
                t20_word_cnt = u[idx + 3]; t20_sync_err = u[idx + 4]; settle_cycles = u[idx + 5]
                idx += 6
                adc45_hiz = list(u[idx : idx + 6]); idx += 6
                adc49_hiz = list(u[idx : idx + 6]); idx += 6
                cap45 = [list(u[idx + 6 * k : idx + 6 * (k + 1)]) for k in range(16)]; idx += 96
                cap49 = [list(u[idx + 6 * k : idx + 6 * (k + 1)]) for k in range(16)]; idx += 96
                fwht45 = [list(u[idx + 6 * k : idx + 6 * (k + 1)]) for k in range(16)]; idx += 96
                fwht49 = [list(u[idx + 6 * k : idx + 6 * (k + 1)]) for k in range(16)]; idx += 96
                return HadamardDiagResult(
                    mode=u[2],
                    en_mask=u[3],
                    settle_cycles=settle_cycles,
                    ack_ok=ack_ok,
                    ack_miss=ack_miss,
                    lat_last=lat_last,
                    lat_min=lat_min,
                    lat_max=lat_max,
                    t20_word_cnt=t20_word_cnt,
                    t20_sync_err=t20_sync_err,
                    perm=perm,
                    h_words=h_words,
                    cap45=cap45,
                    cap49=cap49,
                    fwht45=fwht45,
                    fwht49=fwht49,
                    adc45_hiz=adc45_hiz,
                    adc49_hiz=adc49_hiz,
                )
        return None

    def reset_valleys_spread(self) -> None:
        """Re-spreads the 4 inner-loop loss basins so the user can watch Ref 40 gather them."""
        rng = np.random.default_rng()
        angles = [0.65, 2.35, -2.45, -0.70]
        for k, ang in enumerate(angles):
            r = float(rng.uniform(1.45, 1.85))
            self.valley_coords[k] = np.array([r * math.cos(ang), r * math.sin(ang)])
        self.sim_telemetry.outer_epoch = 0
        self.sim_telemetry.inner_step = 0
        self.seed_weights(self.sim_telemetry.seed_mode, self.sim_telemetry.seed_pct)

    def run_auto_bit_precision_test(self) -> Tuple[float, float, float]:
        """
        Benchmarks effective bit precision (ENOB):
          1. Centers all compensation weights (M3/M8 = 128) -> measures uncompensated ENOB
          2. Restores/steps trained compensation weights -> measures compensated ENOB
        Returns (enob_uncomp, enob_comp, delta_enob).
        """
        self.center_compensation_weights()
        t_uncomp = self.step_outer_loop()
        u_bits = t_uncomp.enob_uncomp_bits

        self.seed_weights(self.sim_telemetry.seed_mode, self.sim_telemetry.seed_pct)
        t_comp = self.step_outer_loop()
        c_bits = t_comp.enob_comp_bits

        return u_bits, c_bits, (c_bits - u_bits)

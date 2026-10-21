#!/usr/bin/env python3
import os
import sys
import json

EFINITY_HOME = "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2"
os.environ["EFINITY_HOME"] = EFINITY_HOME
os.environ["EFXDBG_HOME"]  = os.path.join(EFINITY_HOME, "debugger")
os.environ["EFXPGM_HOME"]  = os.path.join(EFINITY_HOME, "pgm")
sys.path.insert(0, os.path.join(EFINITY_HOME, "debugger", "bin"))

from efx_dbg.define import DebugProfile, DebugProfileEncoder, LogicNSpec
from efx_dbg.rtl_gen import write_debug_top_verilog, write_debug_template_verilog

OUT_DIR = "/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324_LA"

profile = DebugProfile()
profile.jtag_user = "USER1"

la = profile.add_core("la0", "la", gen_uuid=True)
la.set_attr("data_depth", 2048)
la.set_attr("capture_control", True)
la.set_attr("trigin_en", False)
la.set_attr("trigout_en", False)
la.set_attr("input_pipeline", 1)

# Probe Type 1 = DATA_AND_TRIGGER (all probes < 64 support both Trigger and Capture Enable!)
TID_DATA_AND_TRIG = LogicNSpec.LogicNProbe.TID["DATA AND TRIGGER"]

probes = [
    # 1. Downsampling / Capture-Enable One-Shot Pulses (use in Capture Setup -> Basic!)
    ("ce_10mhz_1shot",      1,  TID_DATA_AND_TRIG),
    ("ce_2mhz_1shot",       1,  TID_DATA_AND_TRIG),
    ("adc_done_1shot",      1,  TID_DATA_AND_TRIG),
    ("h_latch_1shot",       1,  TID_DATA_AND_TRIG),

    # 2. Hadamard ON vs OFF & Sub-Window Mode Flags
    ("hadamard_burst_act",  1,  TID_DATA_AND_TRIG),
    ("hadamard_on_n_off",   1,  TID_DATA_AND_TRIG),
    ("hadamard_mat3_on",    1,  TID_DATA_AND_TRIG),
    ("hadamard_mat8_on",    1,  TID_DATA_AND_TRIG),
    ("h_step_idx",          4,  TID_DATA_AND_TRIG),
    ("h_word_m3_ptu",       6,  TID_DATA_AND_TRIG),
    ("h_word_tristate",     1,  TID_DATA_AND_TRIG),

    # 3. Physical H-Bus & ADC_45 Pins
    ("h_sync_tx11p",        1,  TID_DATA_AND_TRIG),
    ("h_data_tx11n",        1,  TID_DATA_AND_TRIG),
    ("t20_clk9",            1,  TID_DATA_AND_TRIG),
    ("adc45_conv",          1,  TID_DATA_AND_TRIG),
    ("adc45_sck",           1,  TID_DATA_AND_TRIG),
    ("adc45_out1_sdo0",     1,  TID_DATA_AND_TRIG),
    ("adc45_out2_sdo1",     1,  TID_DATA_AND_TRIG),

    # 4. Parallel Latched 12-bit ADC_45 & ADC_49 Channels
    ("adc45_ch0_raw",       12, TID_DATA_AND_TRIG),
    ("adc45_ch1_raw",       12, TID_DATA_AND_TRIG),
    ("adc45_ch2_raw",       12, TID_DATA_AND_TRIG),
    ("adc45_ch1_sig",       12, TID_DATA_AND_TRIG),
    ("adc49_ch2_raw",       12, TID_DATA_AND_TRIG),
]

for name, width, ptype in probes:
    la.add_probe(name, width, ptype)

profile_path = os.path.join(OUT_DIR, "debug_profile.json")
with open(profile_path, "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=4, cls=DebugProfileEncoder)

os.makedirs(os.path.join(OUT_DIR, "work_dbg"), exist_ok=True)
with open(os.path.join(OUT_DIR, "work_dbg", "debug_profile.json"), "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=4, cls=DebugProfileEncoder)
with open(os.path.join(OUT_DIR, "outflow", "debug_profile.json"), "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=4, cls=DebugProfileEncoder)

debug_top_path = os.path.join(OUT_DIR, "debug_top.v")
debug_tpl_path = os.path.join(OUT_DIR, "debug_TEMPLATE.v")

write_debug_top_verilog(debug_top_path, profile, "edb_top", insert_gbuf=False)
write_debug_template_verilog(debug_tpl_path, profile, "edb_top")

print(f"[+] Generated {profile_path}")
print(f"[+] Generated {debug_top_path} (UUID={la.get_uuid()}, depth={la.get_depth()}, width={la.get_capture_width()} bits)")
print(f"[+] Generated {debug_tpl_path}")


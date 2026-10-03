import subprocess
import os
import sys

EFINITY_HOME = "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2"
os.environ["EFINITY_HOME"] = EFINITY_HOME
BASE_DIR = "/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4"

proj_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/T120_MALM.xml")
mem_info = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.raminfo.pb")
place_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.place")
lbf_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/work_pnr/T120_MALM.lbf")
hex_file = os.path.join(BASE_DIR, "FPGA_code/sw/t120_master/build/t120_master.hex")

cmd = [
    os.path.join(EFINITY_HOME, "bin/efx_bram_update"),
    "--project", proj_file,
    "--mem_info", mem_info,
    "--place", place_file,
    "--lbf", lbf_file,
    "--family", "Trion",
    "--memory", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol0,{hex_file}",
    "--mode", "update"
]

print("Executing:", " ".join(cmd))
res = subprocess.run(cmd)
print("Exit code:", res.returncode)

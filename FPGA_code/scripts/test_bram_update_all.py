import subprocess
import os

EFINITY_HOME = "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2"
os.environ["EFINITY_HOME"] = EFINITY_HOME
BASE_DIR = "/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4"

proj_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/T120_MALM.xml")
mem_info = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.raminfo.pb")
place_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.place")
lbf_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/work_pnr/T120_MALM.lbf")

rom_dir = os.path.join(BASE_DIR, "FPGA_code/sw/t120_master/rom")
bin0 = os.path.join(rom_dir, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol0.bin")
bin1 = os.path.join(rom_dir, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol1.bin")
bin2 = os.path.join(rom_dir, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol2.bin")
bin3 = os.path.join(rom_dir, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol3.bin")

mem_args = [
    "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol0,{bin0}",
    "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol1,{bin1}",
    "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol2,{bin2}",
    "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol3,{bin3}",
]

cmd = [
    os.path.join(EFINITY_HOME, "bin/efx_bram_update"),
    "--project", proj_file,
    "--mem_info", mem_info,
    "--place", place_file,
    "--lbf", lbf_file,
    "--family", "Trion",
    "--mode", "update"
] + mem_args

print("Running command...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)
print("STDOUT:")
for line in res.stdout.splitlines()[-20:]:
    print(line)
if res.stderr:
    print("STDERR:", res.stderr)

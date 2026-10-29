#!/usr/bin/env python3
"""
flash_bin.py - Patch and flash an existing compiled RISC-V BRAM binary (.bin) into T120 via JTAG.
Usage:
    python3 FPGA_code/scripts/flash_bin.py <path_to_bin>
"""

import sys
import os
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EFINITY_HOME = "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2"
TOOLCHAIN = "/home/olle/efinity/efinity-riscv-ide-2025.1/toolchain/bin"
SW_DIR = os.path.join(BASE_DIR, "FPGA_code/sw/t120_master")
ROM_DIR = os.path.join(SW_DIR, "rom")

def run(cmd, cwd=BASE_DIR, desc=""):
    print(f"[*] {desc}...")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FEL under {desc} ({dt:.1f}s):")
        print(res.stdout)
        print(res.stderr)
        sys.exit(1)
    print(f"[+] Klar ({dt:.1f}s)")
    return res

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 flash_bin.py <path/to/t120_master.bin>")
        sys.exit(1)

    bin_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(bin_path):
        print(f"[!] File not found: {bin_path}")
        sys.exit(1)

    os.environ["PATH"] = f"{TOOLCHAIN}:{os.environ.get('PATH', '')}"
    os.environ["EFINITY_HOME"] = EFINITY_HOME

    print(f"[*] Flashing RISC-V binary: {bin_path}")

    # 1. Split into 4 BRAM symbol files
    run(f"python3 tool/binGen.py -b {bin_path} -f 0 -s 131072", cwd=SW_DIR, desc="Genererar BRAM-binärer")

    # 2. Patch bitstream with efx_bram_update
    proj_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/T120_MALM.xml")
    mem_info = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.raminfo.pb")
    place_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/outflow/T120_MALM.place")
    lbf_file = os.path.join(BASE_DIR, "FPGA_code/T120F324/work_pnr/T120_MALM.lbf")

    bin0 = os.path.join(ROM_DIR, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol0.bin")
    bin1 = os.path.join(ROM_DIR, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol1.bin")
    bin2 = os.path.join(ROM_DIR, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol2.bin")
    bin3 = os.path.join(ROM_DIR, "EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol3.bin")

    cmd_update = [
        os.path.join(EFINITY_HOME, "bin/efx_bram_update"),
        "--project", proj_file,
        "--mem_info", mem_info,
        "--place", place_file,
        "--lbf", lbf_file,
        "--family", "Trion",
        "--mode", "update",
        "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol0,{bin0}",
        "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol1,{bin1}",
        "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol2,{bin2}",
        "-b", f"u_sapphire_soc/u_EfxSapphireSoc/system_ramA_logic/ram_symbol3,{bin3}"
    ]
    run(cmd_update, cwd=BASE_DIR, desc="Uppdaterar BRAM i bitstream")

    # 3. Generate final bitstream via efx_pgm
    run("bash FPGA_code/scripts/run_efx_pgm.sh", cwd=BASE_DIR, desc="Genererar färdig bitstream")

    # 4. Program FPGA via JTAG
    run("python3 FPGA_code/scripts/program_t120.py", cwd=BASE_DIR, desc="Programmerar FPGA via JTAG")

    print("\n[SUCCESS] Gammal verifierad binär är nu laddad och körs på kortet!")

if __name__ == "__main__":
    main()

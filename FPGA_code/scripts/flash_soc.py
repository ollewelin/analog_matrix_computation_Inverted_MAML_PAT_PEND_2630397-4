#!/usr/bin/env python3
"""
flash_soc.py - Blixtsnabb C-kompilering, BRAM-patch och JTAG-programmering.
Ingen manuell felsökning i assembler eller stora loggar.
Körs på ~10-15 sekunder!
"""

import sys
import os
import subprocess
import time

BASE_DIR = "/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4"
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

def summarize_main():
    """Komprimerad sammanfattning av main(): räknar minnesaccesser istället för att visa assembler."""
    asm = os.path.join(SW_DIR, "build/t120_master.asm")
    if not os.path.exists(asm):
        return
    in_main, stack, other = False, 0, 0
    for line in open(asm):
        if line.strip().endswith("<main>:"):
            in_main = True
            continue
        if in_main and line.strip() == "":
            break
        if in_main:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            op = parts[2].strip()
            if op in ("lw", "sw", "lb", "lbu", "lh", "lhu", "sb", "sh"):
                if "(sp)" in line:
                    stack += 1
                else:
                    other += 1
    print(f"    main(): {stack} stack/RAM-accesser, {other} periferi-/övriga accesser")

def main():
    os.environ["PATH"] = f"{TOOLCHAIN}:{os.environ.get('PATH', '')}"
    os.environ["EFINITY_HOME"] = EFINITY_HOME

    # 1. Kompilera firmware (make clean && make)
    run("make clean && make", cwd=SW_DIR, desc="Kompilerar C-firmware")
    summarize_main()

    # 2. Generera BRAM symbol-filer med binGen.py
    bin_file = os.path.join(SW_DIR, "build/t120_master.bin")
    run(f"python3 tool/binGen.py -b {bin_file} -f 0 -s 131072", cwd=SW_DIR, desc="Genererar BRAM-binärer")

    # 3. Patcha bitstream med efx_bram_update
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

    # 4. Generera ny hex / bitstream via efx_pgm
    run("bash FPGA_code/scripts/run_efx_pgm.sh", cwd=BASE_DIR, desc="Genererar färdig bitstream")

    # 5. Flashar direkt via JTAG
    run("python3 FPGA_code/scripts/program_t120.py", cwd=BASE_DIR, desc="Programmerar FPGA via JTAG")

    print("\n[SUCCESS] Ny kod är laddad och körs på kortet!")

if __name__ == "__main__":
    main()

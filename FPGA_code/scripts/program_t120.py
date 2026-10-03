#!/usr/bin/env python3
"""
program_t120.py - Program Efinix Trion T120 FPGA via JTAG or SPI Flash using Efinity FTDI programmer.

Usage:
    python3 FPGA_code/scripts/program_t120.py                  # Programs outflow/T120_MALM.hex via JTAG
    python3 FPGA_code/scripts/program_t120.py --scan           # Scan USB and detect FPGA JTAG IDCODE
    python3 FPGA_code/scripts/program_t120.py -l               # List available USB URLs
    python3 FPGA_code/scripts/program_t120.py --mode active    # Program SPI flash (active mode)
    python3 FPGA_code/scripts/program_t120.py path/to/file.hex # Program specific hex file
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path

DEFAULT_EFINITY_PATH = Path("/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2")
DEFAULT_HEX_PATH = Path(__file__).resolve().parent.parent / "T120F324" / "outflow" / "T120_MALM.hex"
DEFAULT_BIT_PATH = Path(__file__).resolve().parent.parent / "T120F324" / "outflow" / "T120_MALM.bit"

def get_efinity_home():
    env_home = os.environ.get("EFINITY_HOME")
    if env_home and Path(env_home).exists():
        return Path(env_home)
    if DEFAULT_EFINITY_PATH.exists():
        return DEFAULT_EFINITY_PATH
    raise FileNotFoundError("Could not find Efinity installation directory. Please set EFINITY_HOME.")

def get_efinity_python(efinity_home):
    py = efinity_home / "bin" / "python3"
    if py.exists():
        return py
    return Path(sys.executable)

def get_env_with_efinity(efinity_home):
    # Dynamically extract full environment by sourcing setup.sh
    setup_sh = efinity_home / "bin" / "setup.sh"
    env = os.environ.copy()
    if setup_sh.exists():
        cmd = f"source {setup_sh} && env"
        try:
            res = subprocess.run(["bash", "-c", cmd], stdout=subprocess.PIPE, text=True, check=True)
            for line in res.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k] = v
            return env
        except Exception:
            pass

    # Fallback if sourcing setup.sh directly fails
    env["EFINITY_HOME"] = str(efinity_home)
    env["EFXPT_HOME"] = str(efinity_home / "pt")
    env["EFXPGM_HOME"] = str(efinity_home / "pgm")
    env["EFXDBG_HOME"] = str(efinity_home / "debugger")
    env["EFXIPM_HOME"] = str(efinity_home / "ipm")
    env["EFXIPMGR_HOME"] = str(efinity_home / "ipm" / "bin" / "ip_manager")
    env["EFXIPPKG_HOME"] = str(efinity_home / "ipm" / "bin" / "ip_packager")
    env["EFXSVF_HOME"] = str(efinity_home / "debugger" / "svf_player")
    env["EFXSERDESDBG_HOME"] = str(efinity_home / "debugger" / "serdes_debug_tool")
    env["EFINITY_USER_DIR_INI"] = os.path.expanduser("~/.local/share/efinity/user_dir.ini")
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONHOME"] = str(efinity_home)
    
    bin_paths = [
        str(efinity_home / "bin"),
        str(efinity_home / "scripts"),
        str(efinity_home / "pgm" / "bin"),
        str(efinity_home / "debugger" / "bin"),
        str(efinity_home / "debugger" / "svf_player" / "bin"),
        str(efinity_home / "ipm" / "bin"),
        str(efinity_home / "ipm" / "bin" / "ip_manager"),
        str(efinity_home / "ipm" / "bin" / "ip_packager")
    ]
    env["PATH"] = ":".join(bin_paths) + ":" + env.get("PATH", "")
    lib_path = str(efinity_home / "lib")
    env["PYTHONPATH"] = lib_path + ((":" + env["PYTHONPATH"]) if "PYTHONPATH" in env else "")
    env["LD_LIBRARY_PATH"] = lib_path + ((":" + env["LD_LIBRARY_PATH"]) if "LD_LIBRARY_PATH" in env else "")

    return env

def scan_usb(py_bin, ftdi_prog, env):
    cmd = [str(py_bin), str(ftdi_prog), "--scan_usb"]
    result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[!] Scan failed: {result.stderr.strip()}", file=sys.stderr)
        return None
    try:
        data = json.loads(result.stdout.strip())
        return data
    except Exception as e:
        print(f"[!] Failed to parse scan output: {result.stdout.strip()} ({e})", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Efinix Trion T120 JTAG/Flash Programmer")
    parser.add_argument("file", nargs="?", default=None, help="Bitstream HEX file to program (defaults to outflow/T120_MALM.hex)")
    parser.add_argument("-m", "--mode", default="jtag", choices=["jtag", "active", "passive", "jtag_chain"],
                        help="Programming mode (default: jtag)")
    parser.add_argument("-u", "--url", default=None, help="Target FTDI URL (e.g. ftdi://0x0403:0x6010:1:6/2)")
    parser.add_argument("--scan", action="store_true", help="Scan USB JTAG targets and exit")
    parser.add_argument("-l", "--list", action="store_true", help="List available USB URLs and exit")
    parser.add_argument("--freq", default="6000000", help="JTAG clock frequency in Hz (default: 6MHz)")
    
    args = parser.parse_args()

    efinity_home = get_efinity_home()
    py_bin = get_efinity_python(efinity_home)
    ftdi_prog = efinity_home / "pgm" / "bin" / "efx_pgm" / "ftdi_program.py"

    if not ftdi_prog.exists():
        print(f"[!] Error: Programmer script not found at {ftdi_prog}", file=sys.stderr)
        sys.exit(1)

    env = get_env_with_efinity(efinity_home)

    if args.scan:
        print("[*] Scanning USB JTAG targets...")
        devices = scan_usb(py_bin, ftdi_prog, env)
        if devices:
            print("[+] Found connected devices:")
            for d in devices:
                print(f"    - Description : {d.get('description')}")
                print(f"      VID:PID     : {d.get('vid')}:{d.get('pid')}")
                print(f"      IDCODE      : {d.get('idcode')} (0x00220A79 = Trion T120)")
        else:
            print("[-] No JTAG devices detected.")
        sys.exit(0)

    if args.list:
        cmd = [str(py_bin), str(ftdi_prog), "-l"]
        subprocess.run(cmd, env=env)
        sys.exit(0)

    # Determine input file based on programming mode:
    # Efinity requirement:
    #   - JTAG mode: requires .bit file
    #   - Active / Passive modes: require .hex file
    if args.file:
        input_file = Path(args.file)
        if args.mode in ["jtag", "jtag_chain"] and input_file.suffix == ".hex":
            bit_cand = input_file.with_suffix(".bit")
            if bit_cand.exists():
                print(f"[*] Note: JTAG mode requires .bit file. Auto-switching to {bit_cand.name}")
                input_file = bit_cand
        elif args.mode in ["active", "passive"] and input_file.suffix == ".bit":
            hex_cand = input_file.with_suffix(".hex")
            if hex_cand.exists():
                print(f"[*] Note: {args.mode} mode requires .hex file. Auto-switching to {hex_cand.name}")
                input_file = hex_cand
    else:
        if args.mode in ["jtag", "jtag_chain"]:
            input_file = DEFAULT_BIT_PATH if DEFAULT_BIT_PATH.exists() else DEFAULT_HEX_PATH
        else:
            input_file = DEFAULT_HEX_PATH if DEFAULT_HEX_PATH.exists() else DEFAULT_BIT_PATH

    if not input_file.exists():
        print(f"[!] Error: Target file '{input_file}' not found!", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Programming Target: {input_file}")
    print(f"[*] Mode: {args.mode}")

    # Build command
    cmd = [
        str(py_bin),
        str(ftdi_prog),
        str(input_file),
        "-m", args.mode,
        "--jtag_clock_freq", str(args.freq)
    ]

    if args.url:
        cmd.extend(["-u", args.url])

    print(f"[*] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, env=env)
    if res.returncode == 0:
        print(f"\n[+] Programming SUCCESSFUL!")
    else:
        print(f"\n[!] Programming FAILED with exit code {res.returncode}", file=sys.stderr)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()

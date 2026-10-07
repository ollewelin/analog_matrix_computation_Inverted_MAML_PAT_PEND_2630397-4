#!/usr/bin/env python3
"""
flash_and_listen.py - Flash firmware and immediately capture UART output.
"""
import os
import sys
import time
import subprocess
import termios

BASE_DIR = "/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4"
DEV = "/dev/ttyACM0"

def configure_port(port):
    try:
        fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(fd)
        # 115200 baud, 8N1, raw (Sapphire SoC UART)
        attrs[4] = termios.B115200  # ispeed
        attrs[5] = termios.B115200  # ospeed
        attrs[0] = 0              # iflag
        attrs[1] = 0              # oflag
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag
        attrs[3] = 0              # lflag
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        return fd
    except Exception as e:
        print(f"[WARN] Could not configure {port}: {e}")
        return None

def main():
    # 1. Open and configure serial port before flashing
    fd = configure_port(DEV)
    if fd is not None:
        # Flush existing buffer
        try:
            while True:
                buf = os.read(fd, 1024)
                if not buf: break
        except BlockingIOError:
            pass

    # 2. Run flash script
    print("[*] Running flash_soc.py...")
    res = subprocess.run(["python3", "FPGA_code/scripts/flash_soc.py"], cwd=BASE_DIR)
    if res.returncode != 0:
        print("[!] Flashing failed.")
        sys.exit(1)

    # 3. Read output for 18 seconds
    print("\n[*] Capturing UART output from /dev/ttyACM0 for 18 seconds...\n" + "="*50)
    t0 = time.time()
    captured = bytearray()
    if fd is not None:
        while time.time() - t0 < 18.0:
            try:
                chunk = os.read(fd, 256)
                if chunk:
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.flush()
                    captured.extend(chunk)
            except BlockingIOError:
                time.sleep(0.05)
        os.close(fd)
    print("\n" + "="*50)
    print(f"[*] Done. Total bytes captured: {len(captured)}")

if __name__ == "__main__":
    main()

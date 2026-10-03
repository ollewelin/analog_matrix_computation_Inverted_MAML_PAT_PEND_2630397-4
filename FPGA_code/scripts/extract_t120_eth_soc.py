#!/usr/bin/env python3
"""
Condense and extract vital Sapphire SoC, Ethernet, and lwIP assets from
messy legacy T120 reference project into clean staging directory.
"""
import os
import shutil
import re

SRC_DIR = "/home/olle/efinity_p2/BRAM/T120F324_A"
STAGING_DIR = "FPGA_code/ref_staging/t120_eth_soc"

KEYWORDS = [
    "mdio", "phy", "eth", "udp", "tcp", "sapphire", "soc",
    "rtl8211", "rgmii", "rmii", "lwip", "bsp"
]

def scan_and_stage():
    os.makedirs(STAGING_DIR, exist_ok=True)
    staged = []

    # 1. Scan top-level files in SRC_DIR
    for item in os.listdir(SRC_DIR):
        full_path = os.path.join(SRC_DIR, item)
        lower_name = item.lower()
        if os.path.isfile(full_path):
            if any(k in lower_name for k in KEYWORDS) or item in ["top_level.sv", "rebuild_and_flash.sh"]:
                # skip camera-specific or video dump files
                if "video" in lower_name or "frame" in lower_name or "mipi" in lower_name or "cam" in lower_name:
                    continue
                dest = os.path.join(STAGING_DIR, item)
                shutil.copy2(full_path, dest)
                staged.append(item)

    print(f"Staged {len(staged)} top-level reference files:")
    for f in staged:
        print(f" - {f}")

    # 2. Check for ip directory
    ip_src = os.path.join(SRC_DIR, "ip")
    if os.path.isdir(ip_src):
        ip_dest = os.path.join(STAGING_DIR, "ip")
        os.makedirs(ip_dest, exist_ok=True)
        for ip_item in os.listdir(ip_src):
            if any(k in ip_item.lower() for k in ["soc", "sapphire", "mdio", "eth", "mac", "pll"]):
                s_path = os.path.join(ip_src, ip_item)
                d_path = os.path.join(ip_dest, ip_item)
                if os.path.isdir(s_path):
                    if os.path.exists(d_path):
                        shutil.rmtree(d_path)
                    shutil.copytree(s_path, d_path)
                    print(f" - Copied IP core: {ip_item}")

    # 3. Check for embedded_sw
    sw_src = os.path.join(SRC_DIR, "T120_embedded_sw")
    if os.path.isdir(sw_src):
        sw_dest = os.path.join(STAGING_DIR, "embedded_sw")
        if os.path.exists(sw_dest):
            shutil.rmtree(sw_dest)
        shutil.copytree(sw_src, sw_dest)
        print(" - Copied embedded software tree (T120_embedded_sw)")

if __name__ == "__main__":
    scan_and_stage()

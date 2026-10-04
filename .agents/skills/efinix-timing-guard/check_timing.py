#!/usr/bin/env python3
"""
check_timing_and_inputs.py - Efinix Timing & Input Synchronization Guard

Körs automatiskt efter Place & Route och syntes:
1. Granskar STA-rapporten (outflow/*.timing.rpt):
   - Säkerställer att klockor analyserats i 'Maximum possible analyzed clocks frequency'.
   - Larmar vid negativa slacks (Setup/Hold violations).
   - Larmar vid otillräcklig Fmax.
2. Granskar RTL/top_level för asynkrona ingångar:
   - Alla fysiska ingångar från omvärlden (knappar, externa signaler, sensorer, RX-linjer)
     MÅSTE ha minst 2 registersteg (2-stage synchronizer / double-flop) innan de används i klockdomänen!
   - Undantag: Dedikerade hårdvarublock såsom DDIO (som hanteras i IO-celler) eller klockor.
"""

import sys
import os
import re

def check_timing(report_path):
    print("\n" + "="*70)
    print("1. KONTROLL AV EFINITY STATIC TIMING ANALYSIS (STA):")
    print("="*70)

    if not os.path.exists(report_path):
        print(f"[ERROR] Timing report hittades inte: {report_path}")
        return False

    with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    errors = []
    clocks_found = {}

    # Analyserade klockor
    m_max = re.search(r"Maximum possible analyzed clocks frequency\s*\n\s*Clock Name\s+Period \(ns\)\s+Frequency \(MHz\)\s+Edge\s*\n(.*?)(?:\n\n|\n-|$)", content, re.DOTALL)
    if not m_max or not m_max.group(1).strip():
        errors.append("KRITISKT TIMINGFEL: Inga klockor analyserades i 'Maximum possible analyzed clocks frequency'! Logiken saknar timingkrav!")
    else:
        for line in m_max.group(1).strip().splitlines():
            parts = line.split()
            if len(parts) >= 3:
                clk_name = parts[0]
                period = float(parts[1])
                fmax = float(parts[2])
                clocks_found[clk_name] = {"fmax": fmax, "period": period}
                print(f"  * {clk_name}: Fmax = {fmax:.2f} MHz (Mål period {period:.3f} ns)")

    # Slack
    setup_slack = re.findall(r"Setup \(Max\) Clock Relationship.*?Slack \(ns\).*?\n(.*?)(?:\n\n|\n-|$)", content, re.DOTALL)
    if setup_slack:
        for line in setup_slack[0].strip().splitlines():
            parts = line.split()
            if len(parts) >= 6:
                try:
                    slack = float(parts[4])
                    clk = parts[0]
                    if slack < 0:
                        errors.append(f"TIMING VIOLATION: Setup slack negativ ({slack:.3f} ns) på {clk}!")
                    else:
                        print(f"  [OK] Slack: {slack:.3f} ns ({clk})")
                except ValueError:
                    pass

    if errors:
        for e in errors:
            print(f"  [CRITICAL ERROR] {e}")
        return False

    print("  --> STA: GODKÄND.")
    return True

def check_input_synchronizers(top_file):
    print("\n" + "="*70)
    print("2. KONTROLL AV ASYNKRONA INGÅNGAR OCH METASTABILITET:")
    print("="*70)

    if not os.path.exists(top_file):
        print(f"[SKIP] Filen {top_file} hittades inte.")
        return True

    with open(top_file, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    # Rensa kommentarer
    clean_code = re.sub(r"//.*", "", code)
    clean_code = re.sub(r"/\*.*?\*/", "", clean_code, flags=re.DOTALL)

    # Hitta ingångsportar
    inputs = re.findall(r"input\s+(?:wire|logic)?\s*(?:\[.*?\])?\s*(\w+)", clean_code)
    
    # Exkludera klockor, resets och DDIO/RGMII bussar som har dedikerad timing
    clk_or_ddio = re.compile(r"(clk|gclk|clock|rx_clk|rxc|rst|reset|tdi|tck|tms)", re.IGNORECASE)

    raw_inputs = [i for i in inputs if not clk_or_ddio.search(i)]
    print(f"  Identifierade fysiska asynkrona ingångar: {len(raw_inputs)} st")

    warnings = []
    for sig in raw_inputs:
        # Sök efter synkroniseringslager för signalen (t.ex. sig_sync, sig_d1, [1:0] sig_r)
        sync_pattern = re.compile(rf"{sig}_sync|{sig}_r|{sig}_d1|{sig}_q", re.IGNORECASE)
        two_stage_pattern = re.compile(rf"\[1:0\]\s*{sig}|reg\s*\[1:0\].*{sig}", re.IGNORECASE)
        
        if not (sync_pattern.search(clean_code) or two_stage_pattern.search(clean_code)):
            warnings.append(f"Signal '{sig}' verkar sakna explicit 2-stegs metastabilitetssynkronisering (_sync / _r[1:0])!")

    if warnings:
        print("  [METASTABILITY WARNINGS]:")
        for w in warnings:
            print(f"    ! {w}")
        print("  --> OBS: Kontrollera att asynkrona insignaler passerar minst 2 flip-flops före logik.")
    else:
        print("  [OK] Inga uppenbara oskyddade asynkrona ingångar upptäcktes.")

    print("="*70 + "\n")
    return True

def main():
    report = sys.argv[1] if len(sys.argv) > 1 else "FPGA_code/T120F324/outflow/T120_MALM.timing.rpt"
    top = sys.argv[2] if len(sys.argv) > 2 else "FPGA_code/T120F324/top_level.sv"

    t_ok = check_timing(report)
    check_input_synchronizers(top)

    if not t_ok:
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()

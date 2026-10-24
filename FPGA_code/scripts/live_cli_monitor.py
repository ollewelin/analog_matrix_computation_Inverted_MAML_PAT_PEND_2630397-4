#!/usr/bin/env python3
"""
live_cli_monitor.py - Real-Time Terminal Dashboard for Silicon Neural Training
==============================================================================
Reads FPGA_code/docs/live_10min_training_progress.json every 1.0s and renders
a clean, live updating terminal dashboard with ASCII progress bar, Loss, RMSE,
ENOB, and per-column errors.
"""

import os
import sys
import time
import json
from pathlib import Path

PROGRESS_FILE = Path(__file__).resolve().parent.parent / "docs" / "live_10min_training_progress.json"

# ANSI Colors
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_CYAN    = "\033[36m"
C_GREEN   = "\033[32m"
C_YELLOW  = "\033[33m"
C_RED     = "\033[31m"
C_BLUE    = "\033[34m"
C_MAGENTA = "\033[35m"
C_DIM     = "\033[2m"
CLEAR_SCREEN = "\033[2J\033[H"


def render_dashboard(data: dict):
    elapsed = data.get("elapsed_sec", 0.0)
    duration = data.get("duration_sec", 600.0)
    pct = data.get("progress_pct", 0.0)
    epoch = data.get("latest_epoch", 0)
    loss = data.get("latest_loss", 0)
    rmse = data.get("latest_rmse", 0.0)
    enob = data.get("latest_enob_comp", 0.0)
    pts = data.get("num_checkpoints", 0)
    tail = data.get("trajectory_tail", [])

    # Progress bar (35 chars)
    bar_len = 35
    filled = int(bar_len * (pct / 100.0))
    bar = "█" * filled + "░" * (bar_len - filled)

    rem_sec = max(0.0, duration - elapsed)

    out = []
    out.append(f"{C_BOLD}{C_CYAN}╔══════════════════════════════════════════════════════════════════════╗{C_RESET}")
    out.append(f"{C_BOLD}{C_CYAN}║     INVERTED MAML — REAL-TIME SILICON TRAINING DASHBOARD (T120)      ║{C_RESET}")
    out.append(f"{C_BOLD}{C_CYAN}╚══════════════════════════════════════════════════════════════════════╝{C_RESET}")
    out.append("")
    out.append(f"  {C_BOLD}Progress:{C_RESET} [{C_GREEN}{bar}{C_RESET}] {C_BOLD}{pct:5.1f}%{C_RESET}  ({elapsed:5.1f}s / {duration:5.1f}s)")
    out.append(f"  {C_BOLD}Status:{C_RESET}   {C_GREEN}● LIVE ON-CHIP GRADIENT DESCENT (MODE C){C_RESET} | Tid kvar: {C_YELLOW}{int(rem_sec)}s{C_RESET}")
    out.append("")
    out.append(f"  {C_DIM}┌─────────────────────────┬─────────────────────────┬─────────────────────────┐{C_RESET}")
    out.append(f"  {C_DIM}│{C_RESET} {C_BOLD}Epok (Indata-mönster){C_RESET}   {C_DIM}│{C_RESET} {C_BOLD}Aktuell Loss / RMSE{C_RESET}     {C_DIM}│{C_RESET} {C_BOLD}Effektiv Precision (ENOB){C_RESET}{C_DIM}│{C_RESET}")
    out.append(f"  {C_DIM}├─────────────────────────┼─────────────────────────┼─────────────────────────┤{C_RESET}")
    out.append(f"  {C_DIM}│{C_RESET}  {C_CYAN}{C_BOLD}{epoch:6d}{C_RESET} kisel-epoker   {C_DIM}│{C_RESET}  {C_YELLOW}{rmse:5.1f} LSB{C_RESET} ({loss:7d})   {C_DIM}│{C_RESET}   {C_GREEN}{C_BOLD}{enob:4.2f} bitar{C_RESET} (12-bit ADC) {C_DIM}│{C_RESET}")
    out.append(f"  {C_DIM}└─────────────────────────┴─────────────────────────┴─────────────────────────┘{C_RESET}")
    out.append("")

    if tail:
        last = tail[-1]
        errs = last.get("err49", [0]*6)
        x_ref = last.get("x_ref", [0]*6)
        z_targ = last.get("z_target", [0]*6)
        adc = last.get("adc49", [0]*6)

        out.append(f"  {C_BOLD}Kolumn-status för senaste indatavektorn:{C_RESET}")
        out.append(f"  {C_DIM}Col    Mål (Z_target)   Mätt (ADC_49)     Fel (LSB)    Stapel{C_RESET}")
        out.append(f"  {C_DIM}─────  ───────────────  ───────────────  ────────────  ────────────────────{C_RESET}")
        for c in range(6):
            e = errs[c]
            col_color = C_GREEN if abs(e) < 400 else (C_YELLOW if abs(e) < 1000 else C_RED)
            # Mini bar
            b_bars = min(15, int(abs(e) / 130))
            b_str = "■" * b_bars
            sign = "+" if e >= 0 else "-"
            out.append(f"  C{c+1}:      {z_targ[c]:6d} LSB       {adc[c]:6d} LSB    {col_color}{sign}{abs(e):5.0f} LSB{C_RESET}  {col_color}{b_str}{C_RESET}")

    out.append("")
    # Sparkline of last 10 points
    if len(tail) >= 3:
        spark_rmses = [p["rmse"] for p in tail]
        min_r = min(spark_rmses)
        max_r = max(spark_rmses)
        out.append(f"  {C_BOLD}Senaste trenden (RMSE sista 10s):{C_RESET} {C_MAGENTA}{[round(r, 0) for r in spark_rmses]}{C_RESET}")
        out.append(f"  {C_DIM}(Min: {min_r:.1f} LSB | Max: {max_r:.1f} LSB | Loggpunkter: {pts}){C_RESET}")

    out.append("")
    out.append(f"  {C_DIM}Tryck Ctrl+C för att avsluta monitorn (träningen fortsätter i bakgrunden).{C_RESET}")
    return "\n".join(out)


def main():
    print(CLEAR_SCREEN)
    while True:
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, "r") as f:
                    data = json.load(f)
                sys.stdout.write(CLEAR_SCREEN + render_dashboard(data) + "\n")
                sys.stdout.flush()
                if data.get("progress_pct", 0.0) >= 100.0:
                    print(f"\n{C_GREEN}{C_BOLD}[✓] 10-Minuters-träningen är SLUTFÖRD! Rapport genereras...{C_RESET}\n")
                    break
            except Exception:
                pass
        else:
            sys.stdout.write(CLEAR_SCREEN + f"{C_YELLOW}Väntar på att live_10min_training_progress.json ska skapas...{C_RESET}\n")
            sys.stdout.flush()
        time.sleep(1.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C_RESET}Monitor avslutad.")


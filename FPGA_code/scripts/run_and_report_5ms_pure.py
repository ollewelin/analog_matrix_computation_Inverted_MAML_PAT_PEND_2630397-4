#!/home/olle/anaconda3/bin/python
"""
run_and_report_5ms_pure.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Unified Parameter Benchmark Orchestrator:
Executes Mode A training on Card 2 with selectable parameters (LR, Lambda, Fig 7 Variance, Swing),
and automatically produces:
1. Complete JSON telemetry log
2. 3-panel PNG figure with vertical phase dividers & English annotations
3. Standardized 2-page publication PDF report
4. Technical GitHub Markdown report (including all 6x6 disturbance matrices)
5. Copies all artifacts to active conversation artifact directory
"""

from __future__ import annotations
import sys
import subprocess
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from FPGA_code.scripts.generate_5ms_pure_short_report import build_short_report

LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
PYTHON_EXE = "/home/olle/anaconda3/bin/python"


def main():
    parser = argparse.ArgumentParser(description="Unified Mode A 5.0ms Hardware Benchmark & Automated Report Generator")
    parser.add_argument("--epochs", type=int, default=1000, help="Total epochs (default 1000 for 4-phase ablation)")
    parser.add_argument("--lr", type=float, default=0.16, help="Inner loop learning rate (e.g. 0.08, 0.16, 0.25)")
    parser.add_argument("--reg-lambda", type=int, default=150, help="L2 regularization lambda (e.g. 150, 341, 1024)")
    parser.add_argument("--variance", "--w33-variance-lsb-range", dest="variance", type=int, default=4,
                        help="Patent Fig 7 hidden offset range in LSB (default 4)")
    parser.add_argument("--d-line", type=int, default=2, help="Input swing divider: 2 for +/-40 LSB, 1 for +/-80 LSB")
    parser.add_argument("--noise-color", choices=["toeplitz", "white"], default="toeplitz")
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--compress-m33-weight", type=float, default=1.0)
    parser.add_argument("--tag", type=str, default=None, help="Custom tag (if omitted, auto-generated from parameters)")
    parser.add_argument("--skip-run", action="store_true", help="Skip hardware run and only regenerate reports from existing JSON")
    args = parser.parse_args()

    # Construct standard tag if not given
    if not args.tag:
        lr_str = f"lr{str(args.lr).replace('.', 'p')}"
        swing_str = f"swing{80 if args.d_line == 1 else 40}"
        var_str = f"var{args.variance}"
        k_str = f"_k{args.k_batch}" if args.k_batch != 20 else ""
        comp_str = f"_comp{int(args.compress_m33_weight)}" if args.compress_m33_weight > 1.0 else ""
        abl_str = "_ablation" if args.epochs >= 600 else ""
        tag = f"{args.noise_color}_reg{args.reg_lambda}_{lr_str}_{swing_str}_{var_str}{k_str}{comp_str}{abl_str}"
    else:
        tag = args.tag

    out_stem = f"mode_a_{args.epochs}ep_5ms_pure_{tag}"
    json_path = LOGS_DIR / f"{out_stem}.json"
    pdf_path = DOCS_DIR / f"INVERTED_MAML_CARD2_{args.epochs}EP_5MS_PURE_{tag.upper()}_REPORT.pdf"
    md_path = DOCS_DIR / f"INVERTED_MAML_CARD2_{args.epochs}EP_5MS_PURE_{tag.upper()}_REPORT.md"

    print("=" * 95)
    print("INVERTED MAML: UNIFIED 5.0 ms PARAMETER BENCHMARK & REPORT ORCHESTRATOR")
    print(f"Parameters: Epochs={args.epochs}, LR={args.lr}x, λ={args.reg_lambda}, Disturbance=±{args.variance} LSB, Swing=±{80 if args.d_line==1 else 40} LSB")
    print(f"Output Stem: {out_stem}")
    print(f"Target PDF:  {pdf_path.name}")
    print("=" * 95)

    if not args.skip_run:
        cmd = [
            PYTHON_EXE,
            str(REPO_ROOT / "FPGA_code" / "scripts" / "run_card2_5ms_pure.py"),
            "--epochs", str(args.epochs),
            "--lr", str(args.lr),
            "--reg-lambda", str(args.reg_lambda),
            "--w33-variance-lsb-range", str(args.variance),
            "--d-line", str(args.d_line),
            "--noise-color", str(args.noise_color),
            "--rho", str(args.rho),
            "--k-batch", str(args.k_batch),
            "--compress-m33-weight", str(args.compress_m33_weight),
            "--tag", tag,
        ]
        print(f"\n[*] Startar hårdvarukörning på Kort 2...")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"[!] Hårdvarukörning misslyckades med returkod {res.returncode}!")
            sys.exit(res.returncode)

    if not json_path.exists():
        print(f"[!] Fel: Telemetrifilen hittades inte: {json_path}")
        sys.exit(1)

    print(f"\n[*] Bygger publiceringsrapport (PDF + MD) från: {json_path.name}")
    build_short_report(json_path, pdf_path, md_path)

    print("\n" + "=" * 95)
    print("[+] ALLA ARTEFAKTER GENERERADE OCH PUBLICERADE:")
    print(f"    - JSON Logg:  {json_path}")
    print(f"    - PDF Rapport: {pdf_path}")
    print(f"    - MD Rapport:  {md_path}")
    print("=" * 95)


if __name__ == "__main__":
    main()


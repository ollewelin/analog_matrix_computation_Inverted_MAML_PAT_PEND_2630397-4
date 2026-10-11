#!/home/olle/anaconda3/bin/python3
"""
Entrypoint for the Inverted MAML Analog Matrix Development Platform GUI.
Automatically re-executes under /home/olle/anaconda3/bin/python3 if launched
with system python3 where PyQt5/matplotlib are not installed.
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ANACONDA_PY = "/home/olle/anaconda3/bin/python3"
try:
    import PyQt5  # noqa: F401
    import matplotlib  # noqa: F401
except ImportError:
    if os.path.exists(ANACONDA_PY) and os.path.realpath(sys.executable) != os.path.realpath(ANACONDA_PY):
        os.execv(ANACONDA_PY, [ANACONDA_PY] + sys.argv)
    raise

# Ensure repository root is on sys.path
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PyQt5.QtWidgets import QApplication
from gui.main_window import InvertedMamlMainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Inverted MAML Analog Matrix Platform GUI")
    parser.add_argument("--host", default="192.168.1.50", help="T120 FPGA IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=5000, help="T120 UDP port (default: 5000)")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run automated headless GUI & Pop-Up 3D visualizer smoke test and exit",
    )
    args = parser.parse_args()

    if args.self_test and "DISPLAY" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    win = InvertedMamlMainWindow(host=args.host, port=args.port)
    win.show()

    if args.self_test:
        # Exercise all major GUI features: Pop-Up 3D window, Heater Arm, Auto Bit Test, Cell Diagnostics
        win._on_open_3d_popup()
        win._apply_heater_preset([60, 40, 20, 80])
        win._on_step_outer_clicked()
        u_bits, c_bits, delta = win.client.run_auto_bit_precision_test()
        rep = win.diag_engine.run_full_cell_diagnostics()
        win.btn_arm_heater.setChecked(False)
        app.processEvents()
        print(f"[GUI SELF-TEST PASS] Auto Bit Test: Uncomp={u_bits:.2f}b -> Comp={c_bits:.2f}b (Delta=+{delta:.2f}b)")
        print(f"[GUI SELF-TEST PASS] {rep.summary_text}")
        print("[GUI SELF-TEST PASS] Main Window + Detachable 3D Loss Landscape Pop-Up Window verified.")
        if win.popup_3d is not None:
            win.popup_3d.close()
        win.close()
        return 0

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())


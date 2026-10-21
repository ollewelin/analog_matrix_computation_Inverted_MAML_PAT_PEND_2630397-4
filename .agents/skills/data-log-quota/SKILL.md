---
name: data-log-quota
description: Strict quota enforcement and safety management for hardware data logs, dumps, captures, and test exports. Enforces a hard ceiling of 100 MB total log data, prohibits continuous background streaming to disk, permits burst writes on explicit user command, and provides automated quota auditing and cleanup tools.
---

# Hardware Data Log Quota Management Skill (Max 100 MB)

This skill manages and enforces a strict **100 Mbyte ceiling** across all hardware data logs, dumps, ADC captures, and test exports (`FPGA_code/docs/`). It prevents accidental disk exhaustion on the host development machine while allowing high-speed multi-megabyte burst logging whenever explicitly requested by the user.

---

## 1. Operating Rules & Hardware Policy

### Rule 1: Zero Continuous Disk Streaming (Strictly Forbidden)
- **Do NOT** run continuous, unbounded background disk-logging loops.
- During continuous operation (e.g., continuous 100 Hz 2T1C refresh, continuous 500 kHz ADC sampling, or live GUI telemetry), all real-time ADC buffers, UDP packets, and Hadamard pulses must remain in **RAM / network socket buffers**.
- Streaming live telemetry to disk without explicit user command is strictly prohibited.

### Rule 2: On-Demand Burst Data Writes (Fully Permitted)
- Multi-megabyte data writes are **fully permitted as on-demand bursts** triggered by explicit user commands or actions:
  - GUI **"Export Results (Full Data Dump JSON & CSV)"** button.
  - GUI **"Capture & Dump Live Hadamard 24µs Waveform"** button.
  - CLI diagnostic runs (e.g. `run_analog_diagnostics.py`).
- Bursts may write full raw captures, JSON dictionaries, and high-resolution CSV matrices, provided total log usage remains within the 100 MB ceiling.

### Rule 3: 100 Mbyte Hard Quota Ceiling
- The total cumulative size of transient data logs and test exports must **never exceed 100 MB** (104,857,600 bytes).
- Tracked file types include:
  - `maml_gui_full_dump_*.json`
  - `maml_gui_hadamard_dump_*.csv`
  - `maml_gui_cell_eval_*.json`
  - `multiplier_dynamics_self_test_*.csv` / `*.json`
  - `t120_la_bare_metal_captures.json`
  - Transient raw `.bin` or `.csv` test buffers.

### Rule 4: Permanent Documentation Protection
- The quota manager **NEVER** touches or deletes permanent documentation, specifications, or source code:
  - Markdown files (`*.md`)
  - PDFs (`*.pdf`)
  - Verilog / SystemVerilog HDL (`*.v`, `*.sv`)
  - C / RISC-V firmware (`*.c`, `*.h`)
  - Python scripts (`*.py`)
  - Hardware schematic & BOM files (`*.csv` under `EasyEDA/`)
- Only transient hardware test captures in `FPGA_code/docs/` are eligible for quota pruning.

---

## 2. Command Line Usage

### View Quota Status & File Table
```bash
python3 .agents/skills/data-log-quota/check_quota.py --status
```
Example Output:
```text
======================================================================
 MAML HARDWARE DATA LOG QUOTA STATUS (MAX 100 MB CEILING)
======================================================================
 Log Directory:   .../FPGA_code/docs
 Total Log Files: 10
 Current Usage:   8.65 MB / 100.0 MB (8.6%)
 Remaining Quota: 91.35 MB
----------------------------------------------------------------------
 [OK] Data log usage is well within safe 100 MB quota bounds.
======================================================================
```

### Automated Check (CI / Pre-Test Script)
Exits with code `0` if within 100 MB, or code `1` if the quota is breached:
```bash
python3 .agents/skills/data-log-quota/check_quota.py --check
```

### Prune Oldest Transient Dumps to Target MB (e.g. 80 MB)
```bash
# Dry run (simulation only)
python3 .agents/skills/data-log-quota/check_quota.py --prune --target-mb 80 --dry-run

# Execute pruning of oldest transient dumps
python3 .agents/skills/data-log-quota/check_quota.py --prune --target-mb 80
```

---

## 3. Python API Integration

Before saving large burst files in GUI or CLI scripts, call `enforce_quota_before_write`:

```python
import sys
from pathlib import Path

# Add skill path to sys.path
SKILL_DIR = Path(__file__).resolve().parent.parent / ".agents" / "skills" / "data-log-quota"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from check_quota import enforce_quota_before_write, get_quota_status

# Check quota before saving burst
status = get_quota_status(max_mb=100.0)
if status["usage_pct"] >= 95.0:
    enforce_quota_before_write(incoming_bytes=5_000_000, max_mb=100.0, auto_prune=True)
```


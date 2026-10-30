---
name: t120-version-guard
description: Automatic hardware and software version verification protocol for Trion T120 Master SoC. Verifies HW logic synthesis version and SW C-firmware version via UDP telemetry before experiments, and automatically reprograms the FPGA via JTAG if a version mismatch or offline state is detected.
---

# T120 Version Guard & Automatic Reprogramming Protocol

## 1. Scope & Mandatory Rule
Whenever a new FPGA synthesis is completed, and **before starting any new silicon experiment or benchmark campaign**, the agent MUST execute the version guard verification.

If the board reports a version mismatch, an outdated build, or is unprogrammed/offline, the protocol automatically executes JTAG programming with the correct target bitstream and firmware.

---

## 2. Command Line Usage

### Quick Verification Check
```bash
python3 FPGA_code/scripts/verify_and_guard_version.py
```

### Force Reprogramming Regardless of Active Version
```bash
python3 FPGA_code/scripts/verify_and_guard_version.py --force-reprogram
```

### Custom Version Target
```bash
python3 FPGA_code/scripts/verify_and_guard_version.py --expected-hw 0x20261030 --expected-sw v2.1-MAML
```

---

## 3. Python Integration in Test Runners

Any Python runner script (such as batch training, 1000-epoch benchmarks, or characterization sweeps) should import and run `ensure_version_guard` at startup:

```python
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

# Guard ensures correct HW logic and SW firmware before executing tests
version_info = ensure_version_guard(
    host="192.168.1.50",
    port=5000,
    expected_hw="0x20261030",
    expected_sw="v2.1-MAML"
)
print(f"Verified: HW {version_info['hw_version']}, SW {version_info['sw_version']}")
```

---

## 4. Hardware & Software Register Architecture

### Hardware Logic Register (`t120_analog_io_ctrl.sv`)
- **Base Address:** `0xF810_4000` (`AIO_BASE`)
- **Register `0x018` (`AIO_HW_VERSION`):** RO 32-bit BCD/Hex synthesis date (`0x20261030` = 2026-10-30).
- **Register `0x01C` (`AIO_HW_ID`):** RO 32-bit ASCII subsystem tag (`0x4D414D31` = "MAM1", Mode A Logic v1).

### Software Firmware Version (`main.c` / `maml_platform.c`)
- Embedded string: `T120_SOC_ETH_FW v2.1-MAML (SW Build <__DATE__> <__TIME__>)`.
- Queryable via ASCII UDP command `"VERSION"` on Port 5000.
- Telemetry shadow registers reflect active `reg_lambda_q16` and compensation authority in real time.


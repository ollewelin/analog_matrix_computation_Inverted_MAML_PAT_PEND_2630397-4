# Experiment Plan: Live Mid-Phase Dynamic `M(3)` L2 Regularization Switching (`4× -> 1×`)

**Target Hardware:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 1k` = 50/50 Passive Summing Attenuator)  
**Baseline Discovery (2026-11-27):**  
- With **`1×` L2** on `M(3)` (`λ_M3 = λ_M8 = 1920`), extended `120 s` ON phases at `60%` PWM heat achieve **`+1.19 b` detrended lift** (`+4.177` score), reaching **`7.87 b` (P7)** and **`8.10 b` (P11)** via a ~20–40 s saddle-crossing jump where `W(3)` briefly rises to `20–30 LSB` before relaxing to `4–6 LSB`.
- With **`4×` L2** on `M(3)` (`λ_M3 = 7,680`, commit `eef714d`), `W(3)` stays suppressed below `7–9 LSB`, completely blocking the saddle-crossing jump (`+0.00 b` lift, `-0.477` score).

---

## 1. Scientific Objective

Test dynamically **in a single continuous warm ON phase** (with zero weight resets and continuous SGD + momentum) whether releasing `M(3)` from **`4×` L2 $\to$ `1×` L2** mid-phase triggers an immediate saddle-crossing breakout ("lossnar"):

- **First Half of Each `120 s` ON Phase (`0–60 s`):** Run `g_reg_m3_mult = 4` (`4×` L2 on `M(3)`). Expected behavior: ENOB stays trapped near the uncompensated thermal drift floor (`~6.1–6.8 b`), `W(3) ≤ 7 LSB`.
- **Second Half of Each `120 s` ON Phase (`60–120 s`):** Switch live over UDP to `g_reg_m3_mult = 1` (`1×` L2 on `M(3)`), keeping all current `M(3)` / `M(8)` weights and momentum buffers intact. Expected behavior: `M(3)` frees up to explore `20–30 LSB`, unlocks `Sigmoid 4`, and triggers a sharp **`+1.0` to `+1.8 b`** precision breakout straight toward **`~8.0 b`** right after the `60 s` mark.

*(Optional Follow-Up Test B — Inverse Schedule `1× -> 4×`:* Run `1×` for `0–60 s` to cross into the deep basin, then engage `4×` at `60–120 s` to evaluate whether late `M(3)` regularization prevents shallow-attractor lock-in on phases like P9/P13.*)

---

## 2. Implementation Steps (Next Session)

### Step 1 — Firmware UDP Control (`maml_platform.c`)
1. Under `MAML_CMD_SET_W33` (`0x1E`), add subcommand `8` (`len >= 7`, `<BB` = `[8, mult]`):
   - Clamp `mult` to `[1..16]` and assign `g_reg_m3_mult = mult;`.
   - Zero impact on hardware timing or EMC; takes effect on the very next `MAML_CMD_BATCH_STEP`.
2. Compile and flash Card 2 via `python3 FPGA_code/scripts/flash_soc.py`, then verify via `python3 FPGA_code/scripts/verify_and_guard_version.py`.

### Step 2 — Host Runner Schedule (`run_card1_extended_thermal_sweep.py`)
1. Add optional CLI arguments `--m3-reg-mult-first` (default `1`), `--m3-reg-mult-second` (default `1`), and `--m3-reg-switch-sec` (default `60.0`).
2. Inside the `120 s` warm ON phases (`time_in_phase < switch_sec` vs `>= switch_sec`), send `client._send_binary(0x1E, struct.pack("<BB", 8, mult))` on transitions and record `m3_reg_mult` in every `pair_record`.
3. Launch on Card 2 (`1k/1k`) with `60%` PWM heat, `90 s` cooldown + fresh cold DC cal, `120 s ON / 30 s OFF`, and `bit_slicing_live_gui.py` active on `DISPLAY=:1`:
   - First half (`0–60 s`): `4×` `M(3)` L2
   - Second half (`60–120 s`): `1×` `M(3)` L2

### Step 3 — Comparative Report & 6-Color Per-Column Figures (`generate_card2_1k1k_report.py`)
1. Overlay vertical dashed lines at the exact `4× -> 1×` mid-phase switch points (`t_in_phase = 60 s`) on the 4-panel timeline and the four **6-color per-column weight plots** (`W8 MSB`, `W8 LSB`, `W3 MSB`, `W3 LSB`, `Col 0–5`, `R0–R5`).
2. Compare `0–60 s` (`4×` trapped) vs. `60–120 s` (`1×` released) precision, loss reduction ratio, and `W(3)`/`W(8)` trajectories.
3. Archive and commit report, figures, and DC calibration.

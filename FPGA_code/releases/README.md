# Inverted MAML Hardware & Firmware Official Releases Index
**Patent Pending SE 2630397-4 | Open Science Hardware**  
**Repository Path:** `FPGA_code/releases/`

This directory serves as the immutable release archive for verified hardware bitstreams, firmware, host drivers, and experimental benchmark datasets on physical Inverted MAML silicon (Card 2, Trion T120 Master SoC + Trion T20 Coprocessor).

---

## 📦 Verified Release Packages

| Release Package | Date | Target Benchmark & Hardware State | Peak Performance | Key Deliverables |
| :--- | :---: | :--- | :---: | :--- |
| [**`Release_20261104_ModeA_5ms_Pure_Spatial_Breakthrough`**](./Release_20261104_ModeA_5ms_Pure_Spatial_Breakthrough/) | 2026-11-04 | **Pure Spatial 5.0 ms Snapshot**<br/>- Card 2 (1k/3.3k Attenuator)<br/>- Naked Batch $K=1$ Online SGD<br/>- LLM Toeplitz Data ($\rho=0.85$)<br/>- Patent Fig 7 $\pm 5\text{ LSB}$ Disturbance | **$7.17\text{ b}$ Peak ENOB**<br/>($605.5\text{ LSB}^2$)<br/>**$7.72\times$ Ablation Contrast** | - T120/T20 bitstreams & hex<br/>- Verilog/SystemVerilog sources<br/>- RISC-V C Firmware (`v2.2-MAML`)<br/>- Python host driver & reports |
| [**`Release_20261105_ModeA_Broadened_Temporal_WhiteNoise_and_ModeB_CrossCheck`**](./Release_20261105_ModeA_Broadened_Temporal_WhiteNoise_and_ModeB_CrossCheck/) | 2026-11-05 | **Broadened Temporal Window [4.5..5.5 ms] & Mode B Control Cross-Check**<br/>- 11 Strata, 11,000 updates<br/>- Uncorrelated White Noise Stream<br/>- Mode A (Jumpers IN) vs. Mode B (Jumpers OUT)<br/>- Patent Fig 7 $\pm 5\text{ LSB}$ Disturbance | **$6.29\text{ b}$ Peak ENOB**<br/>($2\,063\text{ LSB}^2$ in Mode A)<br/>**$6.0\times$ Mode B Error Ratio**<br/>**$5.08\times$ vs $1.14\times$ Contrast** | - Unified C Firmware & Bitstreams<br/>- Mode A & Mode B raw JSON logs<br/>- 10-page White Noise PDF report<br/>- 4-page Cross-Check PDF report<br/>- Overlay comparison telemetry |
| [**`Milestone_1_ModeA_5ms_Verified`**](./Milestone_1_ModeA_5ms_Verified/) | 2026-10-25 | **Initial Mode A Proof-of-Concept**<br/>- 1k/5.1k Attenuator<br/>- Batched SGD ($K=20$), 5.0 ms static | $4.85\text{ b}$ Peak ENOB | - Early bitstreams & test logs |
| [**`T20_Custom_Verified`**](./T20_Custom_Verified/) | 2026-11-02 | **T20 Coprocessor Verified Configuration** | Synchronous bus bridge | - T20 logic & bitstream |
| [**`v1.2_bridge_udp_version`**](./v1.2_bridge_udp_version/) | 2026-10-10 | **Trion T120 Master SoC Baseline Bridge** | Base UDP comms verified | - Baseline bridge logic |

---

## 🔬 Scientific Summary of Recent Releases

### 1. Release 20261104: Pure Spatial 5.0 ms Breakthrough
- **Hardware Upgrade:** Passive summing attenuator upgraded to $1\text{ k}\Omega / 3.3\text{ k}\Omega$ ($-12.7\text{ dB}$), providing $+42\%$ correction current into ColTIA virtual grounds.
- **Naked Batch $K=1$ Protocol:** Single stochastic forward pass per epoch exposed true physical silicon baseline of $3.33\text{ b}$ ($133\,318\text{ LSB}^2$).
- **Disturbance Absorption:** Successfully countered severe $\pm 5\text{ LSB}$ non-stationary hardware shifts across Matrix 33 (Patent SE 2630397-4 Fig 7 Emulator).
- **Result:** $7.17\text{ b}$ peak precision, $7.72\times$ ablation contrast upon zeroing weights ($W=0$), and relaxed weights ($|W_8| \le 25\text{ LSB}$) preserving $>95\text{ LSB}$ linear headroom.

### 2. Release 20261105: Temporal Dynamic Window & Mode B Negative Control Cross-Check
- **Dynamic 1,000 µs Window:** Extends compensation across 11 discrete strata from $4.5\text{ ms}$ to $5.5\text{ ms}$, synthesizing an autonomous counter-slope against 100 nF capacitor discharge.
- **Uncorrelated White Noise Stream:** Proves that Inverted MAML convergence does not rely on input spatial correlations.
- **Mode B Physical Cross-Check:** Definitive double-blind control on live hardware with physical jumpers removed from `H1$CBB8`.
  - In Mode A, the $3.3\text{ k}\Omega$ resistor shunts the summing junction, lowering impedance by $1/3.3$ (passive gain $0.767$ / $-2.3\text{ dB}$).
  - In Mode B, the jumper is disconnected, leaving the primary $M_{33}$ signal **100% un-damped**.
  - **Empirical Verdict:** Despite being un-damped, Mode B error was **$6.0\times$ higher** ($104.8\text{k}$ vs $17.4\text{k}\text{ LSB}^2$), trapped at $3.20\text{ b}$ mean (zero learning, $1.14\times$ ablation contrast).
  - This definitively proves that Mode A precision is driven exclusively by active analog anti-phase current injection canceling silicon transfer distortion at the virtual-ground summing nodes.

---

## 🛠 Reproduction Workflow

To restore and re-run any archived release on physical hardware:

1. **Verify Target Hardware:**
   Ensure Card 2 is powered on and connected to the Ethernet network (`192.168.1.50:5000`).
   ```bash
   /home/olle/anaconda3/bin/python <RELEASE_DIR>/pc_python/verify_and_guard_version.py
   ```

2. **Reprogram T120 Master SoC (if required):**
   ```bash
   /home/olle/anaconda3/bin/python <RELEASE_DIR>/pc_python/flash_soc.py
   ```

3. **Execute Benchmark:**
   Refer to `README.md` inside each release directory for exact command-line arguments.

---

## 🔒 Policy on Proprietary Files
In accordance with open-science hardware guidelines and licensing restrictions:
- All proprietary Efinix IP blocks (e.g. `ip/`, encrypted IP cores, temporary synthesis artifacts `work_pnr/`, `work_syn/`) are excluded from release archives.
- All user-authored SystemVerilog HDL, pin constraints (`const.sdc`), XML project definitions, pre-compiled bitstreams (`*.bit`), flash hex files (`*.hex`), and C-firmware are fully preserved.


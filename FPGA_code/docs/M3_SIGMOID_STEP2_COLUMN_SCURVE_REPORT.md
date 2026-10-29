# Matrix 3 Sigmoid Analog Activation Characterization Report (Ref 4)

**Steg 2: Column Collective S-Curve Sweep & Optimal Baseline Starting Weights**  
**Execution Environment:** Pure Physical Silicon (Trion T120 Master SoC @ 192.168.1.50:5000)  
**Settled Snapshot Timing:** Locked strictly to nominal $t = 5.0\text{ ms}$ ($5000\ \mu\text{s}$)  
**Total Execution Duration:** 1.5 minutes  

---

## 1. Executive Summary

Steg 2 evaluated the macroscopic S-curve into the analog sigmoid activation (Ref 4) on differential ADC_45 by ramping all 8 rows of each column simultaneously ($W_3[0..7][c] = W$).
By analyzing responses across full scale ($X = \pm 127$) and medium scale ($X = \pm 64$), we located the optimal knee/bend that achieves:
1. **High Dynamic Sensitivity:** $|dY/dW| > 0$ for arbitrary inputs.
2. **Minimal Stochastic Jitter:** Smooth, non-jerky analog transfer.
3. **Optimal Anchor:** Initial baseline weights $\mathbf{W}_{3,\text{baseline}}$ for compensation matrices and future L2 regularization.

---

## 2. Calibrated Baseline Weight Vector Table

| Column | Optimal Knee $W_{\text{base}}$ | Polarity | Sensitivity ($X=\pm 64$) | Dynamic Swing | Regularization Anchor |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **C0** | **-16 LSB** | **NEG** | 47.35 LSB/W | 2861 LSB | Pull toward -16 |
| **C1** | **-16 LSB** | **NEG** | 43.45 LSB/W | 2859 LSB | Pull toward -16 |
| **C2** | **+16 LSB** | **POS** | 51.31 LSB/W | 2856 LSB | Pull toward +16 |
| **C3** | **+16 LSB** | **POS** | 48.99 LSB/W | 2861 LSB | Pull toward +16 |
| **C4** | **-16 LSB** | **NEG** | 56.47 LSB/W | 2847 LSB | Pull toward -16 |
| **C5** | **+16 LSB** | **POS** | 57.75 LSB/W | 2833 LSB | Pull toward +16 |

### Final Baseline Vector:
```python
W3_BASELINE = [C0: -16, C1: -16, C2: +16, C3: +16, C4: -16, C5: +16]
```

---

## 3. Visualizations

- Column S-Curves: `FPGA_code/docs/figures/fig_m3_sigmoid_step2_column_scurves.png`

# Mode A Hardware Verification: 1k / 15k Ohm Summing Attenuator Report
**Patent Pending SE 2630397-4 | Physical Silicon Telemetry**  
**Target:** Efinix Trion T120 Master SoC + T20 Coprocessor (`192.168.1.50:5000`)  
**Date:** October 26, 2026

---

## 1. Hårdvaruuppgradering: 1k / 3.9k &rarr; 1k / 15k Ohm
Efter omlödning av summeringspunkten på kretskortet sänktes återkopplingsauktoriteten från **$20.4\%$** ($1\text{ k}\Omega / 3.9\text{ k}\Omega$) till **$6.25\%$** ($1\text{ k}\Omega / 15\text{ k}\Omega$). Detta ger kretsen en cirka **$3.3\times$ finare analog Vernier-upplösning**.

### Kontroll av alla 6 kolumner (Lödningsverifiering):
- **ADC 4.5 ms:** `[574.7, 477.5, 324.0, 166.8, 1159.5, 642.2] LSB` (Friska, stabila nivåer på samtliga kanaler)
- **ADC 4.9 ms:** `[-1176.2, -969.3, -1287.8, -447.0, 563.7, 168.3] LSB`
- **Kanal-fel (ERR49):** `[-107.2, -113.3, 30.2, -22.0, 11.7, -97.7] LSB`
- **Slutsats:** Inga öppna kretsar eller kortslutningar föreligger; alla 6 kolumner har solid kontakt.

---

## 2. Jämförelse mellan de fyra testerna med 1k/15k-motståndet

![1k/15k Hårdvaruverifiering](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_1k15k_hardware_verification.png)

| Egenskap | Test 1: $K=8, \text{LR}=0.08x$ | Test 2: $K=8, \text{LR}=0.32x$ | Test 3: $K=16, \text{LR}=0.08x$ | **Test 4: $K=4, \text{LR}=1.00x$ (Dynamisk Backprop)** |
| :--- | :---: | :---: | :---: | :---: |
| **Antal Epoker** | 20 Epoker (37.8 s) | 40 Epoker (87.5 s) | 40 Epoker (99.3 s) | **40 Epoker (75.5 s, 1.9 s/ep)** |
| **Prover per steg ($10 \times K$)** | 80 prover/steg | 80 prover/steg | 160 prover/steg | **40 prover/steg (Snabb respons)** |
| **Initial Val Loss / RMSE** | $20\,035.0\text{ LSB}^2$ ($81.7\text{ LSB}$) | $7\,515.6\text{ LSB}^2$ ($50.1\text{ LSB}$) | $17\,703.5\text{ LSB}^2$ ($76.8\text{ LSB}$) | $29\,031.8\text{ LSB}^2$ ($98.4\text{ LSB}$) |
| **Bästa Uppmätta ENOB** | $5.61\text{ bitar}$ | $5.89\text{ bitar}$ | $6.10\text{ bitar}$ | **$6.28\text{ bitar}$! (Nytt all-time kiselrekord!)** 🏆 |
| **Lägsta Val-RMSE** | $42.00\text{ LSB}$ | $34.49\text{ LSB}$ | $29.95\text{ LSB}$ | **$26.35\text{ LSB}$! (Epok 27)** |
| **Stabilitet / Dynamik** | Mycket jämn nedgång | Högt brus, fladdrig | Lugn och kontrollerad | **Aggressiv adaptiv inlärning** |
| **Viktförflyttning $W_8$ (M8)** | Statisk: alla 24 | Liten rörelse: $24 \dots 25$ | Liten rörelse: $24 \dots 25$ | **Mycket aktiv: $[23, 23, 25, 24, 27, 26]$** |
| **Viktförflyttning $W_3$ (M3)** | Statisk: nästan alla 64 | Liten rörelse: $60 \dots 63$ | Liten rörelse: $62 \dots 64$ | **Mycket aktiv: $60 \dots 65$ + off-diagonaler** |
| **Topologisk Stabilitet** | $r_{M3} = 1.0000$ | $r_{M3} = 0.9994$ | $r_{M3} = 0.9998$ | **$r_{M3} = 0.9998$** |

---

## 3. Fysikalisk Analys & Förklaring till varför matriserna stod stilla tidigare

### 1. Varför stod matriserna stilla i GUI vid låg Learning Rate?
- **6-bitars DAC-upplösning:** Hårdvarans DAC:ar arbetar med diskreta heltalssteg ($0 \dots 63$).
- **Gradientskalan:** Vid $\text{LR} = 0.08x$ var den ackumulerade viktförändringen per epok $\Delta W \approx 0.05 \dots 0.15\text{ DAC-steg}$. Efter heltalsavrundning (eller trunkering) förblev de flesta DAC-värdena identiska med startläget (pedestalen 24 för M8, 64 för M3) under loppet av 20-40 epoker.
- Det gav illusionen i GUI-animeringen att "ingenting hände och bara brus syntes", trots att analog signalbehandling pågick.

### 2. Vad hände när vi höjde till $\text{LR} = 1.0x$ och sänkte till $K = 4$?
1. **Gradientauktoriteten slog igenom:** Med $\text{LR} = 1.0x$ blev gradientstegen tillräckligt kraftiga för att faktiskt korsa diskretiseringströskeln ($\Delta W \ge 1\text{ LSB}$) i varje uppdatering.
2. **Kompensation i båda lagren:**
   - I **Matrix 8** vandrade vikterna dynamiskt mellan 20 och 27 över kolumnerna för att kompensera för kanalernas fysiska asymmetrier.
   - I **Matrix 3** justerades inte bara diagonalen ($62 \dots 65$) utan även off-diagonala korskopplingar ($0 \to 1$) utvecklades för att dämpa överhörning mellan intilliggande kolumner.
3. **Ingen instabilitet tack vare 1k/15k:**
   - På den gamla 1k/3.9k-hårdvaran hade en inlärningshastighet på $1.0x$ omedelbart drivit op-amparna till klippning och skenande svängning.
   - Med det nya 1k/15k-motståndet är återkopplingsslingan så pass dämpad ($6.25\%$) att systemet förblir **helt linjärt och stabilt**, vilket tillät systemet att nå **$6.28\text{ bitar}$ ENOB ($26.35\text{ LSB}$ RMSE)**!

---

## 4. Hur du spelar upp den dynamiska körningen i GUI:t
Öppna den senaste körningen (Test 4) direkt i GUI:t:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/maml_post_analysis_gui.py FPGA_code/logs/mode_a_longterm_sweep/test_1k15k_k4_lr100p_40ep.json
```

1. Klicka på **▶ Play Animation** eller dra i reglaget längst ner.
2. Studera **3D Weight Surfaces**: Nu ser du hur både Matrix 8 och Matrix 3 rör sig aktivt från epok till epok!
3. Vid **Epok 27** ser du den optimala dalen där residualfelet pressas ner till rekordlåga **$26.35\text{ LSB}$**!

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

## 2. Jämförelsetabell över hårdvarutesterna på 1k/15k

| Egenskap | Test 1: $K=8, \text{LR}=0.08x$ | Test 3: $K=16, \text{LR}=0.08x$ | Test 4: $K=4, \text{LR}=1.00x$ | **Test 5: $K=8, \text{LR}=1.50x$ (200 Ep)** 🏆 |
| :--- | :---: | :---: | :---: | :---: |
| **Antal Epoker** | 20 Epoker (37.8 s) | 40 Epoker (99.3 s) | 40 Epoker (75.5 s) | **200 Epoker (373.0 s, 1.9 s/ep)** |
| **Prover per steg ($10 \times K$)** | 80 prover | 160 prover | 40 prover | **80 prover / steg (16 000 prover totalt)** |
| **Initial Val Loss / RMSE** | $20\,035\text{ LSB}^2$ ($81.7\text{ LSB}$) | $17\,703\text{ LSB}^2$ ($76.8\text{ LSB}$) | $29\,031\text{ LSB}^2$ ($98.4\text{ LSB}$) | **$11\,670\text{ LSB}^2$ ($62.4\text{ LSB}$)** |
| **Bästa Uppmätta ENOB** | $5.61\text{ bitar}$ | $6.10\text{ bitar}$ | $6.28\text{ bitar}$ | **$6.71\text{ bitar}$! (All-Time Kiselrekord!)** 👑 |
| **Lägsta Val-RMSE** | $42.00\text{ LSB}$ | $29.95\text{ LSB}$ | $26.35\text{ LSB}$ | **$19.63\text{ LSB}$! (Epok 174)** |
| **Långsiktig Trend** | -57.0% (20 ep) | Stabil runt 5.7 b | Snabb dal vid Ep 27 | **-23.9% nettoloss Q1 &rarr; Q4 ($\beta_1 = -22.7$)** |
| **Viktförflyttning $W_8$ (M8)** | Statisk: alla 24 | Liten rörelse ($24 \dots 25$) | Aktiv ($20 \dots 27$) | **Organisk evolution: $[26, 28, 23, 24, 0, 37]$** |
| **Viktförflyttning $W_3$ (M3)** | Statisk: nästan alla 64 | Liten rörelse ($62 \dots 64$) | Aktiv ($60 \dots 65$) | **Organisk evolution: $[50, 67, 45, 65, 31, 72]$** |
| **Topologisk Korrelation** | $r_{M3} = 1.0000$ | $r_{M3} = 0.9998$ | $r_{M3} = 0.9998$ | **$r_{M3} = 0.8748$ (Bevarad geometri)** |

---

## 3. Fysikalisk Analys: Varför 200 Epoker vid $\text{LR}=1.5x$ gav 6.71 bitar

### 1. Landskapet växer organiskt utan att mättas
Vid $\text{LR} = 5.0x$ drevs vikterna så hårt att de slog i taket för linjär mättning ($W_3 = 80$) redan vid epok 50.
Vid **$\text{LR} = 1.50x$** fann systemet en perfekt balans:
- Vikterna rörde sig kontinuerligt i varje epok för att kompensera för kanalernas analoga olinjäriteter.
- Ingen kanal slog i taket ($W_3$ rörde sig mellan 31 och 72, väl inom det linjära området).
- Korrelationen $r_{M3}$ bevarades på höga **$0.875$**, vilket innebär att matrisens inbördes geometriska struktur förblev intakt.

### 2. Under 20 LSB i residualfel
Vid **Epok 174** nådde systemet ett historiskt minimum:
- **Residualfel (RMSE):** **$19.63\text{ LSB}$**
- **ENOB:** **$6.71\text{ bitar}$**
- Målsignal $Z_{target}$: `[-958.0, -944.0, -1256.0, -496.0, 666.0, 104.0] LSB`
- Uppmätt ADC49: `[-971.0, -970.0, -1252.0, -466.5, 690.0, 106.0] LSB`
- Residualfel per kanal: `[-13.0, -26.0, +4.0, +29.5, +24.0, +2.0] LSB`!

---

## 4. Spela upp 200-epokerskörningen i GUI:t
Öppna den nya 200-epokerskörningen i analys-GUI:t:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/maml_post_analysis_gui.py FPGA_code/logs/mode_a_longterm_sweep/test_1k15k_k8_lr150p_200ep.json
```

1. Klicka på **▶ Play Animation** och luta dig tillbaka!
2. Studera **3D Weight Surfaces**: Se hur 3D-ytan för Matrix 8 och Matrix 3 gradvis växer fram, jämnar ut ojämnheterna och deformeras mjukt över alla 200 epoker.
3. Vid **Epok 174** ser du hur residualfelet dyker ner under 20 LSB och når det nya rekordet **6.71 bitar**!

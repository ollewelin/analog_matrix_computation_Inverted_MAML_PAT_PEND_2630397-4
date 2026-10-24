# Mode A ($t = 5.0\text{ ms}$) Inre Loop-Verifiering — Rapport 2 (Ny Flash- & Repeterbarhetsverifiering)

**Datum:** 2026-10-24  
**Hårdvara:** Inverted MAML Analog Matrix (`192.168.1.50:5000`, Efinix Trion `T120F324` Master + `T20F256` Gate/Hadamard Controller)  
**Byglingsläge:** Mode A (`jumper_mode = 3` — Aktiv kompensationsslinga via Matris 3, Sigmoid 4, Matris 8, Sigmoid 10 och passivt $1\text{ k}\Omega / 3.9\text{ k}\Omega$ summeringsnät)  
**Arbetspunkt:** $t = 5.0\text{ ms}$ (`hadamard_delay_us = 5000`, $100\text{ Hz}$ / $10.0\text{ ms}$ synkron kondensatoruppdatering)  
**Kolumnomfattning:** Samtliga 6 kolumner ($j \in \{0, 1, 2, 3, 4, 5\}$) aktiva samtidigt (noll kolumnmaskering)

---

## 1. Syfte och Jämförelse Mellan Körning 1 och Körning 2

Efter att [`maml_platform.c`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/sw/t120_master/src/maml_platform.c) verifierats, kompilerats om från källkod och nyprogrammerats till `T120F324` via JTAG ([`flash_soc.py`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/scripts/flash_soc.py)) genomfördes ett nytt, oberoende verifieringsvarv (**Körning 2**) med nya slumpade vitbrus-insignaler $\mathbf{x}_{\text{ref}}$ över samtliga 6 kolumner vid $t = 5.0\text{ ms}$.

| Metrik (Alla 6 kolumner, $t = 5.0\text{ ms}$) | Körning 1 (Rapport 1) | Körning 2 — Omgång A | Körning 2 — Omgång B | Körning 2 — Omgång C (Huvudgraf) |
|:---|:---:|:---:|:---:|:---:|
| **Steg 0 Centrerad Förlust $L_0$** | $8\,870.9\text{ LSB}^2$ | $20\,094.2\text{ LSB}^2$ | $9\,449.9\text{ LSB}^2$ | **$6\,133.1\text{ LSB}^2$** |
| **Bästa Konvergerade Förlust $L_{\min}$** | $324.5\text{ LSB}^2$ | $3\,257.7\text{ LSB}^2$ | $1\,592.1\text{ LSB}^2$ | **$657.7\text{ LSB}^2$** |
| **Relativ Förlustreduktion** | **$-96.3\%$** | **$-83.8\%$** | **$-83.2\%$** | **$-89.3\%$** |
| **Steg 0 6-Kolumners RMSE** | $54.38\text{ LSB}$ | $81.84\text{ LSB}$ | $56.12\text{ LSB}$ | **$45.21\text{ LSB}$** |
| **Bästa 6-Kolumners RMSE** | $10.40\text{ LSB}$ (Steg 18) | $32.95\text{ LSB}$ (Steg 13) | $23.04\text{ LSB}$ (Steg 16) | **$14.81\text{ LSB}$ (Steg 8)** |
| **Slutlig 6-Kolumners RMSE (Steg 20)** | $16.04\text{ LSB}$ | $44.56\text{ LSB}$ | $28.24\text{ LSB}$ | **$21.67\text{ LSB}$** |
| **Steg 0 Effektiv Bithöjd (ENOB)** | $5.24\text{ bitar}$ | $4.65\text{ bitar}$ | $5.19\text{ bitar}$ | **$5.50\text{ bitar}$** |
| **Topp-ENOB under Inre Loop** | **$7.62\text{ bitar}$** (`+2.38`) | **$5.96\text{ bitar}$** (`+1.31`) | **$6.47\text{ bitar}$** (`+1.28`) | **$7.11\text{ bitar}$** (`+1.61`) |

![Mode A Inre Loop Konvergens vid t = 5.0 ms (Körning 2)](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_5ms_inner_loop_convergence_run2.png)

---

## 2. Verifiering av Bidirektionell Viktadaption över Alla 6 Kolumner

En avgörande egenskap i **Körning 2 (Omgång C)** är att det slumpade insignalmönstret gav **både negativa och positiva initiala kolumnfel** vid Steg 0:
- **Negativa initiala utgångsfel** på Kolumn 0 ($Er_0^{(49)} = -45.0\text{ LSB}$) och Kolumn 2 ($Er_2^{(49)} = -87.8\text{ LSB}$).
- **Positiva initiala utgångsfel** på Kolumn 1 ($Er_1^{(49)} = +18.5\text{ LSB}$), Kolumn 3 ($Er_3^{(49)} = +13.5\text{ LSB}$), Kolumn 4 ($Er_4^{(49)} = +42.5\text{ LSB}$) och Kolumn 5 ($Er_5^{(49)} = +14.2\text{ LSB}$).

Som framgår av den högra panelen i figur 2 nedan styr den icke-backprop-baserade Hadamard-gradienten (Ekvation 1–7) automatiskt kompensationsvikterna i **båda riktningarna** från startpiedestalen $+24$:
- **Uppåt** på Kolumn 0 ($24 \to 31$) och Kolumn 2 ($24 \to 28$) för att lyfta `ADC_49` mot målvärdet.
- **Nedåt** på Kolumn 4 ($24 \to 14$), Kolumn 1 ($24 \to 21$) och Kolumn 5 ($24 \to 21$) för att sänka `ADC_49` mot målvärdet.
- **Stilla kring jämvikt** på Kolumn 3 ($24 \to 22 \to 24$) där startfelet redan var litet ($+13.5\text{ LSB} \to -4.5\text{ LSB}$).

![Alla 6 Kolumners Feltrajektorior och Vernier-Viktadaption (Körning 2)](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_5ms_6col_error_trajectories_run2.png)

### Steg-för-Steg-Tabell (Körning 2 — Omgång C, Samtliga 6 Kolumner vid $t = 5.0\text{ ms}$)

| Steg | $Er_0^{(49)}$ (Col 0) | $Er_1^{(49)}$ (Col 1) | $Er_2^{(49)}$ (Col 2) | $Er_3^{(49)}$ (Col 3) | $Er_4^{(49)}$ (Col 4) | $Er_5^{(49)}$ (Col 5) | 6-Kol RMSE | Förlust $L$ ($\text{LSB}^2$) | ENOB (bitar) | $W_8$ Diag `[c,c]` |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 (Start)** | $-45.0$ | $+18.5$ | $-87.8$ | $+13.5$ | $+42.5$ | $+14.2$ | **$45.21\text{ LSB}$** | $6\,133.1$ | **$5.50$** | `[24, 24, 24, 24, 24, 24]` |
| **1** | $-23.2$ | $+17.0$ | $-66.2$ | $-28.8$ | $+55.2$ | $+18.8$ | **$39.66\text{ LSB}$** | $4\,719.8$ | **$5.69$** | `[24, 24, 25, 23, 22, 23]` |
| **2** | $-41.2$ | $+23.5$ | $-61.0$ | $-1.5$ | $+45.5$ | $+13.2$ | **$37.01\text{ LSB}$** | $4\,108.7$ | **$5.79$** | `[24, 24, 25, 23, 19, 22]` |
| **4** | $-39.5$ | $+31.8$ | $-48.2$ | $+8.8$ | $+34.2$ | $+26.8$ | **$33.81\text{ LSB}$** | $3\,430.0$ | **$5.92$** | `[25, 24, 26, 24, 17, 22]` |
| **6** | $+1.0$ | $+3.5$ | $-39.8$ | $-7.5$ | $+42.8$ | $-3.2$ | **$24.14\text{ LSB}$** | $1\,747.8$ | **$6.41$** | `[26, 24, 26, 24, 16, 21]` |
| **8 (Bäst)** | **$-14.0$** | **$-9.8$** | **$-27.2$** | **$-4.5$** | **$+14.0$** | **$+8.2$** | **$14.81\text{ LSB}$** | **$657.7$** | **$7.11$** | `[29, 22, 27, 22, 16, 21]` |
| **10** | $-17.0$ | $-5.0$ | $-35.5$ | $+9.8$ | $+19.5$ | $+14.0$ | **$19.35\text{ LSB}$** | $1\,123.3$ | **$6.73$** | `[28, 23, 27, 23, 16, 22]` |
| **11** | $-21.2$ | $+8.5$ | $-43.2$ | $-3.5$ | $+14.5$ | $+9.8$ | **$21.24\text{ LSB}$** | $1\,353.2$ | **$6.59$** | `[29, 23, 27, 22, 15, 22]` |
| **18** | $-48.8$ | $-4.0$ | $-21.0$ | $+1.5$ | $+26.2$ | $+4.5$ | **$24.32\text{ LSB}$** | $1\,773.7$ | **$6.40$** | `[29, 22, 28, 24, 14, 21]` |
| **19** | $-14.2$ | $-15.0$ | $-31.8$ | $-0.2$ | $+34.2$ | $+11.5$ | **$21.37\text{ LSB}$** | $1\,369.9$ | **$6.58$** | `[29, 22, 28, 24, 15, 21]` |
| **20 (Slut)** | $+11.8$ | $-12.2$ | $-41.8$ | $+5.2$ | $+24.8$ | $+11.8$ | **$21.67\text{ LSB}$** | $1\,408.3$ | **$6.56$** | `[30, 21, 28, 24, 14, 21]` |

---

## 3. Verifiering av $1\text{ k}\Omega / 3.9\text{ k}\Omega$-Summeringsdämparen och $6 \times 6$ Mode A-Karta

![1 kOhm / 3.9 kOhm Summeringsdämpare och 6x6 Mode A Sving (Körning 2)](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_1k_3k9_attenuator_verification_run2.png)

- **Primärväg ($M_{33}$ via $1.0\text{ k}\Omega$):** Teoretisk dämpningsfaktor $\frac{3.9}{4.9} = 0.7959$, empiriskt uppmätt kolumnmedelvärde $0.6772\text{--}0.7795\times$ över Kolumn 0..5.
- **Vernier-kompensationsväg ($M_8 \to \text{Sigmoid 10}$ via $3.9\text{ k}\Omega$):** Teoretisk dämpningsfaktor $\frac{1.0}{4.9} = 0.2041$, vilket ger finupplöst kompensationsauktoritet utan att bottna `ADC_49`.

---

## 4. Verifierad Källkodsstatus i `maml_platform.c`

Källkoden i [`FPGA_code/sw/t120_master/src/maml_platform.c`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/sw/t120_master/src/maml_platform.c) är nu 100 % synkroniserad med det flashade kortet och innehåller:
1. **`HADAMARD_2X7_POS[7]`** (rad 475–483) och **`maml_fwht16_demodulate()`** (rad 601–657) med interfolierade $2 \times 7 = 14$ pulser om $2.00\,\mu\text{s}$ och exakt Sylvester-$H_8$ Simplex-ortogonalisering (`>> 1`).
2. **`aio_trigger_settled_adc_read()`** (rad 568–587) med $16\times$ hårdvarumedelvärdesbildning.
3. **`maml_measure_and_extract_gradients()`** (rad 674–841) med Sub-Window A ($M_8$ först, `0x3F00u`) $\to$ $20\,\mu\text{s}$ 3-State Hi-Z $\to$ Sub-Window B ($M_3$ sedan, `0x003Fu`), bärvågssökning `best_k` på `ADC_45` (Ekvation 5 & 6) och direkt Hadamard-felprodukt utan digital multiplicering med $x_i$ (Ekvation 2 & 7).
4. **`maml_center_compensation_weights()`** (rad 897–946) med linjär $+1.65\text{ V}$-piedestal (`M3` diagonal $+64$, rad 6 $+48$, `M8` rader 0..5 $+24$) och $100\text{ Hz}$ synkron nollpunktskalibrering.

---

## 5. Filer och Loggar för Rapport 2

- **PDF-rapport 2:** [`FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.pdf`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.pdf)
- **Markdown-rapport 2:** [`FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.md`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.md)
- **Rådata (JSON, Körning 2):** [`FPGA_code/logs/mode_a_5ms_inner_loop/mode_a_5ms_inner_loop_run2_summary.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_5ms_inner_loop/mode_a_5ms_inner_loop_run2_summary.json)


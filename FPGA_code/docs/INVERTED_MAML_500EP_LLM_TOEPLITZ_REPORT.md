# Inverted MAML: 500-Epoker Mode A Träningsrapport under LLM Toeplitz Färgfilter

> [!NOTE]
> **Patentreferens**: SE 2630397-4 (Open Science Hardware)  
> **Hårdvara**: Efinix Trion T120 Master SoC + T20 Controller + Dual-2T1C Analog Multiplier Silicon (M33, M3, M8)  
> **Firmware-version**: `v2.2-MAML` (HW Logic: `0x20261030`)  
> **Loggdata**: [`mode_a_500ep_llm_toeplitz_rho85_reg512.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/llm_noise_campaign/mode_a_500ep_llm_toeplitz_rho85_reg512.json)

---

## 1. Sammanfattning av Körningen

Denna körning utvärderar Inverted MAML **Mode A (Inre slingans analogträning)** under realistiska, rumsligt korrelerade aktiveringar som efterliknar dolda tillstånd i stora språkmodeller (LLM Transformers).

Tidigare körningar drabbades av våldsamma spikar ("hysteriska ryck") när korrelerade indata råkade driva de analoga transimpedansförstärkarna (ColTIA) in i mättnad. I denna körning aktiverades det nyutvecklade **ColTIA Saturation Guard** tillsammans med **Zero-Mean Centering (LayerNorm)**. Systemet körde 500 epoker med **0 bottnade/klippta epoker**, fullständig stabilitet och uppnådde en topp-upplösning på **7.13 bitar ENOB**!

```
========================================================================================
FAS                     EPOKER    M3 & M8 VIKTER            TRÄNING     MEDEL-LOSS     ENOB
========================================================================================
Fas 1: BASELINE_ZERO    0 .. 99   Nollställda (0 LSB)       AV          8 805 LSB²     5.28 b
Fas 2: BASELINE_KNEE    100..199  Fast Knä (±16 LSB)        AV         21 853 LSB²     4.60 b
Fas 3: TRAIN_REG_ON     200..500  Tränade (λ = 512)         PÅ (Mode A) 4 910 LSB²     5.79 b (Topp 7.13 b)
========================================================================================
```

![3D Silicon Studio Snapshot](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_gui_animation_snapshot_ep353.jpg)
*Figur 1: Skärmdump från Injected FORWARD Propagation Silicon Studio vid Epok 353 (Aktiv Träningsfas). Matrix 8 visar en levande, mångdimensionell kompensationsyta som balanserar analoga olinjäriteter med lågt fel (RMSE: 27.32 LSB, Loss: 2239.4 LSB²) och 6.23 bitars ENOB.*

---

## 2. Vilket Färgfilter Körde Vi? (LLM Toeplitz AR(1))

I verkliga neurala nätverk (som Transformers) är ingångsvektorer $x$ inte oberoende vitt brus, utan har kraftig rumslig korrelation mellan närliggande dimensioner/tokens och kanaler:

$$\text{Mode 3: } \text{COLOR\_LLM\_TOEPLITZ} \quad (\rho = 0.85)$$

Filtret implementerar en **Kac-Murdock-Szegö Toeplitz AR(1)-kovariansstruktur**:
$$\text{Cov}(x_i, x_j) = \rho^{|i - j|} \quad \text{där } \rho = 0.85$$

![LLM Filter Kovarians och Indata](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_llm_filter_covariance.png)
*Figur 2: Vänster: Kovariansmatrisen $\rho^{|i-j|}$ för 6 kanaler vid $\rho = 0.85$. Höger: Exempel på genererade vektorer $x_{\text{ref}}$ efter Zero-Mean Centering.*

### Hårdvaruimplementation på T120 RISC-V SoC:
I `maml_platform.c` genereras vektorn i realtid på T120-processorn:
```c
/* Kac-Murdock-Szegö AR(1) spatial covariance: rho^|i-j| */
val[0] = raw[0];
for (int i = 1; i < 6; i++) {
    int32_t acc = (int32_t)rho * val[i - 1] + (int32_t)(256 - rho) * raw[i];
    val[i] = acc >> 8;
}

/* Zero-Mean Centering (Hardware LayerNorm) */
int32_t mean_sum = 0;
for (int i = 0; i < 6; i++) mean_sum += val[i];
int32_t mean_val = mean_sum / 6;
for (int i = 0; i < 6; i++) val[i] -= mean_val;
```

---

## 3. Varför Spikade Det Förut och Hur Löstes Det?

### Det Fysiska Problemet: "Bottning" i ColTIA
1. **Payload-matrisen $M_{33}$ har en positiv kolumnsockel** ($+114$ till $+128\text{ LSB}$).
2. Vid $\rho = 0.85$ var alla 6 insignaler ofta negativa samtidigt (t.ex. `[-23, -18, -23, -22, -20, -14]`).
3. Negativ insignal gånger positiv förstärkning genererade en enorm samlad DC-ström mot jord, vilket tryckte ColTIA-transimpedansförstärkarna mot enkelmatningens jord ($0\text{ V}$ / negativ mättnad).
4. **Hadamard-demodulationen slog i taket**: Vår uppmätta Hadamard-perturbation är **$243\text{ LSB}$** peak-to-peak. När signalen bottnade klipptes halvvågen av.
5. Snabb Walsh-Hadamard Transformation (FWHT) förlorade sin ortogonalitet och tolkade klippningen som gigantiska, påhittade gradienter ("fantomgradienter") på alla rader samtidigt. Vikterna tog ett våldsamt skutt ut i periferin!

### De Två Motåtgärderna i Hårdvaran:
1. **LayerNorm / Zero-Mean Centering**: $\sum_{i=0}^5 x_i \equiv 0$. Detta eliminerar DC common-mode strömmen genom $M_{33}$ och centrerar signalen kring operationsförstärkarnas $1.65\text{ V}$ virtuella nolla.
2. **ColTIA Saturation Guard (Anti-Clip Distortion Guard)**:
   - Headroom-marginal: $250\text{ LSB}$ (motsvarande Hadamard-svängen).
   - Tröskel: $\text{COLTIA\_CLIP\_THRESHOLD\_LSB} = 2047 - 250 = \mathbf{1797\text{ LSB}}$.
   - Om $|ADC_{45}| \ge 1797$ eller $|ADC_{49}| \ge 1797$: **Inga vikter uppdateras** ($\Delta W \equiv 0$). Korrupta gradienter kasseras omedelbart och telemetrilarm flaggas.

---

## 4. Analys av 3-Fas Dynamiken

![500-Epoch Mode A Training Graph](/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_llm_rho85_reg512.png)
*Figur 3: 500-epokers förlopp på fysisk kisel under LLM Toeplitz-brus ($\rho=0.85, \lambda=512$). Notera de skarpa fasövergångarna vid Epok 100 och 200.*

### Fas 1: Rå Onkompenserad Respons (Epok 0 .. 99)
- **Inställning**: $M_3 = 0, M_8 = 0$, Träning = AV.
- **Prestanda**: Medel-loss $8\,805\text{ LSB}^2$, ENOB $5.28\text{ bitar}$.
- **Observation**: Detta representerar hårdvarans råa termiska och kanalmässiga offset utan kompensationsnätverk.

### Fas 2: Fast Knä-Baseline (Epok 100 .. 199)
- **Inställning**: $M_3 = 0$, $M_8 = [-16, -16, 16, 16, -16, 16]\text{ LSB}$, Träning = AV.
- **Prestanda**: Medel-loss $21\,853\text{ LSB}^2$, ENOB $4.60\text{ bitar}$.
- **Observation**: Knä-läget förspänner cellerna in i deras linjära triodzon. Eftersom ingen träning är aktiv och vikterna är fixerade för att mäta differentiell bias är felet förhöjt (vilket tydligt syns i animations-GUI:t som ett trappsteg).

### Fas 3: Aktiv Mode A Analogträning (Epok 200 .. 500)
- **Inställning**: Inre slingans gradientsteppning aktiv ($LR = 0.25\times$), $L_2$-regularisering $\lambda = 512$ mot baseline.
- **Prestanda**:
  - Medel-loss faller kraftigt från $21\,853\text{ LSB}^2$ ner till **$4\,910\text{ LSB}^2$** (mer än **$77\%$ felreduktion**!).
  - Bästa uppmätta sample vid Epok 424: **$\text{Loss} = 637.9\text{ LSB}^2$**, **$\text{ENOB} = 7.13\text{ bitar}$**!
  - $M_8$ rör sig minimalt och kontrollerat runt knäet (`[-9, -16, 13, 16, -11, 12]`), helt utan rail-mättnad eller drift.

---

## 5. Slutsatser och Nästa Steg

1. **Fullständig stabilitet uppnådd**: ColTIA Saturation Guard och Zero-Mean Centering eliminerade de ryckiga spikarna helt. Nätverket kan nu tränas kontinuerligt även under kraftigt korrelerade indatavektorer ($\rho=0.85$).
2. **3-fasprotokollet stämmer perfekt med Animations-GUI**:
   - Skärmdumpen från Silicon Studio (Figur 1) visar exakt överensstämmelse: Fas 1 (platt nolla) $\rightarrow$ Fas 2 (knä-trappsteg) $\rightarrow$ Fas 3 (monoton och kontrollerad felminimering).
3. **Rekommenderat nästa steg**:
   - Testa glesa aktiveringar (`COLOR_LLM_SPARSE_GELU`, Mode 4) där inaktiva kanaler nollas och aktiva kanaler förstärks, för att efterlikna Transformer MLP-lager.

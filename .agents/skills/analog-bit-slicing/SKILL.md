---
name: analog-bit-slicing
description: Theory, honesty rules and dual-card protocol for true bit slicing on Inverted MAML silicon (Card 1 = MSB slice, Card 2 = LSB slice). Use whenever planning, implementing, running or reporting multi-card / multi-slice precision experiments, shift-and-add recombination, or claims of combined ENOB above the single-card ENOB.
---

# Analog Bit Slicing on Inverted MAML Silicon

## 1. Goal & Non-Negotiable Rules (Olle, 2026-11-11)

Goal: combine two physical cards (each with a stable >= 4.0 b ENOB under thermal stress while Mode A training is ON) into one higher-precision matrix-vector product, target 8 b.

**FORBIDDEN (counts as cheating, never implement):**
- Any adaptive / fitted digital pre- or post-correction: per-column alpha/beta gain & offset, regression fits, moving-target "patches", lookup tables learned from data, digital calibration layers running in full inference bandwidth.
- Any correction that uses the measured output to modify the reported output.
- Offset and gain must be held **only** by the on-board Mode A training (M3 -> Sig4 -> M8 compensation) against each card's own firmware `z_target`.

**ALLOWED (this IS the definition of bit slicing, fixed and data-independent):**
- Fixed integer split of operands into slices (shift / mask) before loading.
- Fixed power-of-two shift-and-add of slice outputs: `Y = 2^s * Y_MSB + Y_LSB`.
- Rounding a slice output to its integer grid using the **fixed, firmware-defined** scale (`acc/32` -> ADC LSB) and the per-card DC zero-cal measured at t=0 (same `g_adc49_zero_cal` already used by the firmware target). No per-column fitted constants.

Every report must state explicitly which of the allowed operations were used.

## 2. The Mathematics of Bit Slicing

Weight slicing (unsigned example, 8-bit weight, 4-bit slices):
```
W = 16 * W_H + W_L        W_H, W_L in [0, 15]
Y = X . W = 16 * (X . W_H) + (X . W_L) = 16 * Y_H + Y_L
```
Input slicing is analogous (`X = 16 X_H + X_L`); both can be combined (4 partial products).
Signed operands: use offset-binary or sign-magnitude per slice; the shift-add is unchanged.

## 3. CRITICAL: Why Two 4-bit-ENOB Cards Do NOT Give 8 bits by Shift-and-Add Alone

Let each card produce its analog partial product with error `e_k`:
```
Y_hat = 16 * (Y_H + e_H) + (Y_L + e_L)
error = 16 * e_H + e_L
full scale FS_total ~ 16 * FS_H
relative error ~ e_H / FS_H   ->   ENOB_total ~ ENOB_MSB-card  (~4 b, NOT 8 b)
```
The MSB card's analog error is multiplied by the same factor 16 as its signal. Shift-and-add of two analog results only re-scales; it cannot create precision. **Any claim of combined ENOB > single-card ENOB from plain shift-add of analog outputs is mathematically wrong.**

## 4. What Actually Makes Bit Slicing Work: Integer Restoration Per Slice

Bit slicing gains precision only when each slice output can be **restored to its exact integer value** before shift-add:
```
Y_k_int = round( (ADC_k - zero_cal_k) / step_k )       step_k = fixed ADC-LSB per unit partial sum
Y = sum_k 2^(s_k) * Y_k_int                             exact if |analog error_k| < step_k / 2
```
If every slice rounds correctly, the combined result is **exact** (error 0) and the 8 b precision is real. This is how ReRAM/PCM bit-sliced crossbars work (1-2 bit cells, bit-serial inputs, partial sums small enough for the ADC to resolve exactly).

Condition for reliable rounding (Gaussian error, sigma = slice RMSE in ADC LSB):
- step >= 6 sigma -> misround probability ~ 0.27 %
- step >= 8 sigma -> ~ 0.006 %

Measured today: RMSE ~ 35-45 LSB (4.0-5.8 b). -> step must be ~ 250-350 ADC LSB -> only **~12-16 distinct partial-sum levels** fit inside +/-2048 LSB. That is exactly what "4 b exact per slice" means.

### Design consequence
Each slice's set of possible partial sums `P = sum_i x_i * w_i` (6 rows) must have <= ~16 levels:
| Input slice | Weight slice | Partial-sum range (6 rows) | Levels | Fits? |
| :--- | :--- | :--- | :---: | :---: |
| 1 bit {0,1} | 1 bit {0,1} | 0..6 | 7 | yes, large margin |
| 1 bit {0,1} | 2 bit {0..3} | 0..18 | 19 | marginal |
| 2 bit | 2 bit | 0..54 | 55 | no |
| 4 bit | 4 bit | 0..1350 | 1351 | no (needs ~10.4 b exact) |

Therefore 8-bit x 8-bit operands require **bit-serial input streaming** (several analog evaluations per MAC) and narrow weight slices, then exact integer shift-add. Throughput drops by the number of slice-cycles; precision becomes exact. This trade-off must be stated in any report.

## 5. Implementeringsarkitektur: 2-Takts Interleaved Serial Slicing (1 Kort) vs Parallell Slicing (2 Kort)

Eftersom $M_{33}^{MSB}$ och $M_{33}^{LSB}$ har helt olika strömnivåer och transkonduktans **måste de två skivorna ha två helt oberoende kompensations- och tränings-states** ($M_8^{MSB}$ och $M_8^{LSB}$). Om man försöker dela samma $M_8$ kastar den sig fram och tillbaka och förstör konvergensen.

### Alternativ A: 2-Takts Interleaved Serial på 1 Kort (Växling varannan Refresh)
För forskningsfasen där vi kör på Card 1 utan att behöva bygga om nätverk eller IP:
- **Refresh-cykel $2k$ (MSB-takt):**
  1. Ladda $M_{33}^{MSB}$ och det sparade tillståndet $M_8^{MSB}$ till 2T1C via DAC.
  2. Evaluera insignal $X$ -> analog ADC-respons $Y_{MSB}$.
  3. Kör 1 steg lokal SGD: uppdatera enbart $M_8^{MSB}$ mot $z_{target}^{MSB}$.
- **Refresh-cykel $2k+1$ (LSB-takt):**
  1. Ladda $M_{33}^{LSB}$ och det sparade tillståndet $M_8^{LSB}$ till 2T1C via DAC.
  2. Evaluera samma insignal $X$ -> analog ADC-respons $Y_{LSB}$.
  3. Kör 1 steg lokal SGD: uppdatera enbart $M_8^{LSB}$ mot $z_{target}^{LSB}$.
- **Rekombination efter paret (tar exakt 2 refresh-cykler):**
  $$Y_{total} = (Y_{MSB}^{restored} \ll 4) + Y_{LSB}^{restored}$$
- **Kondensator- och analoga fördelar:**
  Varje refresh laddar grindarna från DAC:arna. 2T1C-cellerna får exakt rätt analog spänning varje gång. Noll minneseffekt, noll hysteres mellan MSB och LSB.

### Alternativ B: Parallell Dual-Card Slicing (2 Kort)
När Card 2 är anslutet på IP `192.168.1.51`:
- **Card 1:** Permanent laddad med $M_{33}^{MSB}$, lokal Mode A-loop uppdaterar kontinuerligt $M_8^{MSB}$.
- **Card 2:** Permanent laddad med $M_{33}^{LSB}$, lokal Mode A-loop uppdaterar kontinuerligt $M_8^{LSB}$.
- Host skickar samma $X$ till båda korten parallellt, hämtar telemetri i samma epok, och utför integer restoration och shift-add.

## 6. Dual-Card Hardware Protocol

| Item | Card 1 | Card 2 |
| :--- | :--- | :--- |
| Role | MSB slice | LSB slice |
| IP (planned) | 192.168.1.50 | 192.168.1.51 (needs firmware build variant: `MY_IP` + unique MAC in `main.c`) |
| M33 slice | `W_H` (scaled into DAC range) | `W_L` |
| Training | Own Mode A loop vs own slice `z_target` | Own Mode A loop vs own slice `z_target` |

Synchronisation requirements:
1. Both cards must evaluate the **identical** input slice vector each epoch. Firmware currently draws white noise internally (`maml_generate_new_white_noise_ref`, PRNG). Need either a host `SET_X_REF` command or a shared PRNG seed command. Verify before running.
2. Host sends epoch trigger to both, collects both telemetry packets (same epoch id), performs only the ALLOWED operations of Section 1.
3. Combined ENOB is computed against the **exact digital integer reference** `X . W` (full 8-bit operands), on the full combined scale. Report per-slice ENOB, per-slice misround rate, and combined ENOB.

## 8. Arkitektonisk Jämförelse & Inbyggda Fördelar (SE 2630397-4 vs Etablerade Metoder)

### 8.1 Problemet med Etablerade Metoder (Digital Korrigering i Full Bandbredd)
I konventionella analoga in-memory computing-arkitekturer uppstår ett grundläggande problem vid bit-slicing:
1. **Analog drift och olinjäritet:** Termisk drift och transkonduktansvariationer gör att varje analog kolumn kontinuerligt förskjuter sin offset och förstärkning ($\alpha_j, \beta_j$).
2. **Externt digitalt "plåster":** Etablerade metoder kompenserar ofta detta genom att placera en digital DSP-korrigerare efter ADC:n som applicerar linjär regression eller adaptiva skalningsfaktorer:
   $$Y_j^{corr} = \alpha_j \cdot ADC_j + \beta_j$$
3. **Svagheter med denna metod:**
   - **Hög energiförbrukning:** Korrigeringsblocket måste köra digitala multiplikationer i **full datahastighet (GHz/full bandbredd)**, vilket raderar en stor del av den analoga beräkningsfördelen.
   - **Förlust av dynamiskt omfång:** Om analog drift förskjuter signalen mot ADC:ns mättnadsgränser kan ett digitalt block efteråt inte återskapa förlorad information.
   - **Instabilitet vid Bit Slicing:** När MSB- och LSB-skivor har oberoende, tidsberoende förstärkningsfel multipliceras felen vid rekombinationen ($16 \cdot Y_{MSB} + Y_{LSB}$), vilket kräver kontinuerlig, beräkningstung omkalibrering av skalningsparametrarna.

### 8.2 Inbyggd Naturlig Styrka i Inverted MAML (SE 2630397-4)
Inverted MAML adresserar problemet direkt vid den fysikaliska källan genom två integrerade principer:

1. **Intrinsic Analog Compensation vid Strömsummeringspunkten:**
   - Kompensationen sker i den **analoga strömdomänen direkt på transimpedansförstärkarens (ColTIA) virtuella jord** via kompensationsgrenen ($M_8$ driven av $M_3 \rightarrow \text{Sigmoid 4}$).
   - Istället för att justera digitala tal i efterhand neutraliseras parasitströmmar och termisk DC-drift fysiskt innan signalen når ADC:n.
   - Förstärkaren och ADC:n hålls därmed låsta i sitt optimala linjära fönster (maximalt dynamiskt omfång, noll bottning).

2. **Sparse Låg-Bandbredds Digital Kontroll (Sub-milliwatt overhead):**
   - Datavägen genom $M_{33}$ körs i full analog hastighet utan några digitala multiplikationer eller adaptiva skalningslager.
   - Den digitala handledaren (Mode A SGD) opererar uteslutande i **låg bandbredd (sparse)** vid uppdateringsfrekvenser (t.ex. 100 Hz vid refresh-intervall, eller $K=1$).
   - Detta speglar fysikens verkliga tidskonstanter (termisk drift sker på millisekund- till sekundnivå) och minimerar digital styrförbrukning.

3. **Inbyggd Stabilitet vid Bit Slicing (MSB/LSB):**
   - Varje skiva ($M_{33}^{MSB}$ och $M_{33}^{LSB}$) bibehåller sitt eget oberoende kompensationsjämviktsläge ($M_8^{MSB}$ och $M_8^{LSB}$).
   - Båda skivorna regleras naturligt mot fasta, fysikaliska kiselnivåer med strikt nollpunkts- och förstärkningslåsning.
   - Rekombinationen sker med fasta, ideala binära vikter ($16$ och $1$) utan behov av adaptiva flyttande mål eller mjukvarukalibrering.
1. Single card, M33 max +/-60, K=1, white noise, 25 % heater duty: confirm >= 4.0 b with margin when training ON (fails with training OFF is acceptable).
2. Single card, slice-shaped payload (e.g. 1-bit inputs x small-level weights): measure RMSE vs grid step, misround rate. Go/no-go: misround < 0.3 %.
3. Firmware variant for Card 2 (IP .51), dual-card sync test with identical X.
4. Dual-card bit-sliced run, thermal cycling, report combined ENOB with/without training.

## 7. Reporting Checklist
- [ ] Combined ENOB measured vs exact digital reference, not vs card targets.
- [ ] Per-slice RMSE, grid step, misround rate.
- [ ] Explicit list of digital operations used (only Section 1 ALLOWED items).
- [ ] Training ON vs OFF ablation for each slice.
- [ ] Number of analog evaluations per MAC (throughput cost).

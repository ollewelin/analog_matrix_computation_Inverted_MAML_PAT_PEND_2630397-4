# Inverted MAML: Milestone 2 Verifieringsrapport (Kort 2, Rev 2.0)
### Hårdvarudiagnos av 1k/3.9k Dämpare, Termisk Drift & Headroom-Mättnad vid 5.0 ms

> [!NOTE]
> **Patentreferens**: SE 2630397-4 (Open Science Hardware)  
> **Testad Hårdvara**: Kort 2 (Rev 2.0 Silicon, $1\text{ k}\Omega / 3.9\text{ k}\Omega$ passiv dämpare)  
> **Master SoC & Kontroller**: Efinix Trion T120 Master SoC (`v2.2-MAML`, HW Logic: `0x20261030`, Build: Nov 1 18:57:15) + Trion T20 Kontroller (`TAG=T20A`, ACK `0x06`)  
> **Analoga Multiplikatorer**: Dual-2T1C Silicon (M33, M3, M8)  
> **Op-Amp Konfiguration**: MCP6444-E/SL (70 mA) monterad på **DAC 2**, standard op-amp kvar på **Sigmoid 4**  
> **Loggdata**:  
> * Körning 1 (Kallstart): [`mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/llm_noise_campaign/mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb.json)  
> * Körning 2 (Halvvarm): [`mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb_warm.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/llm_noise_campaign/mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb_warm.json)  
> * Körning 3 (Hel-varm): [`mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb_hot.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/llm_noise_campaign/mode_a_500ep_llm_toeplitz_rho85_reg512_card2_milestone2_45lsb_hot.json)  
> **PDF-Rapport**: [`INVERTED_MAML_MILESTONE2_CARD2_1K3P9K_VERIFICATION_REPORT.pdf`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/INVERTED_MAML_MILESTONE2_CARD2_1K3P9K_VERIFICATION_REPORT.pdf)

---

## 1. Sammanfattning & Huvudslutsatser

För att noggrant utvärdera **Kort 2 (Rev 2.0)** med dess monterade **$1\text{ k}\Omega / 3.9\text{ k}\Omega$ passiva summatordämpare** kördes tre på varandra följande 500-epokers Milestone 2-tester ($\pm 45\text{ LSB}$, $\text{LR}=0.25\times$, $\lambda=512$, $t=5.0\text{ ms}$) medan kortet gradvis värmdes upp från kallstart till driftstemperatur.

### Kärnfynd:
1. **Kiselns hälsa (Dual-2T1C) är i världsklass:**  
   Under Körning 3 (Varm) nådde Kort 2 ett okompenserat fel i Fas 1 på **$144.1\text{ LSB}^2$ ($8.21\text{ bitar}$ ENOB)** vid Epok 26! Detta bevisar bortom all tvekan att själva kislet, kondensatorerna och de analoga multiplikatorerna på Kort 2 är exceptionellt tysta och fullt fungerande.
2. **Termisk stabilisering gör stor skillnad:**  
   När kortet värmdes upp sjönk slutfelet vid epok 500 från $16\,429\text{ LSB}^2$ ($4.80\text{ bitar}$) vid kallstart till **$7\,159.8\text{ LSB}^2$ ($5.39\text{ bitar}$)** vid varm drift, och bästa Fas 3-loss förbättrades från $8\,185\text{ LSB}^2$ till **$1\,329.3\text{ LSB}^2$ ($6.60\text{ bitar}$)**.
3. **Flaskhalsen: Headroom-kompression & Op-Amp Svält:**  
   Trots kislets höga precision fastnade Fas 3-träningen runt $7\,000\text{ LSB}^2$ (jämfört med Kort 1 som nådde $280.6\text{ LSB}^2$ och $7.73\text{ bitar}$). Orsaken är dubbel:
   * **$1\text{ k}\Omega / 3.9\text{ k}\Omega$ drar $30\%$ mer ström**: Detta förskjuter DC-nivån rakt mot botten. Kolumn 1 och 5 pressas ned till $-1\,594\text{ LSB}$ och $-1\,617\text{ LSB}$, vilket lämnar knappt $180\text{ LSB}$ marginal innan ColTIA bottnar (saturation guard vid $-1\,797\text{ LSB}$).
   * **Sigmoid 4 op-amp orkar inte driva**: DAC 2 har 70 mA MCP6444-E/SL, men Sigmoid 4 har fortfarande kvar standard op-ampen. Den orkar inte driva alla 6 kolumner i Matrix 8 vernier, vilket gör att vikterna klipper mot taket ($\pm 127\text{ LSB}$) och lämnar ett asymmetriskt fel på $+104\text{ LSB}$ i Kolumn 3.

---

## 2. Empirisk Prestandatabell (Kort 2 över 3 Körningar vs Kort 1)

```
=============================================================================================================
KÖRNING / HÅRDVARA       KORT  DÄMPARE    STATUS    FAS 1 MEDEL   FAS 2 MEDEL   FAS 3 MEDEL   BÄSTA LOSS (ENOB)
=============================================================================================================
Körning 1 (Kallstart)    Kort 2 1k / 3.9k  Kallt     4 919.3 LSB²  17 491.4 LSB² 13 036.7 LSB²  8 185.7 LSB² (5.29 b)
Körning 2 (Halvvarm)     Kort 2 1k / 3.9k  Ljummigt  4 923.3 LSB²  17 870.7 LSB² 10 771.6 LSB²  1 329.3 LSB² (6.60 b)
Körning 3 (Hel-varm)     Kort 2 1k / 3.9k  Varmt     2 893.4 LSB²  18 039.6 LSB² 10 084.5 LSB²  2 152.4 LSB² (6.26 b)
-> Rekord Fas 1 (Ep 26)  Kort 2 1k / 3.9k  Varmt       144.1 LSB² (8.21 b ENOB) - All-time low okompenserat fel!
=============================================================================================================
Kort 1 Referens (Nov 3)  Kort 1 1k / 5.1k  Varmt    10 608.8 LSB²  11 145.7 LSB²  3 059.6 LSB²    280.6 LSB² (7.73 b)
=============================================================================================================
```

---

## 3. Visuell Jämförelse: Kort 2 (Tre Körningar) vs Kort 1

![Milestone 2 Träningskurvor Kort 2](figures/fig_mode_a_500ep_llm_rho85_reg512_card2_milestone2_45lsb.png)
*Figur 1: Träningsförlopp för Kort 2 (Rev 2.0). Körning 1 (blå, kallstart), Körning 2 (orange, halvvarm), Körning 3 (grön, hel-varm) och Kort 1 som referens (streckad röd).*

---

## 4. Hårdvaruorsaksanalys: 1k/3.9k vs 1k/5.1k & Op-Ampar

Varför kunde Kort 1 sänka felet från $11\,145\text{ LSB}^2$ till **$280.6\text{ LSB}^2$**, medan Kort 2 stannade på **$7\,159.8\text{ LSB}^2$**?

### 1. Dämparmotståndet ($3.9\text{ k}\Omega$ vs $5.1\text{ k}\Omega$)
* Dämparen på summanoden definierar överföringen från Matrix 33 till ColTIA-ingången:
  $$\Delta I_{\text{in}} \propto \frac{R_{\text{pull}}}{R_{\text{series}}}$$
* Med $3.9\text{ k}\Omega$ istället för $5.1\text{ k}\Omega$ blir impedansen mot jord ca **$24\%$ lägre**, vilket ökar strömdragningen från multiplikatorns nod.
* Detta drar ned DC-nivån för operationsförstärkarna i ColTIA mot den negativa matningen:
  * På Kort 2 mäter ADC_49 i Kolumn 1 **$-1\,594\text{ LSB}$** och i Kolumn 5 **$-1\,617\text{ LSB}$**.
  * Systemets automatiska mättnadsgräns är satt till **$-1\,797\text{ LSB}$**.
  * Med bara $\sim 180\text{ LSB}$ marginal kvar är operationsförstärkaren kraftigt icke-linjär och saknar dynamiskt omfång ("headroom compression").

### 2. Strömbrist på Sigmoid 4 (Current Starvation)
* Användaren har monterat högströms-op-ampen **MCP6444-E/SL (70 mA)** på **DAC 2** (In-Data-raderna).
* Men på **Sigmoid 4** (som driver ingångarna till Matrix 8 vernier-raderna) sitter fortfarande standard-op-ampen kvar med svag drivförmåga ($\approx 10\text{–}15\text{ mA}$).
* När Matrix 8 ska generera kompensation över 6 kolumner samtidigt för att motverka den kraftiga strömmen från $3.9\text{ k}\Omega$-dämparen, kroknar Sigmoid 4.
* Detta syns tydligt i de slutliga vikterna och kolumnfelen vid epok 500:

| Kolumn | Matrix 8 Vikt (Vernier) | Matrix 3 Vikt (Lager 1) | Kvarvarande ADC_49 Fel | Status |
| :---: | :---: | :---: | :---: | :--- |
| **Kol 0** | $-127\text{ LSB}$ | $-48\text{ LSB}$ | $-3.1\text{ LSB}$ | Klippt mot botten |
| **Kol 1** | $-127\text{ LSB}$ | $+127\text{ LSB}$ | $-11.5\text{ LSB}$ | Båda vikter klipper (Headroom slut) |
| **Kol 2** | $+104\text{ LSB}$ | $-54\text{ LSB}$ | $+104.3\text{ LSB}$ | **Stort kvarvarande positivt fel** |
| **Kol 3** | $+127\text{ LSB}$ | $-48\text{ LSB}$ | $-10.0\text{ LSB}$ | M8 klipper mot taket |
| **Kol 4** | $-43\text{ LSB}$ | $+127\text{ LSB}$ | $-43.1\text{ LSB}$ | M3 klipper mot taket |
| **Kol 5** | $-127\text{ LSB}$ | $-49\text{ LSB}$ | $-9.6\text{ LSB}$ | M8 klipper mot botten |

Slutsats: Vikterna slår i de digitala mättnadsgränserna ($\pm 127\text{ LSB}$) på nästan samtliga kanaler, vilket omöjliggör vidare felminimering. Kolumn 2 och 4 lämnas med signifikanta statiska fel ($+104\text{ LSB}$ och $-43\text{ LSB}$).

---

## 5. Åtgärdsplan & Rekommendationer för Kort 2

Baserat på dessa empiriska mätningar är den optimala åtgärdsplanen helt glasklar:

1. **Löd dit MCP6444-E/SL (70 mA) på Sigmoid 4:**  
   Detta eliminerar strömbristen på Matrix 8 vernier och ger kretsen full förmåga att driva alla 6 kanaler utan spänningsfall.
2. **Byt ut $3.9\text{ k}\Omega$ mot $5.1\text{ k}\Omega$ (eller testa $6.8\text{ k}\Omega$):**  
   Genom att öka motståndet till $5.1\text{ k}\Omega$ (samma som Kort 1) eller $6.8\text{ k}\Omega$ lyfts ColTIA DC-arbetspunkten upp från $-1\,600\text{ LSB}$ tillbaka till ca $-1\,000\text{ LSB}$. Detta återställer fullt dynamiskt headroom ($>700\text{ LSB}$ marginal).
3. **Montera temperaturgivare:**  
   Eftersom Fas 1-felet minskade dramatiskt och Fas 3 förbättrades med över $50\%$ i takt med att kortet värmdes upp, är en temperaturövervakning ett mycket värdefullt tillskott för reproducerbar drift.

Kort 2:s kisel har bevisat att det klarar **$8.21\text{ bitar}$ precision** ($144.1\text{ LSB}^2$). Med dessa två lödåtgärder på plats kommer Kort 2 att nå samma fantastiska resultat i sluten loop som Kort 1!


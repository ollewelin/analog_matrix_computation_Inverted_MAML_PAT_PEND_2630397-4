# Inverted MAML: T120 CLI Snabbguide
### Manuella kommandon för programmering och experimentkörning

> **Miljö-tips**: Kör alltid med Anaconda Python för att undvika versionskonflikter i bibliotek (`numpy`/`matplotlib`):
> ```bash
> conda activate base
> # eller använd direkt: /home/olle/anaconda3/bin/python
> ```

---

## 1. Lägga på mjukvara på T120 (3 alternativ)

### A. Snabb JTAG SRAM-programmering (~6 sekunder)
Programmerar den senaste färdigsyntetiserade bitstreamen direkt in i T120 FPGA:ns SRAM via JTAG:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/program_t120.py
```
* **Vad det gör**: Laddar `FPGA_code/T120F324/outflow/T120_MALM.bit` direkt över FTDI JTAG. Snabbaste sättet att få igång kortet.

---

### B. Kompilera C-firmware & patcha BRAM via JTAG (~10–15 sekunder)
Kompilerar om RISC-V C-koden, patchar BRAM-minnet och laddar upp via JTAG:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/flash_soc.py
```
* **Vad det gör**: Bygger `FPGA_code/sw/t120_master/src/main.c`, uppdaterar BRAM-innehållet i bitstreamen och flashar till FPGA:n utan att behöva göra en fullständig FPGA-syntes.

---

### C. Permanent programmering till SPI Flash
Bränner bitstreamen till det externa SPI-flashminnet så att mjukvaran finns kvar efter strömavbrott/omstart:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/program_t120.py --mode active
```
* **Vad det gör**: Konfigurerar FTDI-chippet i aktivt SPI-flashläge och skriver `T120_MALM.hex` till flash-minnet.

---

## 2. Verifiera kontakt och version (Version Guard)

Kontrollera att T120 svarar på UDP och har rätt hårdvaru- och mjukvaruversion:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/verify_and_guard_version.py
```
* **Vad det gör**: Frågar T120 över nätverket (`192.168.1.50:5000`) och verifierar HW Logic (`0x20261030`) och SW Firmware (`v2.2-MAML`).

---

## 3. Starta senaste körningen mot ett nytt loggfilsnamn

Starta en 500-epokers Milestone 2-träning i Mode A ($\pm 45\text{ LSB}$, $\text{LR}=0.25$, $\lambda=512$, Toeplitz $\rho=0.85$, $5.0\text{ ms}$):

```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_500ep_llm_regularization.py --tag DITT_NAMN
```

* **Exempel**:
  ```bash
  /home/olle/anaconda3/bin/python FPGA_code/scripts/run_500ep_llm_regularization.py --tag card2_test_mod
  ```
* **Vad det gör**:
  1. Verifierar T120-versionen via UDP.
  2. Nollställer och centrerar vikterna i multiplikatorkisel (Dual-2T1C).
  3. Kör 500 epoker med kontinuerligt roterande LLM Toeplitz-brusvektorer.
  4. Sparar telemetridata till JSON:  
     `FPGA_code/logs/llm_noise_campaign/mode_a_500ep_llm_toeplitz_rho85_reg512_DITT_NAMN.json`
  5. Genererar automatiskt en träningsgraf (PNG):  
     `FPGA_code/docs/figures/fig_mode_a_500ep_llm_rho85_reg512_DITT_NAMN.png`

---

## 4. Valfria flaggor för anpassade test

Om du vill justera parametrar manuellt i körningen:

```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_500ep_llm_regularization.py \
    --epochs 500 \
    --lr 0.25 \
    --reg-lambda 512 \
    --d-line 2 \
    --tag mitt_test
```
* `--epochs`: Antal epoker (default `500`).
* `--lr`: Lärhastighet / step size (default `0.25`).
* `--reg-lambda`: L2-regularisering (default `512`).
* `--d-line`: Dämparfaktor för signalnivå (`2` ger $\pm 40\text{–}45\text{ LSB}$, `1` ger $\pm 80\text{ LSB}$).
* `--tag`: Suffix för logg- och bildfilerna.


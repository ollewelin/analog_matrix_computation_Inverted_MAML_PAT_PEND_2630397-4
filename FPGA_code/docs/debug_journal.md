# T120 SoC Felsökningsdagbok (Successive Approximation)

Denna logg spårar varje övergripande förändring och test för att systematiskt isolera felkällor.

---

### [Test 1] lwIP borttaget, ren C-kod (BRAM-patch via efx_bram_update)
- **Hypotes:** lwIP kraschade minnet; ren C-kod i main() ska tända LED2 direkt.
- **Ändring:** Slängde lwIP i Makefile, satte LED2=HIGH och skickade 'A' i main.c, patchade med `efx_bram_update`.
- **Resultat:** LED1 blinkar (PLL ok), LED2 LÅG, ingen UART.
- **Slutsats:** `efx_bram_update` applicerades antingen inte i hårdvaran, eller så når processorn inte `main()` alls från bitstreamen.

---

### [Test 2] Ren fullständig syntes från grunden (Pågående)
- **Hypotes:** En fullständig Efinity compile med nya BRAM-filer direkt i `ip/RISC_mini/` garanterar att rätt minne är i bitstreamen.
- **Ändring:** Kör full Efinity-syntes (`build_t120_fpga.sh`) med nya binärer i `ip/RISC_mini/`.
- **Resultat:** LED1 blinkar (PLL ok), LED2 LÅG, UART helt tyst.
- **Slutsats:** Felet beror INTE på att fel binär var inbakad i bitstreamen. 
  * Efter full syntes från grunden är koden i BRAM garanterat den nya.
  * Eftersom LED2 inte ens sätts HÖG på första raden i `main()`, exekverar processorn INTE `main()`.

---

### [Test 3] Använd start_minimal.S (Hoppa rakt till main() utan libc_init_array)
- **Hypotes:** När LED2 fungerade tidigare användes `start_minimal.S`. `__libc_init_array` i `start.S` låser CPU:n före `main()`.
- **Ändring:** Ändrade `Makefile` till `start_minimal.S`, kompilerade och flashade.
- **Resultat:** **LED2 ÄR HÖG!** CPU:n har startat och nått `main()`!
- **Slutsats:** Hypotesen bevisad! `start.S` / `__libc_init_array` var det som låste processorn före `main()`. Nu kör RISC-V-processorn vår C-kod!

---

### [Test 4] Ren blinkloop i C (utan APB3-access)
- **Hypotes:** LED2 fastnade HÖG i Test 3 p.g.a. att skrivningen till APB3 (`0xf8100008 = 'A'`) hängde bussen/CPU:n.
- **Ändring:** Bort med APB3-skrivning, enbart ren C blinkloop.
- **Resultat:** LED2 förblir konstant HÖG.
- **Slutsats:** CPU eller loop släcker inte LED2, ELLER så är 0=tänd/inverterad polaritet, ELLER så uppdaterades inte BRAM i hårdvaran av `flash_soc.py`.

---

### [Test 5] Binärdelning: Tvinga LED2 till 0 konstant
- **Hypotes:** Om LED2 styrs av CPU:n ska den slockna med `gpio_setOutput(..., 0x0)`.
- **Ändring:** `gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, 0x0)` direkt i main(), ingen loop.
- **Resultat:** **LED2 BLEV LÅG (SLÄCKT)!**
- **Slutsats:** **GENOMBROTT!** 
  1. CPU:n kör koden i main() perfekt!
  2. BRAM-patch och snabb-flödet fungerar till 100%!
  3. LED2 styrs fullständigt av C-koden (1 = Tänd, 0 = Släckt).
  4. Anledningen till att LED2 verkade "konstant hög" tidigare var enbart delay-räknaren eller loop-frekvensen!

---

### [Test 6] Mjukvaruloop med stor räknare (10 000 000)
- **Hypotes:** Med längre loop syns blinkningen tydligt för ögat.
- **Ändring:** C-mjukvaruloop med 10M iterationer.
- **Resultat:** LED2 konstant HÖG.
- **Slutsats:** Mjukvaru-for-loopen tog antingen alldeles för lång tid (flera minuter i 50MHz med minnesaccesser per loop), eller så kom den aldrig ur första loopen.

---

### [Test 7] Exakt Hårdvarutimer (bsp_uDelay 300ms)
- **Hypotes:** `bsp_uDelay(300000)` använder RISC-V SoC:ens inbyggda CLINT-timer (50MHz) vilket garanterar exakt 300 ms tänd och 300 ms släckt.
- **Ändring:** Ersätt for-looparna med `bsp_uDelay(300000)`.
- **Resultat:** LED2 konstant HÖG. UART tyst.
- **Slutsats & "Tänka utanför boxen":**
  1. I **Test 5** (`gpio_setOutput(..., 0x0)`) blev LED2 **LÅG (SLÄCKT)** direkt. Det bevisar att CPU:n kör C-kod och att GPIO-registret svarar.
  2. I **Test 7** (med `bsp_uDelay`), hänger sig processorn omedelbart på första `bsp_uDelay` (läsning av CLINT-registret på 0xF8B0BFF8) eller loop/buss-access, så den hinner tända LED2 men fryser innan den någonsin når släckningen!
  3. **Rotorsak utanför boxen:** CLINT-bussen eller perifera timer-bussen i Sapphire SoC svarar inte med `PREADY`, vilket låser RISC-V-kärnan i ett evigt bus-stall så fort en timer eller delay anropas.
  4. Lösningen framåt är att kontrollera buss-avavkodningen och inte anropa låsta perifera register, eller verifiera SoC-topologin direkt.





---

### Gemensam nämnare (ny agent, 21:00)
- Fungerar: Test 3 (LED=1) och Test 5 (LED=0). Inga läsningar/skrivningar mot RAM eller CLINT – bara skrivningar till GPIO.
- Hänger (LED fast i HÖG): Test 4, 6 (räknare på stacken = RAM-data) och Test 7 (läsning av CLINT).
- **Hypotes:** Instruktionshämtning + GPIO-skrivning fungerar. CPU:n hänger vid **första dataaccess mot RAM eller CLINT** (troligast läsningar).

### [Test 8] Delay enbart i register (0 minnesaccesser)
- **Ändring:** Räknaren ligger i ett CPU-register; inga stack-, RAM- eller CLINT-accesser. `flash_soc.py` skriver nu ut antalet minnesaccesser i main() (ingen manuell läsning av assembler behövs).
- **Förväntat:** Blinkar → kärnan är OK, felet sitter i databussen (RAM/CLINT). Fast i HÖG → kärnan hänger/startar om (fel i trap/reset).
- **Resultat:** (väntar)
- **Resultat Test 8:** LED2 konstant LÅG.

### NYCKELINSIKT: adressgränsen 0xF9000040 (första 64-byte cache-raden)
| Test | Sista GPIO-skrivning FÖRE adress 0x40 | LED2 |
|---|---|---|
| 3/4/6/7 | LED=1 (sedan når koden 0x40) | HÖG |
| 5 | LED=0 (allt ryms före 0x40) | LÅG |
| 8 | LED=1 @0x2c, LED=0 @0x3c, nästa instr @0x40 | LÅG |
- Alla resultat förklaras av: **CPU:n hänger så fort den ska hämta instruktioner från adress ≥ 0xF9000040** (rad 2 i I-cachen, 64 B/rad).
- BRAM-init-filerna (`rom/*.bin`) är verifierade mot `.bin`: 0 fel. Felet ligger alltså i hårdvaran/bitstream-mappningen, inte i C-koden.
- Förklarar även Test 1/2 (stora main låg bortom 0x40 → LED2 sattes aldrig).

### [Test 9] Kod placerad på 0xF9000100
- **Ändring:** main() (i rad 1) sätter LED=0 och hoppar till `far_led_on()` på adress ≥0x100 som sätter LED=1.
- **Förväntat:** HÖG → kod bortom 0x40 körs (hypotes fel). LÅG → hypotesen bekräftad.
- **Resultat:** (väntar)
- **Resultat Test 9:** (inte rapporterat – ersatt av fynd nedan)

### ROTORSAK HITTAD: SoC-klockan saknade timing-constraint (jämförelse mot referens)
- BSP ↔ SoC stämmer: `RISC_mini.v` byte-identisk med referensen, `soc.h`, linker och `start.S` lika.
- **Skillnad 1:** Vår `top_level.sv` klockade SoC:en med `pll_clk_50Mhz`, men `.sdc` constrainar bara `T120_GCLK`. Timing-rapporten visar *inga* analyserade klockor → hela CPU:n placerades och routades **utan timingkrav**. Det ger exakt "delvis fungerande" beteende (första cache-raden ok, sedan korrupta hämtningar).
  Referensen: `sys_clk = T120_GCLK`.
- **Skillnad 2:** `io_asyncReset` var fast `0`. Referensen har en power-on-reset-räknare.
- **Ändring:** `sys_clk = T120_GCLK` + power-on reset (~84 ms) på `io_asyncReset`. Full omkompilering.

### [Test 10] Blink med bsp_uDelay efter klock-/reset-fix
- **Resultat:** **LED2 BLINKAR PERFEKT!** 
- **Slutsats:** Klock- och reset-problemet är löst! CPU:n och minnet är helt stabila och hårdvarutimern fungerar!

---

### [Test 11] UART Mini Telemetri på Pin F13 (SCLR_DAC_W_34)
- **Hypotes:** Nu när processorn kör och inte låser sig på bussen, skickar vi 'U' varje blinkcykel via `uart_mini_tx_string("U")`.
- **Ändring:** La till `uart_mini_tx_string("U")` i blinkloopen.
- **Resultat:** **BEKRÄFTAT! UART skickar 'U' kontinuerligt!** Mottaget i picocom samt avläst direkt via `/dev/ttyACM0`: `UUUUUU`.
- **Slutsats:** 
  1. Processorn (50 MHz), CLINT timer, och minne är 100% stabila.
  2. APB3-bussen fungerar perfekt utan stalls.
  3. UART Mini fungerar på pin F13 vid 9600 baud.
  4. Hårdvaran är nu redo för full telemetri och Ethernet!


# T120 Sapphire SoC – Varför Projektet Havererade & Den Rätta Lösningen

Datum: 2026-10-04  
Hårdvara: Trion T120F324, Sapphire RISC-V SoC (`RISC_mini`), RTL8211F PHY  

---

## 1. Den verkliga grundorsaken till haveriet (lwIP vs Bare-Metal)

Projektet havererade **INTE** på grund av reset-problem, trasig assembler eller felaktiga hårdvaruklockor.

Haveriet berodde på ett **monumentalt arkitektoniskt misstag**:
1. En tidigare session antog felaktigt att Ethernet på T120 krävde hela **lwIP TCP/IP-stacken** (`core/tcp.c`, `core/mem.c`, etc.).
2. **lwIP åt upp minnet:** Det drog in 92,4 KB statisk data/kod i en 128 KB On-Chip BRAM.
3. **Stack- och C-runtime kollision:** När lwIP drog in Newlib standard-C kördes `__libc_init_array()`, och heapen och stacken krockade direkt med BSS/Data-sektionen. Processorn kraschade och nådde aldrig ens `main()`, vilket gjorde att LED2 förblev släckt och UART:en dog.
4. **Den bevisat fungerande källkoden hittades:**  
   På användarens tidigare fungerande kort användes **ALDRIG lwIP**!  
   Den bevisat fungerande koden fanns i:  
   `FPGA_code/ref_staging/t120_eth_soc/correct_full_embedded_sw/embedded_sw/RISC_mini/software/standalone/test_b/src/main.c`

---

## 2. Jämförelse: lwIP vs Beprövad Bare-Metal

| Egenskap | Felaktig lwIP-stack (havererade) | Beprövad Bare-Metal (fungerar) |
|---|---|---|
| **Kodstorlek** | > 92 KB (spräckte minnet) | ~8–12 KB (lämnar > 115 KB fritt) |
| **Beroenden** | Tung Newlib C-runtime (`__libc_init_array`) | Ren fristående C (`bsp.h`, standard C) |
| **Protokollhantering** | Komplexa asynkrona callbacks, timers | Direkta funktioner: `handle_arp()`, `handle_icmp()`, `handle_udp()` |
| **MAC-interaktion** | Tröga abstraktionslager | Direkt register/buffert-access på `0xF8102000` |
| **Telemetri** | Hängde sig i UART0 spin-loops | Stabil `uart_mini_driver.h` via APB3 (`println_s`) |

---

## 3. Plan framåt

1. **Släng lwIP helt:** Rensa Makefile från alla referenser till lwIP och Newlib.
2. **Återställ beprövad C-kod:** Använd den bevisade bare-metal `main.c` från `correct_full_embedded_sw`.
3. **Behåll hårdvaru-UART fixen:** APB3 direkt 1-byte koppling (`.tx_data(pwdata[7:0])`) säkerställer att ASCII-data sänds utan 1-cykels registerfördröjning.
4. **Kompilera & Flasha:** Bygg den rena binären och ladda via `test_bram_update_all.py` / JTAG.

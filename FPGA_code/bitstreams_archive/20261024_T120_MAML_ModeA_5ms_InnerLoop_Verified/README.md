# Inverted MAML Trion T120 Bitstream & Firmware Archive

**Datum:** 2026-10-24  
**Arbetspunkt:** Mode A ($t = 5.0\text{ ms}$, `hadamard_delay_us = 5000`, $100\text{ Hz}$ refresh)  
**Beskrivning:**  
Verifierad FPGA-bitstream och C-firmware för Efinix Trion T120 Master SoC och T20 Controller.
Inkluderar fullständig verifiering enligt Patent SE 2630397-4:
- **Ekvation 1–7** (Icke-backprop Hadamard-gradienter, noll digital multiplicering med $x_i$).
- **Interleaved $2 \times 7 = 14$ pulser Sylvester-$H_8$ Simplex Hadamard** med 0 % överhörning och 0 % DC-drift.
- **Bärvågssökning (`best_k`) på `ADC_45`** för Sigmoid 10-lutning $\sigma_2'(y_j^{(8)})$.
- **$16\times$ hårdvarumedelvärdesbildning** på SAR ADC (`XC2361A`).
- **Full 6-kolumners drift** (ingen kolumnmaskering, alla 36 crosspoints aktiva).
- **Verifierad med rapport 1 & 2:**
  - Start-RMSE: $45.2\text{--}54.4\text{ LSB}$ ($5.2\text{--}5.5\text{ bitar}$ ENOB).
  - Konvergerad RMSE: $10.4\text{--}14.8\text{ LSB}$ ($7.1\text{--}7.6\text{ bitar}$ ENOB).

## Innehåll
- `T120_MALM.hex` — Färdig BRAM-patchad bitstream i Intel HEX-format för aktiv/passiv konfigurering.
- `T120_MALM.bit` — Färdig bitstream i binärt format för JTAG/SPI.
- `t120_master.bin` — Rå RISC-V BRAM-binär ($128\text{ KB}$).
- `t120_master.elf` — Kompilerad ELF med debug-symboler.
- `t120_master.hex` — Minnesbild i HEX-format.
- `t120_master.asm` — Disassemblerad RISC-V maskinkod.
- `t120_master.map` — Länkarkarta med minnesadresser och sektionsstorlekar.


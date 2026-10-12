# EasyEDA Schematic Query & Circuit Analysis

## Rule: No Direct Inspection of Raw 10MB Files
Never load or scan raw Inverted_MAML_IMC.epro2 or .epru directly into LLM context. Use Python mappers to generate lightweight JSON and reports.

## Intermediate Generation Flow
Run from FPGA_code/Auto_gen_Interface_spec_FPGA/:
- T120: python3 t120_easyeda_mapper.py --source Inverted_MAML_IMC/Inverted_MAML_IMC.epru --pinout T120_pin_map.xlsx --json olle_test1_t120_connection.json --report olle_Test1_connection_report.txt --xml-template T120_MALM_template.peri.xml --xml-output T120_MALM.generated.peri.xml
- T20: python3 T20_easyeda_mapper.py --source Inverted_MAML_IMC/Inverted_MAML_IMC.epru --pinout T20F256_pin_map.xlsx --json T20F256_connections.json --report T20F256_connection_report.txt --xml-template T20F256_template.peri.xml --xml-output T20F256.generated.peri.xml

## Inspection via JSON
Query generated JSON files using jq:
- jq ' .pins[] | select(.external_components[]? | contains("U5")) | {package_pin, name, mode} ' olle_test1_t120_connection.json

## Authoritative Schematic Version (Version 1.3.2 — `2026-09-04`)
- **Authoritative File (Matches Physical PCB v1.3.2):** `EasyEDA/ProPrj_Inverted_MAML_6x6_2026-09-04.epro2` (ZIP archive containing `SHEET/*/*.esch`).
- **Pre-Fabrication Fixes Already Applied in Version 1.3.2:**
  1. `"Fix Bug 2026-09-04: TIA correct input to (-) instead of (+) and connect input (+) to common Vref (VR)"` — All TIA op-amps (`U3..U5$CBB49` for M3, `U3..U5$CBB9` for M8, `U3..U5$CBB19` for M33) have `In-` (`Pins 2, 6, 9, 13`) connected to the column lines (`COL+1..6`, `COL-1..6`) with `100 Ω` feedback to `Out` (`Pins 1, 7, 8, 14`), and `In+` (`Pins 3, 5, 10, 12`) tied to `VR` (`1.650 V`).
  2. `"Fix Bug 2026-09-04: MCP6024 Pin 11 to (-) GND VSS, Pin 4 to (+) VDD"` — All `MCP6024` quad op-amps have `Pin 4 = 3.3V (VDD)` and `Pin 11 = GND (VSS)`.
  - The `"Fix Bug 2026-09-04"` text annotations on the schematic sheets are **historical timestamps** documenting when the designer discovered and fixed those bugs **prior to PCB manufacturing**. Both the schematic v1.3.2 and the fabricated PCB are **100% correct**.
- **Outdated Draft Warning:** Do **NOT** use `EasyEDA/Autoplace_matrix/Inverted_MAML_IMC.epru` for analog/TIA netlist queries — it is an older pre-fix snapshot taken before the `2026-09-04` TIA and power-pin corrections.


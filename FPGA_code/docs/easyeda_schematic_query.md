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

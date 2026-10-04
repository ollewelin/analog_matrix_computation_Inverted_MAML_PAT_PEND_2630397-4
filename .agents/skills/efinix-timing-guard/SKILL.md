---
name: efinix-timing-guard
description: Automatisk kontroll av Efinity Static Timing Analysis (STA) samt metastabilitetsskydd för asynkrona ingångar. Säkerställer att alla klockor analyseras, varnar vid negativa slacks, och kontrollerar att fysiska ingångar har 2-stegs synkronisering.
---

# Efinix Timing & Input Synchronization Guard

Denna skill förhindrar tysta timinghaverier och metastabilitetsfel i Efinity-projekt på Trion T120.

## 1. Timing-regeln (STA i Efinity)
- Efinity propagerar **inte** automatiskt klockor genom interna PLL:er till logik om inte klockan explicit definierats i `.sdc` eller via `.pt.sdc`.
- Om en SoC-klocka saknas i `.sdc` rapporterar Efinity noll fel, men routar processorn och bussarna helt utan timingkrav. Det leder till slumpmässiga krascher och korrupta cache-/minnesaccesser.

## 2. Ingångs-regeln (Metastabilitet på asynkrona signaler)
- **ALLA** asynkrona insignaler från omvärlden (tryckknappar, switchar, externa flaggor, sensorer, RX-linjer etc.) **MÅSTE** passera minst två flip-flops (2-stage synchronizer / double-flop) i systemets klockdomän innan de används av logiken:
  ```systemverilog
  logic [1:0] ext_sig_sync;
  always_ff @(posedge sys_clk) begin
      ext_sig_sync <= {ext_sig_sync[0], ext_sig_raw};
  end
  wire ext_sig = ext_sig_sync[1];
  ```
- **Undantag:** Dedikerade hårdvarublock såsom DDIO (Double Data Rate I/O) där samplingen sker direkt i I/O-cellen mot dedikerad klocka.

## 3. Automatisk körning
Körs automatiskt efter syntes/Place & Route:
```bash
python3 .agents/skills/efinix-timing-guard/check_timing.py FPGA_code/T120F324/outflow/T120_MALM.timing.rpt FPGA_code/T120F324/top_level.sv
```
Om timingrapporten saknar analyserade klockor eller har negativ slack, avbryts flödet med rött felmeddelande.

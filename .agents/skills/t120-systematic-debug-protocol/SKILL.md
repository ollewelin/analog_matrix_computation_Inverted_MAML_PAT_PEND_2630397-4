---
name: t120-systematic-debug-protocol
description: Rigorös binärsöknings- och successive-approximation felsökningsmetod för Trion T120 SoC. Förhindrar slumpmässigt letande och assembler-grävande.
---

# T120 SoC Systematic Debug Protocol (Successive Approximation)

När SoC-beteende är okänt eller dött (t.ex. LED2 släckt, tyst UART), tillämpa **strikt binärsökning** och logga varje steg i den kortfattade felsökningsdagboken.

## 1. Gyllene Principer

1. **Halvera problemet (Successive Approximation):**
   - Ändra ALDRIG flera variabler samtidigt.
   - Fråga: Ligger felet i **Hårdvaran/Bitstreamen** (klocka, reset, routing) eller i **Mjukvaran/Firmware** (startkod, loopar, minne)?
2. **Korta, övergripande dagboksanteckningar:**
   - Varje test loggas i `FPGA_code/docs/debug_journal.md` med:
     * Test-ID & Hypotes
     * Övergripande ändring (1 mening)
     * Observerat resultat (JA / NEJ / VÄRDE)
     * Slutsats / Nästa halva
3. **Ingen assembler-mikrostyrning:**
   - Håll felsökningen på C-nivå och Verilog top-level nivå.
4. **Små, verifierbara milstolpar:**
   - Milstolpe 1: Statisk LED2 HIGH direkt vid start.
   - Milstolpe 2: Togglande LED2 (C-loop).
   - Milstolpe 3: UART skickar enskilda bytes ('A').
   - Milstolpe 4: Ethernet MAC / MDIO status.

## 2. Binärsöknings-Trädet (Beslutsträd)

```
                 Är LED2 TÄND?
                 /          \
               JA            NEJ
              /                \
   Kör CPU:n main()?       Når CPU:n ens main()?
   /              \          /               \
 Togglar den?   Fastnar?  Syntes-BRAM ok?   SoC i Reset / Klockfel?
```

## 3. Arbetsflöde för varje testcykel

1. **Formulera hypotes:** "Om vi kopplar bort X, ska Y ske."
2. **Applicera minsta möjliga ändring.**
3. **Bygg & Flasha med standardiserat skript.**
4. **Observera hårdvaran (LED1, LED2, Scope på F13).**
5. **Skriv kort notering i dagboken.**

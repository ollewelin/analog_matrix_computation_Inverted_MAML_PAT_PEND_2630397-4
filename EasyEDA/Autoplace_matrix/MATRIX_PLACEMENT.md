# Inverted MAML IMC — Matrix Auto-Placement Project

## Model in Use
GitHub Copilot using **Claude Sonnet 4.6**

---

## Project Overview

EasyEDA PCB project: `Inverted_MAML_IMC.epru` (≈9.5 MB)

The PCB is a massive matrix of 36 blocks arranged in rows and columns.
The blocks are made of three interleaved sub-matrices that share the same column/row grid:

| Matrix    | Schematic Title                        | Rows | Cols | Total Blocks | Notes                                      |
|-----------|----------------------------------------|------|------|--------------|--------------------------------------------|
| `matrix3` | MUL_CELL_2X_2T1C (rows 1–7)           | 8    | 6    | 48           | Rows 1–7 = same cell type as matrix8       |
| `matrix3` | REF_CELL_2X_2T1C (row 8 ONLY)         | —    | 6    | 6            | Row 8 = SPECIAL reference row, skip/manual |
| `matrix8` | MUL_CELL_2X_2T1C                      | 7    | 6    | 42           | Ends after row 7                           |
| `matrix33`| MUL_NO_H_CELL_2X_2T1C                | 6    | 6    | 36           | Ends after row 6                           |

The three sub-matrices are **interleaved** in the same physical PCB grid.
Blocks [Row 7, Row 8] for matrix33 are **empty holes** (no blocks placed there).
Block [Row 8] for matrix8 is also an **empty hole**.

---

## File Structure

```
Inverted_MAML_IMC/
├── Inverted_MAML_IMC.epru   ← Main PCB file (parse this for component positions)
├── project2.json
├── matx3/
│   ├── matx3.epru           ← Schematic for matrix3 (REF_CELL_2X_2T1C)
│   └── project2.json
├── matx8/
│   ├── matx8.epru           ← Schematic for matrix8 (MUL_CELL_2X_2T1C)
│   └── project2.json
├── matx33/
│   ├── matx33.epru          ← Schematic for matrix33 (MUL_NO_H_CELL_2X_2T1C)
│   └── project2.json
│
│   ── Python analysis scripts:
├── analyze_blocks.py        ← Parse PCB, show locked (placed) components
├── analyze_prefixes.py      ← Group components by Channel ID prefix + position
├── analyze_all_prefixes.py  ← Cleaner version, sorted by position
├── analyze_grid.py          ← Group sorted by grid row/col
└── find_locked.py           ← Show only the already-locked (placed) blocks
```

---

## EPRU File Format

The `.epru` files use a line-based format. Each line is:
```
{meta_json}||{data_json}|
```

Key record types:
- `DOCHEAD` — document metadata
- `META` — schematic/PCB title info
- `COMPONENT` — a placed component (footprint on PCB or symbol on schematic)
- `ATTR` — attributes of a component (Designator, Value, etc.)
- `FONT` — glyph data (very large, can be skipped)

### PCB COMPONENT record (in `Inverted_MAML_IMC.epru`)

```json
{"type":"COMPONENT","id":"..."}||{"x":950,"y":5260,"angle":0,
  "attrs":{"Reuse Block":"matrix8","Group ID":"$1I25","Channel ID":"$1I2_$2I3"},
  "locked":true}|
```

Key fields:
- `x`, `y` — PCB position in **mils** (1 mil = 0.0254mm)
- `Reuse Block` — which matrix this belongs to (`matrix3`, `matrix8`, `matrix33`)
- `Channel ID` — `$1Ixxx_$2Iyyy` where `$1Ixxx` is the **block prefix** (identifies the cell in the grid)
- `locked` — `true` if already placed and fixed

---

## Grid Coordinate System (PCB)

EasyEDA PCB uses mils as units. Y increases **downward** on the PCB canvas.

### Already Placed & Locked Blocks (Row 1)

These are the reference blocks — **do not move them**.

| Matrix    | Grid Cell | Prefix   | PCB X (mil) | PCB Y (mil) |
|-----------|-----------|----------|-------------|-------------|
| matrix3   | [Row1,Col1] | `$1I2`  | 991.00      | 5547.00     |
| matrix3   | [Row1,Col2] | `$1I8`  | 1499.70     | 5547.00     |
| matrix8   | [Row1,Col1] | `$1I2`  | 989.50      | 5292.00     |
| matrix8   | [Row1,Col2] | `$1I8`  | 1498.20     | 5292.00     |
| matrix33  | [Row1,Col1] | `$1I263`| 1242.50     | 5558.75     |
| matrix33  | [Row1,Col2] | `$1I269`| 1751.20     | 5558.75     |

### Grid Spacings (derived from locked blocks)

| Axis | Step        | Value      |
|------|-------------|------------|
| X    | Column step | **508.70 mil** (≈ 12.921 mm) |
| Y    | Row step    | **520.00 mil** (= 13.208 mm) — **provided by user** |

Row 2 PCB Y positions:
- matrix3:  `5547.00 + 520 = 6067.00`
- matrix8:  `5292.00 + 520 = 5812.00`
- matrix33: `5558.75 + 520 = 6078.75`

---

## Block Hierarchy Mapping

The `Channel ID` prefix (e.g. `$1I2`) identifies a **block cell** in the matrix.
The suffix (e.g. `$2I3`) identifies an **individual sub-component** within that cell.

### How to derive grid [Row, Col] from PCB X position

Using the Col1 anchor X and the 508.70 mil step:

```
Col = round((x - anchor_X) / 508.70) + 1
Row = round((y - anchor_Y) / 520.00) + 1
```

Per matrix:
- **matrix3**: anchor Col1 = X:991.00, Y:5547.00
- **matrix8**: anchor Col1 = X:989.50, Y:5292.00
- **matrix33**: anchor Col1 = X:1242.50, Y:5558.75

---

## Placement Rules

1. **Only place COMPONENT records** — skip all wire/track/via/pad/polygon records.
2. Block [1,1] and [1,2] for all three matrices are **locked** — do NOT modify them.
3. Row 1, Columns 3–6 still need to be placed (same Y as Col1/Col2, X offset by steps).
4. Row 2–8 (matrix3), Row 2–7 (matrix8), Row 2–6 (matrix33) need placing.
5. Row 8 of matrix3 uses **REF_CELL_2X_2T1C** (different cell type) — skip entirely, handle manually.
6. matrix33 has NO blocks at rows 7 & 8 → leave those positions empty.
7. matrix8 has NO block at row 8 → leave that position empty.
8. All blocks in the same row share the same Y coordinate.
9. All blocks use the same rotation/angle as the locked reference blocks.

---

## Prefix → Grid Cell Mapping (still to be determined)

The schematic `.epru` files (matx3, matx8, matx33) contain the same `Channel ID`
prefixes with their schematic X,Y positions. These schematic positions are in
schematic-space units and are **not** directly usable as PCB coordinates.

The prefixes found at positive Y (near 5292–5558) in the **PCB** file are the
placed Row 1 blocks. All others (negative Y values ~-419 to -34000) are the
unplaced pool of blocks.

### Unplaced block pool per matrix (representative X positions in PCB)

The schematic X-columns appear to map to:
- Schematic X ≈ 540   → Col 1
- Schematic X ≈ 1818  → Col 2
- Schematic X ≈ 3096  → Col 3
- Schematic X ≈ 4374  → Col 4
- Schematic X ≈ 5652  → Col 5
(6th column may not appear in schematic analysis output)

---

## Next Steps for Auto-Placement Script

A Python script needs to:

1. **Parse** `Inverted_MAML_IMC.epru` to find all COMPONENT records with
   `Reuse Block` in `['matrix3', 'matrix8', 'matrix33']` and `locked == false`.

2. **Build the prefix→[row,col] mapping** from the schematic files
   (matx3.epru, matx8.epru, matx33.epru) using the schematic X,Y of each
   component as a hint for column assignment.

3. **Compute target PCB (x, y)** for each prefix:
   ```
   target_x = anchor_col1_x + (col - 1) * 508.70
   target_y = anchor_row1_y + (row - 1) * 520.00
   ```

4. **For each unlocked COMPONENT** in the target prefix:
   - Compute the offset from its current schematic-relative position to the target
   - Apply the offset to all sub-components of the block
   - **Do NOT move** tracks, vias, or pads

5. **Write back** the modified records into a new output `.epru` file
   (never overwrite original).

6. **Load** the new `.epru` into EasyEDA to verify placement.

---

## Schematic File Titles

| File         | DOCHEAD uuid                         | Title                   | Used for                        |
|--------------|--------------------------------------|-------------------------|---------------------------------|
| matx3.epru   | 9f4c252bf7fb83f8                     | REF_CELL_2X_2T1C        | matrix3 **row 8 ONLY** (manual) |
| matx3.epru   | 2780bbe1df4146de9364c606e5fe927a     | MUL_CELL_2X_2T1C        | matrix3 rows 1–7                |
| matx3.epru   | a7de781feffd2eb3                     | (schematic page)        |                                 |
| matx8.epru   | 2780bbe1df4146de9364c606e5fe927a     | MUL_CELL_2X_2T1C        | matrix8 rows 1–7                |
| matx8.epru   | 385c9409d3f231cb                     | (schematic page)        |                                 |
| matx33.epru  | 57717999f3c4ce1b                     | MUL_NO_H_CELL_2X_2T1C  | matrix33 rows 1–6               |
| matx33.epru  | ce0e61a1a155f769                     | (schematic page)        |                                 |

---

## Component Types in the Cell Block

From schematic metadata, each cell block contains:
- `Q?` → DOX3134A (N-Channel MOSFET, SOT-323)
- `R?` → Resistors (0402): 1MΩ, 1kΩ, 100Ω, 3.3kΩ
- `C?` → Capacitors (0402/0201): 100nF, 1nF
- `U?` → MCP6024T-I/SL-MS (Quad Op-Amp, SOP-14)

---

## Key EasyEDA Notes

- EasyEDA PCB unit = **1 mil** (thou)
- 1 mm = 39.3701 mil
- 13.208 mm = exactly **520 mil** (user confirmed Y row step)
- 12.921 mm ≈ **508.70 mil** (X column step, derived from locked blocks)
- EasyEDA `.epru` file = binary bundle of JSON lines, UTF-8
- Backup before any edit: `cp Inverted_MAML_IMC.epru Inverted_MAML_IMC.epru.bak`

---

## Python Analysis Scripts Summary

| Script                  | Purpose                                               |
|-------------------------|-------------------------------------------------------|
| `analyze_blocks.py`     | Print all locked COMPONENT records                    |
| `analyze_prefixes.py`   | Group by prefix, show avg position, locked flag       |
| `analyze_all_prefixes.py`| Sorted by position, cleaner output                  |
| `analyze_grid.py`       | Sort by Y then X to infer row/col structure           |
| `find_locked.py`        | Show only locked block prefixes per matrix            |

---

## Grid Layout & Schematic Block Mapping Source

For a complete reference mapping CBBxx Designators to exact [Row, Col] coordinates under each matrix, see the master layout file:
- [schematic_block_position.txt](schematic_block_position.txt)

This file serves as the core spatial layout source for the auto-placement script.

---

## Template Block Designator Relative Position Map

For the complete component-level detail for all three matrices, see:
- [Template_designator_all_matrices.txt](Template_designator_all_matrices.txt) ← **MASTER TEMPLATE**

This comprehensive template maps ALL components found in the three matrix [1,1] reference blocks:
- **matrix3 [1,1]**: 10 components (R1, R2, C1-C4, Q5-Q6, Q8-Q9)  
- **matrix8 [1,1]**: 9 components
- **matrix33 [1,1]**: 9 components

All components are listed with **absolute PCB coordinates** and **relative X,Y positions** within each cell. 
The relative coordinates are used by the auto-placement script to calculate where components should be placed 
in all other unplaced blocks by applying the appropriate grid offsets.

**Legacy reference** (matrix3 only):
- [Template_designator_relative_xy.txt](Template_designator_relative_xy.txt) — earlier matrix3-only template

---

## Session Notes (2026-06-28)

- Parsed the 9.5 MB PCB EPRU file format successfully.
- Identified locked row-1 blocks for all 3 matrices.
- Measured X step = 508.70 mil from the two locked Col1 and Col2 blocks.
- User confirmed Y row step = 520 mil (13.208 mm).
- Row 1 is fully placed and routed — col 1 and col 2 locked.
- Row 2 offset confirmed: Y += 520 mil from row 1 anchor.
- Row 8 of matrix3 = REF_CELL_2X_2T1C (different cell type) — user will handle manually. Script skips all row-8 blocks of matrix3.
- Placement script should only move COMPONENT records, skip tracks/vias/pads.
- **NEW (Session 2)**: Extracted comprehensive template map from ALL three [1,1] blocks:
  - Found 28 total components across three [1,1] reference blocks
  - matrix3 [1,1]: 10 components (R1, R2, C1-C4, Q5-Q6, Q8-Q9)
  - matrix8 [1,1]: 9 components
  - matrix33 [1,1]: 9 components
  - Created Template_designator_all_matrices.txt with full documentation
  - Ready for auto-placement script implementation using these templates

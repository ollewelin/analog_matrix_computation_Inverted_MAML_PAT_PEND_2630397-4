#!/usr/bin/env python3
"""
Auto-placement Writer for IMC EPRU File - [G_CBB8] Job (BOTTOM LAYER)
Read: Inverted_MAML_IMC.epru
Write: autoplaced_output_IMC_G_CBB8.epru

This version applies:
Template G_CBB8 (first-level hierarchy: designator$CBBx) to BOTTOM LAYER
Blocks: CBB8, CBB10, CBB11, CBB12, CBB13, CBB14 (CBB9 is EXCLUDED - different purpose)
X offset per block: 12.921mm
Layer: BOTTOM (for all placed components)
"""

import json
from pathlib import Path

# Template G_CBB8 definition (first-level hierarchy)
TEMPLATE_G_CBB8 = {
  'C193': (   6.223,    9.836, 270),
  'H1': (  -3.297,    0.426, 90),
  'Q1': (   2.794,    2.286, 0),
  'Q2': (   0.000,    2.286, 180),
  'Q3': (   0.000,    0.000, 180),
  'Q4': (   2.794,    0.000, 0),
  'R10': (   3.429,    4.064, 0),
  'R13': (  -2.921,   12.503, 90),
  'R15': (   7.366,    7.677, 90),
  'R2': (   1.524,    4.064, 0),
  'R3': (  -2.921,    6.153, 270),
  'R4': (   7.366,    9.709, 270),
  'R5': (   6.731,   11.233, 0),
  'R6': (  -3.937,    6.153, 270),
  'R7': (  -4.948,    5.760, 270),
  'R8': (  -2.921,    8.566, 90),
  'R9': (  -0.381,    4.064, 180),
  'U1': (   1.651,    9.328, 270),
}

# Anchor position (from extracted Block CBB8)
ANCHOR_X_MM = 91.054
ANCHOR_Y_MM = 18.497

# Block configuration
BLOCK_SPACING_X_MM = 12.921  # 12.921mm X offset per block

# Blocks to place: CBB8, CBB10-CBB14 (SKIP CBB9)
BLOCKS = [8, 10, 11, 12, 13, 14]

# Layer for all placed components
TARGET_LAYER = 'Bottom'

# Global set to track which components are being placed (for layer assignment)
PLACED_COMP_IDS = set()

def mil_to_mm(mil):
    return mil / 39.3701

def mm_to_mil(mm):
    return mm * 39.3701

def build_placements_map():
    """Build a dictionary of all placements by designator."""
    placements = {}
    
    # ========== Template _CBB8: First-level hierarchy with multiple blocks ==========
    for block_idx, block_num in enumerate(BLOCKS):
        # Calculate X position based on block index
        block_x_offset = block_idx * BLOCK_SPACING_X_MM
        block_y_mm = ANCHOR_Y_MM
        
        for template_des, (rel_x, rel_y, angle) in TEMPLATE_G_CBB8.items():
            # First-level hierarchy: designator$CBBx
            full_designator = f"{template_des}$CBB{block_num}"
            
            expected_x_mm = ANCHOR_X_MM + block_x_offset + rel_x
            expected_y_mm = block_y_mm + rel_y
            
            placement_key = f"{full_designator}_Block{block_num}"
            
            placements[placement_key] = {
                'designator': full_designator,
                'x_mm': expected_x_mm,
                'y_mm': expected_y_mm,
                'angle': int(angle),
                'x_mil': mm_to_mil(expected_x_mm),
                'y_mil': mm_to_mil(expected_y_mm),
                'block': block_num,
                'layer': TARGET_LAYER,
            }
    
    return placements

def process_epru_file_with_designators(input_file, output_file, placements):
    """Two-pass approach: first build designator map, then apply placements."""
    
    print("=" * 120)
    print("IMC EPRU FILE AUTO-PLACEMENT WRITER - [G_CBB8] JOB (BOTTOM LAYER)")
    print("=" * 120)
    print(f"\nPhase 1: Reading designators from source file...")
    
    # Pass 1: Build designator map (component_id -> designator)
    designators = {}
    component_data = {}
    
    try:
        with open(input_file, 'rb') as f:
            for line in f:
                line_str = line.decode('utf-8', errors='replace').strip()
                if '||' not in line_str:
                    continue
                
                parts = line_str.split('||')
                try:
                    meta = json.loads(parts[0])
                    data = json.loads(parts[1].rstrip('|'))
                    
                    if meta.get('type') == 'ATTR' and data.get('key') == 'Designator':
                        parent_id = data.get('parentId')
                        designators[parent_id] = data.get('value', '')
                    
                    if meta.get('type') == 'COMPONENT':
                        comp_id = meta.get('id')
                        # Store the complete data object for later reference
                        component_data[comp_id] = {
                            'x': data.get('x', 0),
                            'y': data.get('y', 0),
                            'angle': data.get('angle', 0),
                            'layer': data.get('layer'),  # Preserve original layer if exists
                            'original_data': data.copy(),  # Keep full original data
                        }
                except Exception:
                    continue
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_file}")
        return 0, 0
    
    print(f"  -> Found {len(designators)} designators")
    print(f"  -> Found {len(component_data)} components")
    
    # Phase 2: Identify which designators match our placements
    print(f"\nPhase 2: Matching template designators...")
    
    # Build a reverse map: designator -> comp_id
    des_to_comp = {}
    for comp_id, des in designators.items():
        des_to_comp[des] = comp_id
    
    # Find matching designators
    matching_designators = {}
    for des in des_to_comp.keys():
        for placement_key, placement in placements.items():
            if placement['designator'] == des:
                if des not in matching_designators:
                    matching_designators[des] = []
                matching_designators[des].append(placement)
    
    print(f"  -> Found {len(matching_designators)} matching designators")
    
    # Phase 3: Apply placements
    print(f"\nPhase 3: Applying placements...")
    
    applied_count = 0
    not_found_list = []
    placed_comp_ids = set()  # Track which components we're placing
    
    for placement_key, placement in placements.items():
        des = placement['designator']
        
        if des in des_to_comp:
            comp_id = des_to_comp[des]
            placed_comp_ids.add(comp_id)  # Mark this component as placed
            if comp_id in component_data:
                component_data[comp_id]['x'] = mm_to_mil(placement['x_mm'])
                component_data[comp_id]['y'] = mm_to_mil(placement['y_mm'])
                component_data[comp_id]['angle'] = placement['angle']
                # Layer will be set to Bottom in write phase (only for placed components)
                applied_count += 1
        else:
            not_found_list.append(placement['designator'])
    
    # Store the set of placed components globally for use in write phase
    global PLACED_COMP_IDS
    PLACED_COMP_IDS = placed_comp_ids
    
    print(f"  -> Applied {applied_count} placements")
    print(f"  -> Target layer: {TARGET_LAYER} (for placed components only)")
    if not_found_list:
        print(f"  -> Not found: {len(set(not_found_list))} unique designators")
    
    # Phase 4: Write output file
    print(f"\nPhase 4: Writing output file...")
    
    written_count = 0
    with open(input_file, 'rb') as in_f, open(output_file, 'wb') as out_f:
        for line in in_f:
            line_str = line.decode('utf-8', errors='replace').strip()
            
            if '||' not in line_str:
                out_f.write(line)
                continue
            
            parts = line_str.split('||')
            try:
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
                
                if meta.get('type') == 'COMPONENT':
                    comp_id = meta.get('id')
                    if comp_id in component_data:
                        # Update coordinates and angle
                        data['x'] = component_data[comp_id]['x']
                        data['y'] = component_data[comp_id]['y']
                        data['angle'] = component_data[comp_id]['angle']
                        # Set layerId to 2 (Bottom) ONLY for placed components
                        # layerId: 1 = Top, 2 = Bottom
                        if comp_id in PLACED_COMP_IDS:
                            data['layerId'] = 2
                        written_count += 1
                
                # Reconstruct line
                out_line = json.dumps(meta) + '||' + json.dumps(data) + '|'
                out_f.write((out_line + '\n').encode('utf-8'))
            except Exception:
                out_f.write(line)
    
    print(f"  -> Output file written: {output_file}")
    
    return applied_count, len(set(not_found_list))

def main():
    print("\n" + "=" * 120)
    print("TEMPLATE CONFIGURATION - [G_CBB8] JOB (BOTTOM LAYER)")
    print("=" * 120)
    print(f"Template: First-level hierarchy (designator$CBBx) - BOTTOM LAYER")
    print(f"  Components per block: {len(TEMPLATE_G_CBB8)}")
    print(f"  Blocks to place: {BLOCKS}")
    print(f"  Total blocks: {len(BLOCKS)}")
    print(f"  Total placements: {len(BLOCKS) * len(TEMPLATE_G_CBB8)}")
    print(f"  Anchor: X={ANCHOR_X_MM:.3f}mm, Y={ANCHOR_Y_MM:.3f}mm")
    print(f"  Block spacing (X): {BLOCK_SPACING_X_MM}mm")
    print(f"  Target layer: {TARGET_LAYER}")
    print(f"  Note: CBB9 is SKIPPED (excluded from placement)")
    
    print(f"\nTemplate Components (relative offsets):")
    for des in sorted(TEMPLATE_G_CBB8.keys()):
        rel_x, rel_y, angle = TEMPLATE_G_CBB8[des]
        print(f"  • {des:<15} X={rel_x:>8.3f}mm Y={rel_y:>8.3f}mm Angle={angle:>4d}°")
    
    print(f"\nBlock Layout (X offsets):")
    for idx, block_num in enumerate(BLOCKS):
        x_offset = idx * BLOCK_SPACING_X_MM
        abs_x = ANCHOR_X_MM + x_offset
        print(f"  CBB{block_num:2d}: X offset = {x_offset:>7.3f}mm, Absolute X = {abs_x:>8.3f}mm")
    
    print("\n" + "=" * 120)
    
    # Build placements map
    placements = build_placements_map()
    
    # Process file
    input_file = 'Inverted_MAML_IMC.epru'
    output_file = 'autoplaced_output_IMC_G_CBB8.epru'
    
    applied, not_found = process_epru_file_with_designators(input_file, output_file, placements)
    
    print("\n" + "=" * 120)
    print("PLACEMENT RESULTS")
    print("=" * 120)
    print(f"Total placements configured: {len(placements)}")
    print(f"Applied: {applied}")
    print(f"Not found in file: {not_found}")
    print(f"Target layer: {TARGET_LAYER}")
    
    if applied > 0:
        print(f"\n✓ Output file created: {output_file}")
        
        # File size
        import os
        file_size = os.path.getsize(output_file)
        print(f"✓ File size: {file_size} bytes")
        print("\n✓ [G_CBB8] Job placement complete (BOTTOM LAYER)!")
    else:
        print(f"\n⚠ No placements were applied. Check if designators match.")
    
    print("=" * 120)

if __name__ == '__main__':
    main()

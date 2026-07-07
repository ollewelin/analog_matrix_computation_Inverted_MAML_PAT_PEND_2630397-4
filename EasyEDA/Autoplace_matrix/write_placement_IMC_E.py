#!/usr/bin/env python3
"""
Auto-placement Writer for IMC EPRU File - [E] Job
Read: Inverted_MAML_IMC.epru
Write: autoplaced_output_IMC_E.epru

This version applies:
Template E (first-level hierarchy: designator$CBBx) across 6 blocks (CBB1-CBB6)
X offset per block: 12.921mm
Y offset: constant (anchor Y = 18.669mm)
"""

import json
from pathlib import Path

# Template E definition (first-level hierarchy)
TEMPLATE_E = {
    'C193': ( -1.784,    8.636, 90),
    'Q1': (   0.000,    2.286, 180),
    'Q2': (   2.782,    2.286, 0),
    'Q3': (   2.782,    0.000, 0),
    'Q4': (   0.000,    0.000, 180),
    'R1': (   7.360,    9.906, 90),
    'R10': ( -0.387,    4.064, 180),
    'R11': (  9.519,    9.017, 90),
    'R12': (  8.503,    9.017, 90),
    'R13': (  1.518,    4.064, 180),
    'R14': (  7.360,   12.319, 90),
    'R2': (  -1.784,    5.969, 270),
    'R3': (   7.360,    5.969, 270),
    'R4': (  -1.784,   10.668, 270),
    'R5': (  -1.784,   12.573, 270),
    'R6': (   8.884,    6.350, 0),
    'R7': (   8.884,    7.493, 0),
    'R8': (   7.360,    7.874, 90),
    'R9': (   3.550,    4.064, 0),
    'U1': (   2.788,    9.144, 270),
}

# Anchor position (from extracted Block CBB1)
ANCHOR_X_MM = 89.922
ANCHOR_Y_MM = 18.669

# Block configuration
BLOCK_SPACING_X_MM = 12.921  # 12.921mm X offset per block

# Blocks to place: CBB1 to CBB6
BLOCKS = list(range(1, 7))  # [1, 2, 3, 4, 5, 6]

def mil_to_mm(mil):
    return mil / 39.3701

def mm_to_mil(mm):
    return mm * 39.3701

def build_placements_map():
    """Build a dictionary of all placements by designator."""
    placements = {}
    
    # ========== Template E: First-level hierarchy with multiple blocks ==========
    for block_num in BLOCKS:
        # Calculate X position based on block number
        block_x_offset = (block_num - 1) * BLOCK_SPACING_X_MM
        block_y_mm = ANCHOR_Y_MM
        
        for template_des, (rel_x, rel_y, angle) in TEMPLATE_E.items():
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
            }
    
    return placements

def process_epru_file_with_designators(input_file, output_file, placements):
    """Two-pass approach: first build designator map, then apply placements."""
    
    print("=" * 120)
    print("IMC EPRU FILE AUTO-PLACEMENT WRITER - [E] JOB")
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
                        component_data[comp_id] = {
                            'x': data.get('x', 0),
                            'y': data.get('y', 0),
                            'angle': data.get('angle', 0),
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
    
    for placement_key, placement in placements.items():
        des = placement['designator']
        
        if des in des_to_comp:
            comp_id = des_to_comp[des]
            if comp_id in component_data:
                component_data[comp_id]['x'] = mm_to_mil(placement['x_mm'])
                component_data[comp_id]['y'] = mm_to_mil(placement['y_mm'])
                component_data[comp_id]['angle'] = placement['angle']
                applied_count += 1
        else:
            not_found_list.append(placement['designator'])
    
    print(f"  -> Applied {applied_count} placements")
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
                        data['x'] = component_data[comp_id]['x']
                        data['y'] = component_data[comp_id]['y']
                        data['angle'] = component_data[comp_id]['angle']
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
    print("TEMPLATE CONFIGURATION - [E] JOB")
    print("=" * 120)
    print(f"Template: First-level hierarchy (designator$CBBx)")
    print(f"  Components per block: {len(TEMPLATE_E)}")
    print(f"  Blocks to place: {BLOCKS}")
    print(f"  Total blocks: {len(BLOCKS)}")
    print(f"  Total placements: {len(BLOCKS) * len(TEMPLATE_E)}")
    print(f"  Anchor: X={ANCHOR_X_MM:.3f}mm, Y={ANCHOR_Y_MM:.3f}mm")
    print(f"  Block spacing (X): {BLOCK_SPACING_X_MM}mm")
    
    print(f"\nTemplate Components (relative offsets):")
    for des in sorted(TEMPLATE_E.keys()):
        rel_x, rel_y, angle = TEMPLATE_E[des]
        print(f"  • {des:<15} X={rel_x:>8.3f}mm Y={rel_y:>8.3f}mm Angle={angle:>3d}°")
    
    print(f"\nBlock Layout:")
    for block_num in BLOCKS:
        x_offset = (block_num - 1) * BLOCK_SPACING_X_MM
        abs_x = ANCHOR_X_MM + x_offset
        print(f"  CBB{block_num}: X offset = {x_offset:>7.3f}mm, Absolute X = {abs_x:>8.3f}mm")
    
    print("\n" + "=" * 120)
    
    # Build placements map
    placements = build_placements_map()
    
    # Process file
    input_file = 'Inverted_MAML_IMC.epru'
    output_file = 'autoplaced_output_IMC_E.epru'
    
    applied, not_found = process_epru_file_with_designators(input_file, output_file, placements)
    
    print("\n" + "=" * 120)
    print("PLACEMENT RESULTS")
    print("=" * 120)
    print(f"Total placements configured: {len(placements)}")
    print(f"Applied: {applied}")
    print(f"Not found in file: {not_found}")
    
    if applied > 0:
        print(f"\n✓ Output file created: {output_file}")
        
        # File size
        import os
        file_size = os.path.getsize(output_file)
        print(f"✓ File size: {file_size} bytes")
        print("\n✓ [E] Job placement complete!")
    else:
        print(f"\n⚠ No placements were applied. Check if designators match.")
    
    print("=" * 120)

if __name__ == '__main__':
    main()

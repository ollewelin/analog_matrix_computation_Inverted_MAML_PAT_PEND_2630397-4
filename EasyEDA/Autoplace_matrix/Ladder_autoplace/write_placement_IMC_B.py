#!/usr/bin/env python3
"""
Auto-placement Writer for IMC EPRU File - Version B
Read: Inverted_MAML_IMC.epru
Write: autoplaced_output_IMC_B.epru

This version applies:
1. Template A (3-level hierarchy) to all 3x8 blocks with X -100mm offset
2. Template B (2-level hierarchy) to CBB17, CBB18, CBB20 with respective Y offsets
"""

import json
from pathlib import Path

# Template A definition (3-level hierarchy with X -100mm offset)
TEMPLATE_A = {
    'R16': (0.000, 0.000, 180),
    'R1': (0.000, 1.143, 180),
    'R15': (-2.794, 1.905, 90),
    'R3': (0.000, 2.413, 180),
    'R14': (-1.651, 3.048, 90),
    'R4': (0.000, 3.683, 180),
    'R13': (-2.794, 4.318, 90),
    'U6': (5.153, 4.363, 270),
    'R5': (0.000, 4.953, 180),
    'R12': (-1.651, 5.588, 90),
    'R6': (0.000, 6.223, 180),
    'R11': (-2.794, 6.858, 90),
    'R7': (0.000, 7.493, 180),
    'R10': (-1.651, 8.001, 90),
    'R8': (0.000, 8.763, 180),
    'R2': (-2.794, 8.890, 90),
    'R9': (0.000, 9.906, 180),
    'C193': (7.874, 9.906, 0),
}

# Template B definition (2-level hierarchy) - will be loaded from IMC_template_B_dict.py
TEMPLATE_B = {}

# Anchor positions
ANCHOR_A_X_MM = 3.683 - 100.0  # Original 3.683 - 100mm offset
ANCHOR_A_Y_MM = 310.769

ANCHOR_B_X_MM = 0.0  # Will be set from extracted template
ANCHOR_B_Y_MM = 0.0

# Block configuration for Template A
Y_OFFSET_A_MM = -12.5
BLOCK_TYPES_A = ['CBB17', 'CBB18', 'CBB20']
BLOCK_NUMBERS_A = list(range(1, 9))

# Block configuration for Template B (2-level hierarchy, no block numbers)
BLOCK_TYPES_B = ['CBB17', 'CBB18', 'CBB20']
Y_OFFSET_B_MM = -12.5 * 8  # -100mm per outer block type

def mil_to_mm(mil):
    return mil / 39.3701

def mm_to_mil(mm):
    return mm * 39.3701

def load_template_b():
    """Load Template B from extracted file."""
    global TEMPLATE_B, ANCHOR_B_X_MM, ANCHOR_B_Y_MM
    
    try:
        # Try to import from Python file
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("imc_template_b", "IMC_template_B_dict.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        TEMPLATE_B = module.TEMPLATE_IMC_B
        ANCHOR_B_X_MM = module.ANCHOR_X_MM
        ANCHOR_B_Y_MM = module.ANCHOR_Y_MM
        
        print(f"✓ Loaded Template B from IMC_template_B_dict.py")
        print(f"  Anchor: X={ANCHOR_B_X_MM:.3f}mm, Y={ANCHOR_B_Y_MM:.3f}mm")
        return True
    except Exception as e:
        print(f"⚠ Could not load Template B: {e}")
        print(f"  Using empty template for Template B")
        return False

def build_placements_map():
    """Build a dictionary of all placements by designator."""
    placements = {}
    
    # ========== Template A: 3-level hierarchy with 3x8 blocks ==========
    block_index = 0
    for block_type in BLOCK_TYPES_A:
        for block_num in BLOCK_NUMBERS_A:
            # Calculate Y position based on continuous block index
            block_y_mm = ANCHOR_A_Y_MM + block_index * Y_OFFSET_A_MM
            
            for template_des, (rel_x, rel_y, angle) in TEMPLATE_A.items():
                full_designator = f"{template_des}${block_type}/CBB{block_num}"
                
                expected_x_mm = ANCHOR_A_X_MM + rel_x
                expected_y_mm = block_y_mm + rel_y
                
                placements[full_designator] = {
                    'x_mm': expected_x_mm,
                    'y_mm': expected_y_mm,
                    'angle': int(angle),
                    'x_mil': mm_to_mil(expected_x_mm),
                    'y_mil': mm_to_mil(expected_y_mm),
                }
            
            block_index += 1
    
    # ========== Template B: 2-level hierarchy for CBB17, CBB18, CBB20 ==========
    if TEMPLATE_B:
        for block_idx, block_type in enumerate(BLOCK_TYPES_B):
            # Y offset for each block type
            block_y_offset = block_idx * Y_OFFSET_B_MM
            block_y_mm = ANCHOR_B_Y_MM + block_y_offset
            
            for template_des, (rel_x, rel_y, angle) in TEMPLATE_B.items():
                # 2-level hierarchy: designator$BlockType (no CBBx suffix)
                full_designator = f"{template_des}${block_type}"
                
                expected_x_mm = ANCHOR_B_X_MM + rel_x
                expected_y_mm = block_y_mm + rel_y
                
                placements[full_designator] = {
                    'x_mm': expected_x_mm,
                    'y_mm': expected_y_mm,
                    'angle': int(angle),
                    'x_mil': mm_to_mil(expected_x_mm),
                    'y_mil': mm_to_mil(expected_y_mm),
                }
    
    return placements

def process_epru_file_with_designators(input_file, output_file, placements):
    """Two-pass approach: first build designator map, then apply placements."""
    
    print("=" * 120)
    print("IMC EPRU FILE AUTO-PLACEMENT WRITER - VERSION B")
    print("=" * 120)
    print(f"\nPhase 1: Reading designators from source file...")
    
    # Pass 1: Build designator map (component_id -> designator)
    designators = {}
    component_data = {}
    
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
    
    print(f"  -> Found {len(designators)} designators")
    print(f"  -> Found {len(component_data)} components")
    
    # Phase 2: Apply placements
    print(f"\nPhase 2: Applying placements...")
    
    applied_count = 0
    not_found_list = []
    
    for designator, placement in placements.items():
        # Find component with this designator
        found_comp_id = None
        for comp_id, des in designators.items():
            if des == designator:
                found_comp_id = comp_id
                break
        
        if found_comp_id and found_comp_id in component_data:
            component_data[found_comp_id]['x'] = mm_to_mil(placement['x_mm'])
            component_data[found_comp_id]['y'] = mm_to_mil(placement['y_mm'])
            component_data[found_comp_id]['angle'] = placement['angle']
            applied_count += 1
        else:
            not_found_list.append(designator)
    
    print(f"  -> Applied {applied_count} placements")
    if not_found_list:
        print(f"  -> Not found: {len(not_found_list)} designators")
    
    # Phase 3: Write output file
    print(f"\nPhase 3: Writing output file...")
    
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
    
    return applied_count, len(not_found_list)

def main():
    # Load Template B
    load_template_b()
    
    # Build placements
    print("\n" + "=" * 120)
    print("PLACEMENT CONFIGURATION")
    print("=" * 120)
    print(f"Template A: 3 types × 8 numbers = 24 blocks")
    print(f"  Components per block: {len(TEMPLATE_A)}")
    print(f"  Total placements: {24 * len(TEMPLATE_A)}")
    print(f"  Anchor (Template A): ({ANCHOR_A_X_MM:.3f}, {ANCHOR_A_Y_MM:.3f})mm")
    print(f"  Y-offset per block: {Y_OFFSET_A_MM}mm")
    print(f"\nTemplate B: 3 types (CBB17, CBB18, CBB20)")
    if TEMPLATE_B:
        print(f"  Components per type: {len(TEMPLATE_B)}")
        print(f"  Total placements: {3 * len(TEMPLATE_B)}")
        print(f"  Anchor (Template B): ({ANCHOR_B_X_MM:.3f}, {ANCHOR_B_Y_MM:.3f})mm")
        print(f"  Y-offset per outer block: {Y_OFFSET_B_MM}mm")
    else:
        print(f"  (Template B not loaded)")
    
    print("\n" + "=" * 120)
    
    placements = build_placements_map()
    
    input_file = 'Inverted_MAML_IMC.epru'
    output_file = 'autoplaced_output_IMC_B.epru'
    
    applied, not_found = process_epru_file_with_designators(input_file, output_file, placements)
    
    print("\n" + "=" * 120)
    print("PLACEMENT RESULTS")
    print("=" * 120)
    print(f"Total placements configured: {len(placements)}")
    print(f"Applied: {applied}")
    print(f"Not found in file: {not_found}")
    
    print(f"\n✓ Output file: {output_file}")
    
    # File size
    import os
    file_size = os.path.getsize(output_file)
    print(f"✓ File size: {file_size} bytes")
    print("=" * 120)

if __name__ == '__main__':
    main()

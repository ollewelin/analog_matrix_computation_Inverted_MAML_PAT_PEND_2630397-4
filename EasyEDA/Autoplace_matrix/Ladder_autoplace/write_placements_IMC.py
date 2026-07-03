#!/usr/bin/env python3
"""
Auto-placement Writer for IMC EPRU File
Read: Inverted_MAML_IMC.epru
Write: autoplaced_output_IMC.epru
Apply all placements with correct X, Y, angle coordinates
"""

import json
from pathlib import Path

# Template definition
TEMPLATE_IMC = {
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

# Anchor position
ANCHOR_X_MM = 3.683
ANCHOR_Y_MM = 310.769

# Block configuration
Y_OFFSET_MM = -12.5
BLOCK_TYPES = ['CBB17', 'CBB18', 'CBB20']
BLOCK_NUMBERS = list(range(1, 9))

def mil_to_mm(mil):
    return mil / 39.3701

def mm_to_mil(mm):
    return mm * 39.3701

def build_placements_map():
    """Build a dictionary of all placements by designator."""
    placements = {}
    
    # Use continuous block index across all block types
    block_index = 0
    for block_type in BLOCK_TYPES:
        for block_num in BLOCK_NUMBERS:
            # Calculate Y position based on continuous block index
            block_y_mm = ANCHOR_Y_MM + block_index * Y_OFFSET_MM
            
            for template_des, (rel_x, rel_y, angle) in TEMPLATE_IMC.items():
                full_designator = f"{template_des}${block_type}/CBB{block_num}"
                
                expected_x_mm = ANCHOR_X_MM + rel_x
                expected_y_mm = block_y_mm + rel_y
                
                placements[full_designator] = {
                    'x_mm': expected_x_mm,
                    'y_mm': expected_y_mm,
                    'angle': int(angle),
                    'x_mil': mm_to_mil(expected_x_mm),
                    'y_mil': mm_to_mil(expected_y_mm),
                }
            
            block_index += 1
    
    return placements

def process_epru_file_with_designators(input_file, output_file, placements):
    """Two-pass approach: first build designator map, then apply placements."""
    
    print("=" * 120)
    print("IMC EPRU FILE AUTO-PLACEMENT WRITER")
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
                
                # Collect designators
                if meta.get('type') == 'ATTR' and data.get('key') == 'Designator':
                    parent_id = data.get('parentId')
                    designators[parent_id] = data.get('value', '')
                
                # Collect component data
                if meta.get('type') == 'COMPONENT':
                    comp_id = meta.get('id')
                    component_data[comp_id] = {
                        'meta': meta,
                        'data': data,
                        'original_line': line_str,
                    }
            except Exception:
                continue
    
    print(f"  -> Found {len(designators)} designators")
    print(f"  -> Found {len(component_data)} components")
    
    print(f"\nPhase 2: Applying placements...")
    
    # Pass 2: Apply placements
    applied_count = 0
    modified_components = set()
    
    for comp_id, comp_info in component_data.items():
        des = designators.get(comp_id, '')
        
        if des in placements:
            placement = placements[des]
            comp_info['data']['x'] = placement['x_mil']
            comp_info['data']['y'] = placement['y_mil']
            comp_info['data']['angle'] = placement['angle']
            
            applied_count += 1
            modified_components.add(des)
    
    print(f"  -> Applied {applied_count} placements")
    
    # Pass 3: Write modified EPRU file
    print(f"\nPhase 3: Writing output file...")
    
    with open(input_file, 'rb') as fin, open(output_file, 'wb') as fout:
        for line in fin:
            line_str = line.decode('utf-8', errors='replace').strip()
            
            if not line_str or '||' not in line_str:
                fout.write(line)
                continue
            
            try:
                parts = line_str.split('||')
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
                
                comp_id = meta.get('id')
                
                # Replace COMPONENT data if modified
                if meta.get('type') == 'COMPONENT' and comp_id in component_data:
                    updated_data = component_data[comp_id]['data']
                    
                    # Reconstruct line
                    meta_str = json.dumps(meta, separators=(',', ':'))
                    data_str = json.dumps(updated_data, separators=(',', ':'))
                    modified_line = f"{meta_str}||{data_str}|"
                    
                    fout.write(modified_line.encode('utf-8'))
                    fout.write(b'\n')
                else:
                    fout.write(line)
            
            except Exception:
                fout.write(line)
                continue
    
    print(f"  -> Output file written: {output_file}")
    
    return applied_count, len(placements) - applied_count

def main():
    input_file = 'Inverted_MAML_IMC.epru'
    output_file = 'autoplaced_output_IMC.epru'
    
    # Build placements map
    placements = build_placements_map()
    
    print(f"\n" + "=" * 120)
    print(f"PLACEMENT CONFIGURATION")
    print("=" * 120)
    print(f"Blocks: {len(BLOCK_TYPES)} types × {len(BLOCK_NUMBERS)} numbers = {len(BLOCK_TYPES) * len(BLOCK_NUMBERS)}")
    print(f"Components per block: {len(TEMPLATE_IMC)}")
    print(f"Total placements: {len(placements)}")
    print(f"Anchor: ({ANCHOR_X_MM:.3f}, {ANCHOR_Y_MM:.3f})mm")
    print(f"Y-offset per block: {Y_OFFSET_MM}mm")
    print("=" * 120)
    
    # Process file
    applied, not_found = process_epru_file_with_designators(input_file, output_file, placements)
    
    print(f"\n" + "=" * 120)
    print(f"PLACEMENT RESULTS")
    print("=" * 120)
    print(f"Total placements: {len(placements)}")
    print(f"Applied: {applied}")
    print(f"Not found in file: {not_found}")
    print(f"\n✓ Output file: {output_file}")
    print("=" * 120)
    
    # Verify output file exists
    if Path(output_file).exists():
        file_size = Path(output_file).stat().st_size
        print(f"✓ File size: {file_size} bytes")
    
    return applied

if __name__ == '__main__':
    applied = main()

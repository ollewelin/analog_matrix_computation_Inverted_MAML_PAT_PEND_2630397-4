#!/usr/bin/env python3
"""
Extract template components from block [1,1] ONLY.
This block contains ALL component placement patterns for a single cell.

Template area boundaries (user-provided for [1,1] block):
- X: 22.606 to 33.274 mm (890.0 to 1310.38 mil)
- Y: 132.588 to 143.891 mm (5225.0 to 5665.0 mil)

This is the MASTER TEMPLATE containing ALL components that should be replicated
to other grid cells using relative offsets.
"""

import json

# Template area boundaries (in mils, converted from user's mm values)
TEMPLATE_X_MIN_MIL = 22.606 * 39.3701  # 890.0
TEMPLATE_X_MAX_MIL = 33.274 * 39.3701  # 1310.38
TEMPLATE_Y_MIN_MIL = 132.588 * 39.3701 # 5225.0
TEMPLATE_Y_MAX_MIL = 143.891 * 39.3701 # 5665.0

print(f"Template boundaries (converted from mm to mil):")
print(f"  X: {TEMPLATE_X_MIN_MIL:.2f} to {TEMPLATE_X_MAX_MIL:.2f} mil")
print(f"  Y: {TEMPLATE_Y_MIN_MIL:.2f} to {TEMPLATE_Y_MAX_MIL:.2f} mil")
print()

def parse_epru_file(filepath):
    """Parse EPRU file line by line, extract designators and components."""
    designators = {}  # id -> designator value
    components = []   # list of {id, x, y, designator, locked, reuse_block, channel_id}
    
    with open(filepath, 'rb') as f:
        for line in f:
            line = line.decode('utf-8', errors='replace').strip()
            if not line or '||' not in line:
                continue
            
            try:
                parts = line.split('||')
                meta_json = json.loads(parts[0])
                data_json = json.loads(parts[1].rstrip('|'))
            except:
                continue
            
            # Pass 1: Collect designators from ATTR records
            if meta_json.get('type') == 'ATTR':
                obj_id = meta_json.get('id')
                parent_id = data_json.get('parentId')
                key = data_json.get('key')
                value = data_json.get('value', '')
                
                if key == 'Designator' and parent_id and value:
                    if parent_id not in designators:
                        designators[parent_id] = value
            
            # Pass 2: Extract COMPONENT records
            elif meta_json.get('type') == 'COMPONENT':
                obj_id = meta_json.get('id')
                x_mil = data_json.get('x', 0)
                y_mil = data_json.get('y', 0)
                attrs = data_json.get('attrs', {})
                locked = data_json.get('locked', False)
                reuse_block = attrs.get('Reuse Block', 'unknown')
                channel_id = attrs.get('Channel ID', '')
                
                designator = designators.get(obj_id, '?')
                
                components.append({
                    'id': obj_id,
                    'x_mil': x_mil,
                    'y_mil': y_mil,
                    'designator': designator,
                    'locked': locked,
                    'reuse_block': reuse_block,
                    'channel_id': channel_id
                })
    
    return components

def main():
    filepath = '/home/olle/Downloads/Inverted_MAML_IMC/Inverted_MAML_IMC.epru'
    
    all_components = parse_epru_file(filepath)
    
    # Filter for components in template area
    template_components = []
    for comp in all_components:
        x = comp['x_mil']
        y = comp['y_mil']
        
        # Check if within template area
        if TEMPLATE_X_MIN_MIL <= x <= TEMPLATE_X_MAX_MIL and \
           TEMPLATE_Y_MIN_MIL <= y <= TEMPLATE_Y_MAX_MIL:
            template_components.append(comp)
    
    # Sort by position (Y then X)
    template_components.sort(key=lambda c: (c['y_mil'], c['x_mil']))
    
    # Calculate boundaries
    if template_components:
        min_x = min(c['x_mil'] for c in template_components)
        max_x = max(c['x_mil'] for c in template_components)
        min_y = min(c['y_mil'] for c in template_components)
        max_y = max(c['y_mil'] for c in template_components)
    else:
        min_x = max_x = min_y = max_y = 0
    
    print(f"Found {len(template_components)} components in template area [1,1] block:")
    print()
    
    # Group by matrix and prefix to verify which [1,1] blocks are in this area
    by_matrix_prefix = {}
    for comp in template_components:
        matrix = comp['reuse_block']
        channel = comp['channel_id']
        prefix = channel.split('_')[0] if '_' in channel else '?'
        key = (matrix, prefix)
        if key not in by_matrix_prefix:
            by_matrix_prefix[key] = []
        by_matrix_prefix[key].append(comp)
    
    print("Components grouped by Matrix and Block Prefix:")
    for (matrix, prefix), comps in sorted(by_matrix_prefix.items()):
        print(f"\n{matrix} - Block {prefix} ({len(comps)} components):")
        print("-" * 120)
        print(f"{'Designator':<12} {'X (mil)':<12} {'Y (mil)':<12} {'X (mm)':<12} {'Y (mm)':<12} {'Rel X (mil)':<14} {'Rel Y (mil)':<14} {'Locked':<8}")
        print("-" * 120)
        
        for comp in comps:
            x_mil = comp['x_mil']
            y_mil = comp['y_mil']
            x_mm = x_mil / 39.3701
            y_mm = y_mil / 39.3701
            rel_x_mil = x_mil - TEMPLATE_X_MIN_MIL
            rel_y_mil = y_mil - TEMPLATE_Y_MIN_MIL
            locked_str = "YES" if comp['locked'] else "no"
            
            print(f"{comp['designator']:<12} {x_mil:<12.2f} {y_mil:<12.2f} {x_mm:<12.3f} {y_mm:<12.3f} {rel_x_mil:<14.2f} {rel_y_mil:<14.2f} {locked_str:<8}")
    
    print()
    print(f"\nTemplate block [1,1] actual component extent:")
    print(f"  X: {min_x:.2f} to {max_x:.2f} mil ({min_x/39.3701:.3f} to {max_x/39.3701:.3f} mm)")
    print(f"  Y: {min_y:.2f} to {max_y:.2f} mil ({min_y/39.3701:.3f} to {max_y/39.3701:.3f} mm)")
    print(f"  Width: {max_x - min_x:.2f} mil ({(max_x - min_x)/39.3701:.3f} mm)")
    print(f"  Height: {max_y - min_y:.2f} mil ({(max_y - min_y)/39.3701:.3f} mm)")
    print()
    print(f"Template area provided bounds:")
    print(f"  X: {TEMPLATE_X_MIN_MIL:.2f} to {TEMPLATE_X_MAX_MIL:.2f} mil")
    print(f"  Y: {TEMPLATE_Y_MIN_MIL:.2f} to {TEMPLATE_Y_MAX_MIL:.2f} mil")

if __name__ == '__main__':
    main()

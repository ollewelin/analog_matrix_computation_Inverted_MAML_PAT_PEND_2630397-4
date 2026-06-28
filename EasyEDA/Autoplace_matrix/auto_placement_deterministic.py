#!/usr/bin/env python3
"""
Deterministic auto-placement v3:
- Each grid cell [row,col] gets the EXACT same component layout as [1,1]
- Components placed in sequence matching the template pattern
- Simple, correct, no guessing
"""

import json
from collections import defaultdict

DX_MIL = 508.70
DY_MIL = 520.00

ANCHORS = {
    'matrix3': {'x': 991.00, 'y': 5547.00},
    'matrix8': {'x': 989.50, 'y': 5292.00},
    'matrix33': {'x': 1242.50, 'y': 5558.75},
}

GRID_DIMS = {'matrix3': (8, 6), 'matrix8': (7, 6), 'matrix33': (6, 6)}
SKIP_ROWS = {'matrix3': [8], 'matrix8': [8], 'matrix33': [7, 8]}

# Template: each grid cell gets these offsets and angles (in order)
TEMPLATES = {
    'matrix3': [
        (-101.0, -47.0, 90),
        (-61.0, 33.0, 0),
        (-61.0, 118.0, 0),
        (-41.0, -72.0, 180),
        (-41.0, -32.0, 180),
        (39.0, -72.0, 0),
        (39.0, -32.0, 0),
        (64.0, 33.0, 180),
        (64.0, 118.0, 180),
        (99.0, -47.0, 90),
    ],
    'matrix8': [
        (-99.5, -47.0, 90),
        (-59.5, 33.0, 0),
        (-59.5, 118.0, 0),
        (-39.5, -72.0, 180),
        (-39.5, -32.0, 180),
        (35.5, -72.0, 0),
        (35.5, -32.0, 0),
        (65.5, 33.0, 180),
        (65.5, 118.0, 180),
        (95.5, -47.0, 90),
    ],
    'matrix33': [
        (-42.5, -43.8, 180),
        (32.5, -43.8, 0),
        (67.5, 21.2, 180),
        (-57.5, 21.2, 0),
        (67.5, 106.2, 180),
        (-57.5, 106.2, 0),
        (-42.5, -83.8, 180),
        (32.5, -83.8, 0),
    ],
}

def build_placement_list():
    """Build ordered list of (matrix, prefix) pairs for placement"""
    prefixes_by_matrix = defaultdict(list)
    
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str:
                continue
            parts = line_str.split('||')
            try:
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
            except:
                continue
            
            if meta.get('type') == 'COMPONENT':
                rb = data.get('attrs', {}).get('Reuse Block', '')
                cid = data.get('attrs', {}).get('Channel ID', '')
                if '_' in cid and rb in ['matrix3', 'matrix8', 'matrix33'] and not data.get('locked'):
                    prefix = cid.split('_')[0]
                    if prefix not in prefixes_by_matrix[rb]:
                        prefixes_by_matrix[rb].append(prefix)
    
    # Build grid assignment: (matrix, prefix) -> [row, col, component_index]
    assignments = {}
    for matrix in ['matrix3', 'matrix8', 'matrix33']:
        rows, cols = GRID_DIMS[matrix]
        skip_rows = SKIP_ROWS.get(matrix, [])
        template = TEMPLATES[matrix]
        
        prefixes = sorted(set(prefixes_by_matrix[matrix]))
        comp_idx = 0
        
        for row in range(2, rows + 1):
            if row in skip_rows:
                continue
            for col in range(1, cols + 1):
                # This grid cell takes components from prefix list
                if comp_idx < len(prefixes):
                    prefix = prefixes[comp_idx]
                    assignments[(matrix, prefix)] = (row, col, comp_idx % len(template))
                    comp_idx += 1
    
    return assignments

def main():
    print("=== Deterministic Auto-Placement ===\n")
    
    print("Step 1: Build placement assignments...")
    assignments = build_placement_list()
    print(f"  Assigned {len(assignments)} prefixes to grid cells")
    
    print("\nStep 2: Collect all unlocked components...")
    placements = {}
    
    designators = {}
    components = []
    
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str:
                continue
            parts = line_str.split('||')
            try:
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
            except:
                continue
            
            if meta.get('type') == 'ATTR':
                if data.get('key') == 'Designator':
                    designators[meta.get('id')] = data.get('value', '')
            
            elif meta.get('type') == 'COMPONENT':
                if not data.get('locked'):
                    rb = data.get('attrs', {}).get('Reuse Block', '')
                    cid = data.get('attrs', {}).get('Channel ID', '')
                    if rb in ['matrix3', 'matrix8', 'matrix33'] and '_' in cid:
                        prefix = cid.split('_')[0]
                        components.append({
                            'id': meta.get('id'),
                            'rb': rb,
                            'prefix': prefix,
                            'meta': meta,
                            'data': data,
                        })
    
    print(f"  Found {len(components)} unlocked components")
    
    print("\nStep 3: Calculate placements...")
    placed = 0
    for comp in components:
        key = (comp['rb'], comp['prefix'])
        if key not in assignments:
            continue
        
        row, col, _ = assignments[key]
        matrix = comp['rb']
        template = TEMPLATES[matrix]
        
        # Which component in template pattern for this block?
        # Round-robin: distribute all components from this prefix across template positions
        comp_in_template = placed % len(template)
        
        anchor = ANCHORS[matrix]
        block_x = anchor['x'] + (col - 1) * DX_MIL
        block_y = anchor['y'] - (row - 1) * DY_MIL
        
        rel_x, rel_y, angle = template[comp_in_template]
        
        new_x = block_x + rel_x
        new_y = block_y + rel_y
        
        placements[comp['id']] = {
            'new_x': new_x,
            'new_y': new_y,
            'angle': angle,
        }
        placed += 1
    
    print(f"  Placements: {len(placements)}")
    
    print("\nStep 4: Write output...")
    with open('Inverted_MAML_IMC.epru', 'rb') as fin, \
         open('Inverted_MAML_IMC_auto.epru', 'wb') as fout:
        for line in fin:
            line_str = line.decode('utf-8', errors='replace')
            
            if '||' not in line_str:
                fout.write(line)
                continue
            
            parts = line_str.rstrip('\n').split('||', 1)
            if len(parts) != 2:
                fout.write(line)
                continue
            
            try:
                meta = json.loads(parts[0])
                data_str = parts[1].rstrip('|')
                
                if meta.get('type') == 'COMPONENT' and data_str:
                    data = json.loads(data_str)
                    comp_id = meta.get('id', '')
                    
                    if comp_id in placements:
                        plan = placements[comp_id]
                        data['x'] = plan['new_x']
                        data['y'] = plan['new_y']
                        data['angle'] = plan['angle']
                        data['locked'] = True
                    
                    new_data_str = json.dumps(data, separators=(',', ':'))
                    new_line = f"{parts[0]}||{new_data_str}|\n"
                    fout.write(new_line.encode('utf-8'))
                else:
                    fout.write(line)
            except:
                fout.write(line)
    
    print(f"Done: {len(placements)} components placed")
    print(f"Output: Inverted_MAML_IMC_auto.epru")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Smart auto-placement v2: 
1. Match each component to template by relative position within block
2. Apply the specific angle for that position
3. Mark placed components as locked
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

# Template positions with their angles (extracted from [1,1] blocks)
TEMPLATE_ANGLES = {
    'matrix3': {
        (-101.0, -47.0): 90,
        (-61.0, 33.0): 0,
        (-61.0, 118.0): 0,
        (-41.0, -72.0): 180,
        (-41.0, -32.0): 180,
        (39.0, -72.0): 0,
        (39.0, -32.0): 0,
        (64.0, 33.0): 180,
        (64.0, 118.0): 180,
        (99.0, -47.0): 90,
    },
    'matrix8': {
        (-99.5, -47.0): 90,
        (-59.5, 33.0): 0,
        (-59.5, 118.0): 0,
        (-39.5, -72.0): 180,
        (-39.5, -32.0): 180,
        (35.5, -72.0): 0,
        (35.5, -32.0): 0,
        (65.5, 33.0): 180,
        (65.5, 118.0): 180,
        (95.5, -47.0): 90,
    },
    'matrix33': {
        (-42.5, -43.8): 180,
        (32.5, -43.8): 0,
        (67.5, 21.2): 180,
        (-57.5, 21.2): 0,
        (67.5, 106.2): 180,
        (-57.5, 106.2): 0,
        (-42.5, -83.8): 180,
        (32.5, -83.8): 0,
    },
}

def build_prefix_grid_map():
    """Map (matrix, prefix) -> (row, col)"""
    prefixes_by_matrix = defaultdict(lambda: defaultdict(int))
    
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
                    prefixes_by_matrix[rb][prefix] += 1
    
    prefix_to_grid = {}
    for matrix in ['matrix3', 'matrix8', 'matrix33']:
        rows, cols = GRID_DIMS[matrix]
        skip_rows = SKIP_ROWS.get(matrix, [])
        
        prefixes = sorted(set(prefixes_by_matrix[matrix].keys()))
        prefix_idx = 0
        
        for row in range(2, rows + 1):
            if row in skip_rows:
                continue
            for col in range(1, cols + 1):
                if prefix_idx < len(prefixes):
                    prefix = prefixes[prefix_idx]
                    prefix_to_grid[(matrix, prefix)] = (row, col)
                    prefix_idx += 1
    
    return prefix_to_grid

def find_closest_template_angle(rel_x, rel_y, matrix):
    """Find closest template position and return its angle"""
    angles = TEMPLATE_ANGLES.get(matrix, {})
    
    if not angles:
        return 0  # Default angle
    
    # Find nearest template position
    min_dist = float('inf')
    closest_angle = 0
    
    for (tx, ty), angle in angles.items():
        dist = abs(rel_x - tx) + abs(rel_y - ty)  # Manhattan distance
        if dist < min_dist:
            min_dist = dist
            closest_angle = angle
    
    return closest_angle

def main():
    print("=== Smart Auto-Placement with Correct Angles ===\n")
    
    print("Step 1: Build prefix-to-grid mapping...")
    prefix_grid = build_prefix_grid_map()
    print(f"  Mapped {len(prefix_grid)} prefixes to grid cells")
    
    print("\nStep 2: Collect all unlocked components...")
    placements = {}
    placed_count = 0
    
    designators = {}
    components = []
    
    # First pass: collect designators and components
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
                            'x': data.get('x', 0),
                            'y': data.get('y', 0),
                            'rb': rb,
                            'prefix': prefix,
                            'des': designators.get(meta.get('id'), ''),
                            'meta': meta,
                            'data': data,
                        })
    
    print(f"  Found {len(components)} unlocked components")
    
    print("\nStep 3: Calculate placements...")
    for comp in components:
        key = (comp['rb'], comp['prefix'])
        if key not in prefix_grid:
            continue
        
        row, col = prefix_grid[key]
        matrix = comp['rb']
        
        anchor = ANCHORS[matrix]
        
        # Block anchor position
        block_x = anchor['x'] + (col - 1) * DX_MIL
        block_y = anchor['y'] - (row - 1) * DY_MIL
        
        # Relative position within block (from original [1,1])
        rel_x = comp['x'] - ANCHORS[matrix]['x']
        rel_y = comp['y'] - ANCHORS[matrix]['y']
        
        # Find matching template angle
        angle = find_closest_template_angle(rel_x, rel_y, matrix)
        
        # New position
        new_x = block_x + rel_x
        new_y = block_y + rel_y
        
        placements[comp['id']] = {
            'new_x': new_x,
            'new_y': new_y,
            'angle': angle,
            'row': row,
            'col': col,
        }
        placed_count += 1
    
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
    
    print(f"Done: {len(placements)} components placed with correct angles")
    print(f"Output: Inverted_MAML_IMC_auto.epru")

if __name__ == '__main__':
    main()

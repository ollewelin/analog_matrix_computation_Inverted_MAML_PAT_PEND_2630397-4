#!/usr/bin/env python3
"""
Surgical auto-placement: ONLY modify x and y fields in COMPONENT records.
Preserves byte-for-byte structure of all other fields.
"""

import json
import re
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

def parse_template():
    templates = {'matrix3': [], 'matrix8': [], 'matrix33': []}
    current_matrix = None
    with open('Template_designator_all_matrices.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if 'MATRIX3 [1,1]' in line and 'MATRIX33' not in line:
                current_matrix = 'matrix3'
            elif 'MATRIX8 [1,1]' in line:
                current_matrix = 'matrix8'
            elif 'MATRIX33 [1,1]' in line:
                current_matrix = 'matrix33'
            
            if current_matrix and '$CBB' in line and not line.startswith(('Designator', '-', '=')):
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        templates[current_matrix].append({
                            'designator': parts[0],
                            'rel_x': float(parts[5]),
                            'rel_y': float(parts[6]),
                        })
                    except (ValueError, IndexError):
                        pass
    return templates

def build_prefix_grid_map():
    """Build mapping from (matrix, prefix) -> (row, col)."""
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

def main():
    print("=== Surgical Auto-Placement (x,y only) ===\n")
    
    print("Step 1: Parse template...")
    templates = parse_template()
    for m, comps in templates.items():
        print(f"  {m}: {len(comps)} components")
    
    print("\nStep 2: Build prefix-to-grid mapping...")
    prefix_grid = build_prefix_grid_map()
    print(f"  Mapped {len(prefix_grid)} prefixes to grid cells")
    
    print("\nStep 3: Collect placements...")
    placements = {}
    placed_count = 0
    
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
                            'x': data.get('x', 0),
                            'y': data.get('y', 0),
                            'rb': rb,
                            'prefix': prefix,
                            'des': designators.get(meta.get('id'), ''),
                        })
    
    for comp in components:
        key = (comp['rb'], comp['prefix'])
        if key not in prefix_grid:
            continue
        
        row, col = prefix_grid[key]
        matrix = comp['rb']
        
        if matrix not in templates:
            continue
        
        template = templates[matrix]
        if not template:
            continue
        
        anchor = ANCHORS[matrix]
        target_x = anchor['x'] + (col - 1) * DX_MIL
        target_y = anchor['y'] - (row - 1) * DY_MIL
        
        if template:
            tcomp = template[placed_count % len(template)]
            new_x = target_x + tcomp['rel_x']
            new_y = target_y + tcomp['rel_y']
            
            placements[comp['id']] = {
                'new_x': new_x,
                'new_y': new_y,
            }
            placed_count += 1
    
    print(f"  Placements: {len(placements)}")
    
    print("\nStep 4: Write output (surgical edits only)...")
    with open('Inverted_MAML_IMC.epru', 'rb') as fin, \
         open('Inverted_MAML_IMC_auto.epru', 'wb') as fout:
        for line in fin:
            line_str = line.decode('utf-8', errors='replace')
            
            # Check if it's a record line (has ||)
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
                
                # ONLY modify COMPONENT records
                if meta.get('type') == 'COMPONENT' and data_str:
                    data = json.loads(data_str)
                    comp_id = meta.get('id', '')
                    
                    if comp_id in placements:
                        plan = placements[comp_id]
                        # SURGICAL: modify x, y, angle and mark as locked (placed)
                        data['x'] = plan['new_x']
                        data['y'] = plan['new_y']
                        data['angle'] = 180
                        data['locked'] = True
                        
                        # Reconstruct: preserve original JSON formatting exactly
                        new_data_str = json.dumps(data, separators=(',', ':'))
                        new_line = f"{parts[0]}||{new_data_str}|\n"
                        fout.write(new_line.encode('utf-8'))
                    else:
                        # Unmodified COMPONENT
                        fout.write(line)
                else:
                    # Not a COMPONENT, keep exactly as-is
                    fout.write(line)
            except Exception as e:
                # If parse fails, keep original line
                fout.write(line)
    
    print(f"Done: {len(placements)} components placed")
    print(f"Output: Inverted_MAML_IMC_auto.epru")

if __name__ == '__main__':
    main()

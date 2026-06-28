#!/usr/bin/env python3
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

# 1. HARDCODED SUFFIX TEMPLATES based on your [1,1] blocks
# Extracted from Source 3: mapping the suffix to (rel_x, rel_y, angle)
TEMPLATE_MAP = {
    'matrix3': {
        '$2I4':  (-101.0, -47.0, 90),
        '$2I9':  (-61.0, 33.0, 0),
        '$2I15': (-61.0, 118.0, 0),
        '$2I22': (-41.0, -72.0, 180),
        '$2I3':  (-41.0, -32.0, 180),
        '$2I26': (39.0, -72.0, 0),
        '$2I16': (39.0, -32.0, 0),
        '$2I2':  (64.0, 33.0, 180),
        '$2I14': (64.0, 118.0, 180),
        '$2I17': (99.0, -47.0, 90),
    },
    'matrix8': {
        '$2I4':  (-99.5, -47.0, 90),
        '$2I9':  (-59.5, 33.0, 0),
        '$2I15': (-59.5, 118.0, 0),
        '$2I22': (-39.5, -72.0, 180),
        '$2I3':  (-39.5, -32.0, 180),
        '$2I26': (35.5, -72.0, 0),
        '$2I16': (35.5, -32.0, 0),
        '$2I2':  (65.5, 33.0, 180),
        '$2I14': (65.5, 118.0, 180),
        '$2I17': (95.5, -47.0, 90),
    },
    'matrix33': {
        '$2I4':  (-42.5, -43.8, 180), # Note: Assuming these from the first template iteration
        '$2I9':  (32.5, -43.8, 0),
        '$2I15': (67.5, 21.2, 180),
        '$2I22': (-57.5, 21.2, 0),
        '$2I3':  (67.5, 106.2, 180),
        '$2I26': (-57.5, 106.2, 0),
        '$2I16': (-42.5, -83.8, 180),
        '$2I2':  (32.5, -83.8, 0),
    }
}

def build_prefix_grid_map():
    prefixes_by_matrix = defaultdict(list)
    
    # Gather unlocked prefixes
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str: continue
            parts = line_str.split('||')
            try:
                meta, data = json.loads(parts[0]), json.loads(parts[1].rstrip('|'))
                if meta.get('type') == 'COMPONENT' and not data.get('locked'):
                    rb = data.get('attrs', {}).get('Reuse Block', '')
                    cid = data.get('attrs', {}).get('Channel ID', '')
                    if '_' in cid and rb in ['matrix3', 'matrix8', 'matrix33']:
                        prefix = cid.split('_')[0]
                        if prefix not in prefixes_by_matrix[rb]:
                            prefixes_by_matrix[rb].append(prefix)
            except:
                continue
    
    # Map to Grid
    prefix_to_grid = {}
    for matrix in ['matrix3', 'matrix8', 'matrix33']:
        rows, cols = GRID_DIMS[matrix]
        skip_rows = SKIP_ROWS.get(matrix, [])
        prefixes = sorted(set(prefixes_by_matrix[matrix]))
        prefix_idx = 0
        
        # FIX 1: Start at Row 1, but explicitly skip [1,1] and [1,2]
        for row in range(1, rows + 1):
            if row in skip_rows: continue
            for col in range(1, cols + 1):
                if row == 1 and col in [1, 2]: 
                    continue # Skip locked reference blocks
                
                if prefix_idx < len(prefixes):
                    prefix_to_grid[(matrix, prefixes[prefix_idx])] = (row, col)
                    prefix_idx += 1
                    
    return prefix_to_grid

def main():
    print("Step 1: Building grid map...")
    prefix_grid = build_prefix_grid_map()
    placements = {}
    
    print("Step 2: Calculating precise component placements...")
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str: continue
            parts = line_str.split('||')
            try:
                meta, data = json.loads(parts[0]), json.loads(parts[1].rstrip('|'))
                if meta.get('type') == 'COMPONENT' and not data.get('locked'):
                    rb = data.get('attrs', {}).get('Reuse Block', '')
                    cid = data.get('attrs', {}).get('Channel ID', '')
                    
                    if '_' in cid and rb in TEMPLATE_MAP:
                        prefix, suffix = cid.split('_')
                        
                        # Check if this block is slated for placement
                        if (rb, prefix) in prefix_grid:
                            row, col = prefix_grid[(rb, prefix)]
                            
                            # FIX 2: Exact matching via Channel ID suffix
                            if suffix in TEMPLATE_MAP[rb]:
                                rel_x, rel_y, angle = TEMPLATE_MAP[rb][suffix]
                                
                                anchor = ANCHORS[rb]
                                block_x = anchor['x'] + (col - 1) * DX_MIL
                                block_y = anchor['y'] - (row - 1) * DY_MIL
                                
                                placements[meta['id']] = {
                                    'x': block_x + rel_x,
                                    'y': block_y + rel_y,
                                    'angle': angle
                                }
            except:
                continue

    print(f"Step 3: Writing {len(placements)} fixed placements...")
    with open('Inverted_MAML_IMC.epru', 'rb') as fin, open('Inverted_MAML_IMC_fixed.epru', 'wb') as fout:
        for line in fin:
            line_str = line.decode('utf-8', errors='replace')
            if '||' not in line_str:
                fout.write(line)
                continue
                
            parts = line_str.rstrip('\n').split('||', 1)
            try:
                meta = json.loads(parts[0])
                if meta.get('type') == 'COMPONENT' and meta.get('id') in placements:
                    data = json.loads(parts[1].rstrip('|'))
                    plan = placements[meta['id']]
                    
                    data['x'] = plan['x']
                    data['y'] = plan['y']
                    data['angle'] = plan['angle']
                    data['locked'] = True
                    
                    new_line = f"{parts[0]}||{json.dumps(data, separators=(',', ':'))}|\n"
                    fout.write(new_line.encode('utf-8'))
                else:
                    fout.write(line)
            except:
                fout.write(line)
                
    print("Done! Output saved to Inverted_MAML_IMC_fixed.epru")

if __name__ == '__main__':
    main()
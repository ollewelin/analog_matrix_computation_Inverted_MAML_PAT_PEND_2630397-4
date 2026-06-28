#!/usr/bin/env python3
"""
Designator-Based Auto-Placement Script
--------------------------------------
This script bypasses internal prefix guessing and strictly relies on the 
actual schematic Designator (e.g., 'Q6$CBB19/CBB1').
It maps 'Q6' to specific coordinates and 'CBB1' to a specific grid cell.
"""

import json

# Grid configuration
DX_MIL = 508.70
DY_MIL = 520.00

ANCHORS = {
    'matrix3': {'x': 991.00, 'y': 5547.00},
    'matrix8': {'x': 989.50, 'y': 5292.00},
    'matrix33': {'x': 1242.50, 'y': 5558.75},
}

TEMPLATE_MAP = {
    'matrix3': {
        'C2':  (-101.0, -47.0, 90),       
        'Q6':  (-61.0, 33.0, 0),          
        'Q9': (-61.0, 118.0, 0),         
        'R1': (-41.0, -72.0, 180),       
        'C1':  (-41.0, -32.0, 180),       
        'R2': (39.0, -72.0, 0),          
        'C3': (39.0, -32.0, 0),          
        'Q5':  (64.0, 33.0, 180),         
        'Q8': (64.0, 118.0, 180),        
        'C4': (99.0, -47.0, 90),         
    },
    'matrix8': {
        'C2':  (-99.5, -47.0, 90),        
        'Q6':  (-59.5, 33.0, 0),          
        'Q9': (-59.5, 118.0, 0),         
        'R1': (-39.5, -72.0, 180),       
        'C1':  (-39.5, -32.0, 180),       
        'R2': (35.5, -72.0, 0),          
        'C3': (35.5, -32.0, 0),          
        'Q5':  (65.5, 33.0, 180),         
        'Q8': (65.5, 118.0, 180),        
        'C4': (95.5, -47.0, 90),         
    },
    'matrix33': {
        'C1':   (-42.5, -43.8, 180),      
        'C3':  (32.5, -43.8, 0),         
        'Q5':   (67.5, 21.2, 180),        
        'Q6':   (-57.5, 21.2, 0),         
        'Q8':  (67.5, 106.2, 180),       
        'Q9':  (-57.5, 106.2, 0),        
        'R1':  (-42.5, -83.8, 180),      
        'R2':  (32.5, -83.8, 0),         
    }
}


# ==============================================================================
# 2. GRID MAP: Maps CBB Target -> (Row, Column)
# ==============================================================================
GRID_MAP = {
    'matrix33': {
        'CBB1': (1, 1), 'CBB7': (1, 2), 'CBB13': (1, 3), 'CBB19': (1, 4), 'CBB25': (1, 5), 'CBB31': (1, 6),
        'CBB2': (2, 1), 'CBB8': (2, 2), 'CBB14': (2, 3), 'CBB20': (2, 4), 'CBB26': (2, 5), 'CBB32': (2, 6),
        'CBB3': (3, 1), 'CBB9': (3, 2), 'CBB15': (3, 3), 'CBB21': (3, 4), 'CBB27': (3, 5), 'CBB33': (3, 6),
        'CBB4': (4, 1), 'CBB10': (4, 2), 'CBB16': (4, 3), 'CBB22': (4, 4), 'CBB28': (4, 5), 'CBB34': (4, 6),
        'CBB5': (5, 1), 'CBB11': (5, 2), 'CBB17': (5, 3), 'CBB23': (5, 4), 'CBB29': (5, 5), 'CBB35': (5, 6),
        'CBB6': (6, 1), 'CBB12': (6, 2), 'CBB18': (6, 3), 'CBB24': (6, 4), 'CBB30': (6, 5), 'CBB36': (6, 6)
    },
    'matrix8': {
        'CBB1': (1, 1), 'CBB7': (1, 2), 'CBB13': (1, 3), 'CBB19': (1, 4), 'CBB25': (1, 5), 'CBB31': (1, 6),
        'CBB2': (2, 1), 'CBB8': (2, 2), 'CBB14': (2, 3), 'CBB20': (2, 4), 'CBB26': (2, 5), 'CBB32': (2, 6),
        'CBB3': (3, 1), 'CBB9': (3, 2), 'CBB15': (3, 3), 'CBB21': (3, 4), 'CBB27': (3, 5), 'CBB33': (3, 6),
        'CBB4': (4, 1), 'CBB10': (4, 2), 'CBB16': (4, 3), 'CBB22': (4, 4), 'CBB28': (4, 5), 'CBB34': (4, 6),
        'CBB5': (5, 1), 'CBB11': (5, 2), 'CBB17': (5, 3), 'CBB23': (5, 4), 'CBB29': (5, 5), 'CBB35': (5, 6),
        'CBB6': (6, 1), 'CBB12': (6, 2), 'CBB18': (6, 3), 'CBB24': (6, 4), 'CBB30': (6, 5), 'CBB36': (6, 6),
        'CBB37': (7, 1), 'CBB38': (7, 2), 'CBB39': (7, 3), 'CBB40': (7, 4), 'CBB41': (7, 5), 'CBB42': (7, 6)
    },
    'matrix3': {
        'CBB1': (1, 1), 'CBB7': (1, 2), 'CBB13': (1, 3), 'CBB19': (1, 4), 'CBB25': (1, 5), 'CBB31': (1, 6),
        'CBB2': (2, 1), 'CBB8': (2, 2), 'CBB14': (2, 3), 'CBB20': (2, 4), 'CBB26': (2, 5), 'CBB32': (2, 6),
        'CBB3': (3, 1), 'CBB9': (3, 2), 'CBB15': (3, 3), 'CBB21': (3, 4), 'CBB27': (3, 5), 'CBB33': (3, 6),
        'CBB4': (4, 1), 'CBB10': (4, 2), 'CBB16': (4, 3), 'CBB22': (4, 4), 'CBB28': (4, 5), 'CBB34': (4, 6),
        'CBB5': (5, 1), 'CBB11': (5, 2), 'CBB17': (5, 3), 'CBB23': (5, 4), 'CBB29': (5, 5), 'CBB35': (5, 6),
        'CBB6': (6, 1), 'CBB12': (6, 2), 'CBB18': (6, 3), 'CBB24': (6, 4), 'CBB30': (6, 5), 'CBB36': (6, 6),
        'CBB37': (7, 1), 'CBB38': (7, 2), 'CBB39': (7, 3), 'CBB40': (7, 4), 'CBB41': (7, 5), 'CBB42': (7, 6),
        'CBB43': (8, 1), 'CBB44': (8, 2), 'CBB45': (8, 3), 'CBB46': (8, 4), 'CBB47': (8, 5), 'CBB48': (8, 6)
    }
}
def main():
    designators = {}
    placements = {}

    print("Step 1: Extracting Designators from EPRU file...")
    # Pass 1: Link Component IDs to their actual Designator string (e.g., 'Q6$CBB19/CBB1')
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str: 
                continue
            
            parts = line_str.split('||')
            try:
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
                
                # Look for ATTR records that define the Designator
                if meta.get('type') == 'ATTR' and data.get('key') == 'Designator':
                    parent_id = data.get('parentId')
                    designators[parent_id] = data.get('value', '')
            except Exception:
                continue

    print(f"  -> Found {len(designators)} designators.")
    print("Step 2: Calculating precise placements based on naming convention...")
    
    # Pass 2: Calculate target coordinates for unlocked components
    with open('Inverted_MAML_IMC.epru', 'rb') as f:
        for line in f:
            line_str = line.decode('utf-8', errors='replace').strip()
            if '||' not in line_str: 
                continue
            
            parts = line_str.split('||')
            try:
                meta = json.loads(parts[0])
                data = json.loads(parts[1].rstrip('|'))
                
                if meta.get('type') == 'COMPONENT' and not data.get('locked'):
                    comp_id = meta.get('id')
                    matrix = data.get('attrs', {}).get('Reuse Block', '')
                    
                    if matrix in TEMPLATE_MAP and comp_id in designators:
                        full_des = designators[comp_id]  # e.g., 'Q6$CBB19/CBB1'
                        
                        # Validate that the designator follows the expected hierarchical format
                        if '/' in full_des and '$' in full_des:
                            comp_type = full_des.split('$')[0]   # Extracts 'Q6'
                            cbb_target = full_des.split('/')[-1] # Extracts 'CBB1'
                            
                            # Check if we have templates and mapping for these extracted values
                            if comp_type in TEMPLATE_MAP[matrix] and cbb_target in GRID_MAP.get(matrix, {}):
                                rel_x, rel_y, angle = TEMPLATE_MAP[matrix][comp_type]
                                row, col = GRID_MAP[matrix][cbb_target]
                                
                                # Apply formula to find absolute position
                                block_x = ANCHORS[matrix]['x'] + (col - 1) * DX_MIL
                                block_y = ANCHORS[matrix]['y'] - (row - 1) * DY_MIL
                                
                                placements[comp_id] = {
                                    'x': block_x + rel_x,
                                    'y': block_y + rel_y,
                                    'angle': angle
                                }
            except Exception:
                continue

    print(f"  -> Successfully calculated {len(placements)} component positions.")

    if not placements:
        print("WARNING: No placements were calculated. Please check if TEMPLATE_MAP and GRID_MAP are populated.")
        return

    print("Step 3: Writing updated positions to new EPRU file...")
    
    # Pass 3: Write the modifications to a new file
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
                    
                    # Update coordinates, angle, and lock the component
                    data['x'] = plan['x']
                    data['y'] = plan['y']
                    data['angle'] = plan['angle']
                    data['locked'] = True
                    
                    new_line = f"{parts[0]}||{json.dumps(data, separators=(',', ':'))}|\n"
                    fout.write(new_line.encode('utf-8'))
                else:
                    fout.write(line)
            except Exception:
                fout.write(line)
                
    print("Done! Output saved to 'Inverted_MAML_IMC_fixed.epru'.")

if __name__ == '__main__':
    main()
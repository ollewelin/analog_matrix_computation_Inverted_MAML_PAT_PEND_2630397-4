import json
import re
from collections import defaultdict

def parse_epru(filepath):
    # rb_prefix -> list of x, y
    rb_map = defaultdict(lambda: defaultdict(list))
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '||' not in line: continue
            parts = line.split('||')
            try:
                meta = json.loads(parts[0])
                if meta.get('type') != 'COMPONENT': continue
                
                data_part = parts[1].strip()
                if data_part.endswith('|'): data_part = data_part[:-1]
                data = json.loads(data_part)
                
                attrs = data.get('attrs', {})
                rb = attrs.get('Reuse Block')
                cid = attrs.get('Channel ID')
                
                if rb and cid:
                    m = re.match(r'^(\$[0-9]+I[0-9]+)_', cid)
                    if m:
                        prefix = m.group(1)
                    else:
                        prefix = cid
                    
                    rb_map[rb][prefix].append((data['x'], data['y']))
            except:
                pass
    return rb_map

def get_grid(rb_map):
    grid = {}
    for rb, prefixes in rb_map.items():
        if rb not in ['matrix3', 'matrix8', 'matrix33']: continue
        grid[rb] = []
        for p, pos_list in prefixes.items():
            avg_x = sum(p[0] for p in pos_list) / len(pos_list)
            avg_y = sum(p[1] for p in pos_list) / len(pos_list)
            grid[rb].append({'prefix': p, 'x': avg_x, 'y': avg_y})
    return grid

rb_map = parse_epru('Inverted_MAML_IMC.epru')
grid = get_grid(rb_map)

for rb in ['matrix3', 'matrix8', 'matrix33']:
    if rb not in grid: continue
    print(f"\n{rb} prefixes (Sorted by original Y then X):")
    # Using a larger tolerance for Y grouping
    sorted_p = sorted(grid[rb], key=lambda b: (round(b['y']/10), round(b['x']/10)))
    for p in sorted_p:
        print(f"  {p['prefix']} at ({p['x']:.2f}, {p['y']:.2f})")

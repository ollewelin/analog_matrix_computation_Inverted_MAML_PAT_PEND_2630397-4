import json
import re

def parse_epru(filepath):
    components = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split('||')
            if len(parts) < 2:
                continue
            
            try:
                data_part = parts[1].strip()
                if data_part.endswith('|'):
                    data_part = data_part[:-1]
                
                meta = json.loads(parts[0])
                data = json.loads(data_part)
                
                if meta.get('type') == 'COMPONENT':
                    attrs = data.get('attrs', {})
                    comp = {
                        'id': meta.get('id'),
                        'x': data.get('x'),
                        'y': data.get('y'),
                        'reuse_block': attrs.get('Reuse Block'),
                        'channel_id': attrs.get('Channel ID'),
                        'locked': data.get('locked', False)
                    }
                    if comp['reuse_block'] and comp['channel_id']:
                        components.append(comp)
            except:
                pass
    return components

comps = parse_epru('Inverted_MAML_IMC.epru')

blocks = {}
for c in comps:
    cid = c['channel_id']
    m = re.match(r'^(\$[0-9]+I[0-9]+)_(\$[0-9]+I[0-9]+)$', cid)
    if m:
        prefix = m.group(1)
    else:
        prefix = cid
    
    rb = c['reuse_block']
    if rb not in blocks:
        blocks[rb] = {}
    if prefix not in blocks[rb]:
        blocks[rb][prefix] = []
    blocks[rb][prefix].append(c)

for rb in ['matrix3', 'matrix8', 'matrix33']:
    if rb not in blocks: continue
    print(f"\nReuse Block: {rb}")
    res = []
    for p in blocks[rb]:
        xs = [c['x'] for c in blocks[rb][p]]
        ys = [c['y'] for c in blocks[rb][p]]
        avg_x = sum(xs)/len(xs)
        avg_y = sum(ys)/len(ys)
        is_locked = any(c['locked'] for c in blocks[rb][p])
        res.append({'prefix': p, 'x': avg_x, 'y': avg_y, 'locked': is_locked})
    
    # Sort by Y (asc), then X (asc)
    res.sort(key=lambda b: (round(b['y']/10), round(b['x']/10)))
    for b in res:
        print(f"  Prefix: {b['prefix']}, AvgPos: ({b['x']:.2f}, {b['y']:.2f}), Locked: {b['locked']}")

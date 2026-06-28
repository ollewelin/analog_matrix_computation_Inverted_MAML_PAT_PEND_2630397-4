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
    m = re.match(r'^([^$]+)?(\$[0-9]+I[0-9]+)_(\$[0-9]+I[0-9]+)$', cid)
    if m:
        prefix = m.group(2)
        suffix = m.group(3)
    else:
        prefix = cid
        suffix = ""
    
    rb = c['reuse_block']
    if rb not in blocks:
        blocks[rb] = {}
    if prefix not in blocks[rb]:
        blocks[rb][prefix] = []
    blocks[rb][prefix].append(c)

for rb in blocks:
    print(f"Reuse Block: {rb}")
    sorted_prefixes = sorted(blocks[rb].keys())
    for p in sorted_prefixes:
        # Get one representative center
        xs = [c['x'] for c in blocks[rb][p]]
        ys = [c['y'] for c in blocks[rb][p]]
        avg_x = sum(xs)/len(xs)
        avg_y = sum(ys)/len(ys)
        is_locked = any(c['locked'] for c in blocks[rb][p])
        print(f"  Prefix: {p}, Count: {len(blocks[rb][p])}, AvgPos: ({avg_x:.2f}, {avg_y:.2f}), Locked: {is_locked}")

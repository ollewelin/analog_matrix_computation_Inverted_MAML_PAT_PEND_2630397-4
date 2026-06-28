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
                # Remove the trailing | if it exists
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
                        'group_id': attrs.get('Group ID'),
                        'channel_id': attrs.get('Channel ID'),
                        'unique_id': attrs.get('Unique ID'),
                        'locked': data.get('locked', False)
                    }
                    if comp['reuse_block']:
                        components.append(comp)
            except Exception as e:
                # print(f"Error parsing line: {e}")
                pass
    return components

comps = parse_epru('Inverted_MAML_IMC.epru')
for c in comps:
    if c['locked']:
        print(f"LOCKED: {c}")
    # else:
    #    print(c)

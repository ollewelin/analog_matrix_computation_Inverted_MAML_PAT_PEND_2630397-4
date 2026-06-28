import json, re
from collections import defaultdict

def parse_sch_comps(filepath):
    comps = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '||' not in line:
                continue
            parts = line.split('||')
            try:
                meta = json.loads(parts[0])
                if meta.get('type') != 'COMPONENT':
                    continue
                data_part = parts[1].strip().rstrip('|')
                data = json.loads(data_part)
                attrs = data.get('attrs', {})
                cid = attrs.get('Channel ID', '')
                rb = attrs.get('Reuse Block', '')
                if cid:
                    m = re.match(r'^(\$[0-9]+I[0-9]+)', cid)
                    prefix = m.group(1) if m else cid
                    comps.append({
                        'prefix': prefix,
                        'x': data.get('x', 0),
                        'y': data.get('y', 0),
                        'rb': rb,
                        'cid': cid
                    })
            except:
                pass
    return comps

for fname, label in [
    ('matx3/matx3.epru', 'matx3'),
    ('matx8/matx8.epru', 'matx8'),
    ('matx33/matx33.epru', 'matx33')
]:
    comps = parse_sch_comps(fname)
    pfx = defaultdict(list)
    for c in comps:
        pfx[c['prefix']].append((c['x'], c['y']))

    print(f'\n=== {label}: {len(pfx)} unique prefixes ===')
    items = sorted(pfx.items(), key=lambda kv: (
        sum(p[1] for p in kv[1]) / len(kv[1]),
        sum(p[0] for p in kv[1]) / len(kv[1])
    ))
    for k, v in items[:8]:
        ax = sum(p[0] for p in v) / len(v)
        ay = sum(p[1] for p in v) / len(v)
        print(f'  {k}: avg({ax:.0f}, {ay:.0f})')
    print('  ...')
    for k, v in items[-4:]:
        ax = sum(p[0] for p in v) / len(v)
        ay = sum(p[1] for p in v) / len(v)
        print(f'  {k}: avg({ax:.0f}, {ay:.0f})')
    
    # Show distinct X clusters (column positions)
    all_x = [sum(p[0] for p in v)/len(v) for v in pfx.values()]
    all_x_sorted = sorted(set(round(x/100)*100 for x in all_x))
    print(f'  Distinct X clusters (rounded to 100): {all_x_sorted}')
    all_y = [sum(p[1] for p in v)/len(v) for v in pfx.values()]
    all_y_sorted = sorted(set(round(y/100)*100 for y in all_y))
    print(f'  Distinct Y clusters (rounded to 100): {all_y_sorted}')

"""
Explore the structure of pool blocks in the PCB file.
Shows centroids of each prefix, and sub-component count per prefix.
"""
import json, re
from collections import defaultdict

def parse_pcb(filepath):
    blocks = defaultdict(lambda: defaultdict(list))  # rb -> prefix -> [(x,y,locked,cid)]
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
                rb = attrs.get('Reuse Block', '')
                cid = attrs.get('Channel ID', '')
                if not rb or not cid:
                    continue
                if rb not in ('matrix3', 'matrix8', 'matrix33'):
                    continue
                m = re.match(r'^(\$[0-9]+I[0-9]+)', cid)
                prefix = m.group(1) if m else cid
                locked = data.get('locked', False)
                blocks[rb][prefix].append((data['x'], data['y'], locked, cid))
            except:
                pass
    return blocks

blocks = parse_pcb('Inverted_MAML_IMC.epru')

for rb in ['matrix3', 'matrix8', 'matrix33']:
    if rb not in blocks:
        continue
    prefixes = blocks[rb]
    pool = {p: v for p, v in prefixes.items() if not all(c[2] for c in v)}
    locked_pf = {p: v for p, v in prefixes.items() if all(c[2] for c in v)}
    print(f'\n=== {rb}: {len(pool)} pool prefixes, {len(locked_pf)} locked prefixes ===')
    
    # Show component counts
    counts = sorted(set(len(v) for v in pool.values()))
    print(f'  Sub-component counts per prefix: {counts}')
    
    # Group pool prefixes by sub-component count (to separate REF_CELL from MUL_CELL)
    by_count = defaultdict(list)
    for p, v in pool.items():
        cx = sum(c[0] for c in v) / len(v)
        cy = sum(c[1] for c in v) / len(v)
        by_count[len(v)].append((p, cx, cy))
    
    for cnt, items in sorted(by_count.items()):
        print(f'\n  --- {cnt} sub-components per prefix ({len(items)} prefixes) ---')
        # Sort by Y then X
        items.sort(key=lambda x: (round(x[2]/50)*50, round(x[1]/50)*50))
        for p, cx, cy in items[:5]:
            print(f'    {p}: centroid=({cx:.1f}, {cy:.1f})')
        if len(items) > 5:
            print(f'    ... ({len(items)-5} more)')
        # Show Y distribution (cluster into rows?)
        ys = sorted(set(round(cy/50)*50 for _, _, cy in items))
        print(f'  Y clusters (rounded to 50): {ys}')
        xs = sorted(set(round(cx/50)*50 for _, cx, _ in items))
        print(f'  X clusters (rounded to 50): {xs[:10]}{"..." if len(xs)>10 else ""}')

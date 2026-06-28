"""
Build the full grid map: for each matrix, show the (y_cluster, x_cluster) → prefix table.
This reveals exactly which prefix belongs to which [row, col].
"""
import json, re
from collections import defaultdict

def parse_pcb(filepath):
    blocks = defaultdict(lambda: defaultdict(list))
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

def cluster(values, tol=200):
    """Return sorted list of cluster centers."""
    vals = sorted(values)
    clusters = []
    cur = [vals[0]]
    for v in vals[1:]:
        if v - cur[-1] < tol:
            cur.append(v)
        else:
            clusters.append(sum(cur) / len(cur))
            cur = [v]
    clusters.append(sum(cur) / len(cur))
    return clusters

def assign_cluster(value, centers):
    return min(range(len(centers)), key=lambda i: abs(centers[i] - value))

blocks = parse_pcb('Inverted_MAML_IMC.epru')

for rb in ['matrix3', 'matrix8', 'matrix33']:
    if rb not in blocks:
        continue
    prefixes = blocks[rb]
    
    # Separate by sub-component count
    by_cnt = defaultdict(dict)
    for p, v in prefixes.items():
        cx = sum(c[0] for c in v) / len(v)
        cy = sum(c[1] for c in v) / len(v)
        locked = all(c[2] for c in v)
        by_cnt[len(v)][p] = (cx, cy, locked)
    
    # Find the main cell count (most common, >1)
    main_cnt = max((k for k in by_cnt if k > 1), key=lambda k: len(by_cnt[k]))
    main = by_cnt[main_cnt]
    
    print(f'\n{"="*70}')
    print(f'{rb} — {main_cnt} sub-components/cell, {len(main)} prefixes')
    
    # Build Y and X cluster centers
    all_y = [v[1] for v in main.values()]
    all_x = [v[0] for v in main.values()]
    y_centers = cluster(all_y, tol=300)
    x_centers = cluster(all_x, tol=300)
    print(f'Y clusters ({len(y_centers)}): {[f"{c:.0f}" for c in sorted(y_centers)]}')
    print(f'X clusters ({len(x_centers)}): {[f"{c:.0f}" for c in sorted(x_centers)]}')
    
    # Build grid: (y_rank, x_rank) → prefix
    grid = {}
    for p, (cx, cy, locked) in main.items():
        yr = assign_cluster(cy, y_centers)
        xr = assign_cluster(cx, x_centers)
        grid[(yr, xr)] = (p, cx, cy, locked)
    
    # Print as table sorted by Y (row), X (col)
    y_sorted = sorted(range(len(y_centers)), key=lambda i: y_centers[i])
    x_sorted = sorted(range(len(x_centers)), key=lambda i: x_centers[i])
    
    print(f'\nGrid map (row=Y rank ascending, col=X rank ascending):')
    print(f'{"":>8}', end='')
    for xr in x_sorted:
        print(f'  X≈{x_centers[xr]:6.0f}', end='')
    print()
    
    for row_i, yr in enumerate(y_sorted):
        print(f'Y≈{y_centers[yr]:7.0f}', end='')
        for xr in x_sorted:
            cell = grid.get((yr, xr))
            if cell:
                p, cx, cy, locked = cell
                flag = 'L' if locked else ' '
                print(f'  {flag}{p:>10}', end='')
            else:
                print(f'  {"--":>11}', end='')
        print()
    
    # Also show the 1-component prefixes
    if 1 in by_cnt:
        singles = by_cnt[1]
        print(f'\n  1-component prefixes ({len(singles)} total):')
        single_y = sorted(set(round(v[1]/100)*100 for v in singles.values()))
        single_x = sorted(set(round(v[0]/100)*100 for v in singles.values()))
        print(f'  Y≈: {single_y}')
        print(f'  X≈: {single_x[:10]}{"..." if len(single_x)>10 else ""}')
        for p, (cx, cy, locked) in sorted(singles.items())[:4]:
            print(f'    {p}: ({cx:.1f}, {cy:.1f}) lock={locked}')

"""
Extract CBB Designator schematic X,Y positions for all three matrices.
"""
import json
from collections import defaultdict

def get_cbb_positions(fname):
    """Returns dict: CBB_number -> (x, y)"""
    # Pass 1: id -> (x, y)
    id_pos = {}
    with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '||' not in line:
                continue
            parts = line.split('||')
            try:
                meta = json.loads(parts[0])
                data_part = parts[1].strip().rstrip('|')
                data = json.loads(data_part)
                mid = meta.get('id', '')
                if mid:
                    x = data.get('x', data.get('startX'))
                    y = data.get('y', data.get('startY'))
                    id_pos[mid] = (x, y)
            except:
                pass

    # Pass 2: find Designator ATTRs with CBB values, map to parent position
    cbb_pos = {}
    with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '||' not in line:
                continue
            parts = line.split('||')
            try:
                meta = json.loads(parts[0])
                if meta.get('type') != 'ATTR':
                    continue
                data_part = parts[1].strip().rstrip('|')
                data = json.loads(data_part)
                if data.get('key') != 'Designator':
                    continue
                val = str(data.get('value') or '')
                if not val.startswith('CBB'):
                    continue
                pid = data.get('parentId', '')
                pos = id_pos.get(pid)
                if pos and pos[0] is not None:
                    cbb_num = int(val[3:])
                    cbb_pos[cbb_num] = pos
            except:
                pass
    return cbb_pos

results = {}
for fname, label in [
    ('matx3/matx3.epru',   'matrix3'),
    ('matx8/matx8.epru',   'matrix8'),
    ('matx33/matx33.epru', 'matrix33'),
]:
    results[label] = get_cbb_positions(fname)
    nums = sorted(results[label].keys())
    print(f'{label}: {len(nums)} CBB blocks, range CBB{min(nums)}-CBB{max(nums)}')
    for n in nums:
        x, y = results[label][n]
        print(f'  CBB{n:3d}  x={x:6}  y={y:6}')

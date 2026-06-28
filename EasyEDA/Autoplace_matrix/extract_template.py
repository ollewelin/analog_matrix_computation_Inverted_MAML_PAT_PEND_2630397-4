"""
Extract template block designators and relative X,Y positions from PCB file.
Template block: matrix3 [1,1] with prefix $1I2 (locked, reference block)

This maps all component designators and their relative positions within the
block cell, which will be used to calculate offsets for placing all other blocks.
"""
import json
import re
from collections import defaultdict

def mil_to_mm(mils):
    """Convert mils to mm (1 mil = 0.0254 mm)"""
    return mils * 0.0254

def mm_to_mil(mm):
    """Convert mm to mils"""
    return mm / 0.0254

def parse_pcb_template(filepath, rb='matrix3', prefix='$1I2'):
    """
    Extract all COMPONENT records for the locked template block.
    Returns: list of {x_mil, y_mil, designator, channel_id}
    """
    components = []
    designators = {}  # id -> designator_value
    
    # Pass 1: collect designators from ATTR records
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
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
                if data.get('key') == 'Designator':
                    pid = data.get('parentId', '')
                    val = data.get('value') or ''
                    designators[pid] = val
            except:
                pass
    
    # Pass 2: find all COMPONENT records with the target prefix in this matrix
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
                comp_rb = attrs.get('Reuse Block', '')
                cid = attrs.get('Channel ID', '')
                
                if comp_rb != rb:
                    continue
                
                # Match prefix in Channel ID
                m = re.match(r'^(\$[0-9]+I[0-9]+)', cid)
                comp_prefix = m.group(1) if m else cid
                
                if comp_prefix != prefix:
                    continue
                
                cid_full = attrs.get('Channel ID', '')
                x_mil = data.get('x', 0)
                y_mil = data.get('y', 0)
                comp_id = meta.get('id', '')
                des = designators.get(comp_id, '')
                
                components.append({
                    'id': comp_id,
                    'x_mil': x_mil,
                    'y_mil': y_mil,
                    'x_mm': mil_to_mm(x_mil),
                    'y_mm': mil_to_mm(y_mil),
                    'designator': des,
                    'channel_id': cid_full,
                })
            except:
                pass
    
    return components

# Parse template block
comps = parse_pcb_template('Inverted_MAML_IMC.epru', rb='matrix3', prefix='$1I2')

print(f"Found {len(comps)} components in matrix3 [1,1] template block (prefix $1I2)")

# Find block boundaries
if not comps:
    print("ERROR: No components found!")
    exit(1)

xs_mil = [c['x_mil'] for c in comps]
ys_mil = [c['y_mil'] for c in comps]
xs_mm = [c['x_mm'] for c in comps]
ys_mm = [c['y_mm'] for c in comps]

min_x_mil, max_x_mil = min(xs_mil), max(xs_mil)
min_y_mil, max_y_mil = min(ys_mil), max(ys_mil)
min_x_mm, max_x_mm = min(xs_mm), max(xs_mm)
min_y_mm, max_y_mm = min(ys_mm), max(ys_mm)

print(f"\nBlock boundaries (PCB coordinates):")
print(f"  X: {min_x_mil:.2f} to {max_x_mil:.2f} mil ({min_x_mm:.3f} to {max_x_mm:.3f} mm)")
print(f"  Y: {min_y_mil:.2f} to {max_y_mil:.2f} mil ({min_y_mm:.3f} to {max_y_mm:.3f} mm)")
print(f"  Size: {max_x_mil - min_x_mil:.2f} mil × {max_y_mil - min_y_mil:.2f} mil")
print(f"       ({max_x_mm - min_x_mm:.3f} mm × {max_y_mm - min_y_mm:.3f} mm)")

# Calculate relative positions from upper-left corner
# Upper-left = min_x, min_y
rel_comps = []
for c in comps:
    rel_x_mil = c['x_mil'] - min_x_mil
    rel_y_mil = c['y_mil'] - min_y_mil
    rel_x_mm = mil_to_mm(rel_x_mil)
    rel_y_mm = mil_to_mm(rel_y_mil)
    
    rel_comps.append({
        'designator': c['designator'],
        'abs_x_mil': c['x_mil'],
        'abs_y_mil': c['y_mil'],
        'abs_x_mm': c['x_mm'],
        'abs_y_mm': c['y_mm'],
        'rel_x_mil': rel_x_mil,
        'rel_y_mil': rel_y_mil,
        'rel_x_mm': rel_x_mm,
        'rel_y_mm': rel_y_mm,
        'channel_id': c['channel_id'],
    })

# Sort by relative Y (ascending), then X (ascending)
rel_comps.sort(key=lambda c: (round(c['rel_y_mil']/10), round(c['rel_x_mil']/10)))

print(f"\nTemplate designators (sorted by Y then X, relative to upper-left corner):")
print(f"{'Desig':>8}  {'Abs X (mil)':>11}  {'Abs Y (mil)':>11}  {'Abs X (mm)':>10}  {'Abs Y (mm)':>10}  {'Rel X (mil)':>12}  {'Rel Y (mil)':>12}  {'Rel X (mm)':>10}  {'Rel Y (mm)':>10}")
print("=" * 125)
for r in rel_comps:
    print(f"{r['designator']:>8}  {r['abs_x_mil']:>11.2f}  {r['abs_y_mil']:>11.2f}  {r['abs_x_mm']:>10.3f}  {r['abs_y_mm']:>10.3f}  {r['rel_x_mil']:>12.2f}  {r['rel_y_mil']:>12.2f}  {r['rel_x_mm']:>10.3f}  {r['rel_y_mm']:>10.3f}")

#!/usr/bin/env python3
"""
Extract new template E from Inverted_MAML_IMC.epru
Search area: X: 86-101mm, Y: 16-33mm
This template extracts first-level hierarchy components
"""

import json

def mil_to_mm(mil):
    return mil / 39.3701

def extract_all_components(epru_file):
    components = {}
    designators = {}
    
    try:
        with open(epru_file, 'rb') as f:
            for line in f:
                line_str = line.decode('utf-8', errors='replace').strip()
                if '||' not in line_str:
                    continue
                
                parts = line_str.split('||')
                try:
                    meta = json.loads(parts[0])
                    data = json.loads(parts[1].rstrip('|'))
                    
                    if meta.get('type') == 'ATTR' and data.get('key') == 'Designator':
                        parent_id = data.get('parentId')
                        designators[parent_id] = data.get('value', '')
                    
                    if meta.get('type') == 'COMPONENT':
                        comp_id = meta.get('id')
                        x_mil = data.get('x', 0)
                        y_mil = data.get('y', 0)
                        
                        components[comp_id] = {
                            'x_mil': x_mil,
                            'y_mil': y_mil,
                            'x_mm': mil_to_mm(x_mil),
                            'y_mm': mil_to_mm(y_mil),
                            'angle': data.get('angle', 0),
                            'locked': data.get('locked', False),
                        }
                except Exception:
                    continue
    except FileNotFoundError:
        print(f"ERROR: File not found: {epru_file}")
        return {}, {}
    
    return components, designators

def search_area(components, designators, x_mm_min, x_mm_max, y_mm_min, y_mm_max):
    found = []
    for comp_id, comp in components.items():
        x_mm = comp['x_mm']
        y_mm = comp['y_mm']
        if (x_mm_min <= x_mm <= x_mm_max) and (y_mm_min <= y_mm <= y_mm_max):
            found.append({
                'comp_id': comp_id,
                'designator': designators.get(comp_id, 'UNKNOWN'),
                'x_mil': comp['x_mil'],
                'y_mil': comp['y_mil'],
                'x_mm': comp['x_mm'],
                'y_mm': comp['y_mm'],
                'angle': comp['angle'],
                'locked': comp['locked'],
            })
    return sorted(found, key=lambda c: (c['y_mm'], c['x_mm']))

def main():
    print("=" * 120)
    print("EXTRACT TEMPLATE E FROM Inverted_MAML_IMC.epru")
    print("=" * 120)
    
    epru_file = 'Inverted_MAML_IMC.epru'
    
    print(f"\nParsing: {epru_file}")
    components, designators = extract_all_components(epru_file)
    print(f"  -> Found {len(components)} total components")
    print(f"  -> Found {len(designators)} designators")
    
    # Search area: X 86-101mm, Y 16-33mm (from image coordinates)
    x_min, x_max, y_min, y_max = 86, 101, 16, 33
    
    print(f"\n" + "=" * 120)
    print(f"SEARCHING: X {x_min}-{x_max}mm, Y {y_min}-{y_max}mm")
    print("=" * 120)
    
    found = search_area(components, designators, x_min, x_max, y_min, y_max)
    
    print(f"\n✓ Found {len(found)} components\n")
    
    if found:
        print(f"{'Designator':<35} {'X (mm)':<12} {'Y (mm)':<12} {'Angle':<8} {'Locked':<8}")
        print("-" * 100)
        
        for comp in found:
            locked_str = "✓" if comp['locked'] else " "
            print(f"{comp['designator']:<35} {comp['x_mm']:>11.2f} {comp['y_mm']:>11.2f} {comp['angle']:>7.0f}° {locked_str:<8}")
    
    # Template extraction
    if not found:
        print("\n⚠ No components found in search area!")
        return
    
    print("\n" + "=" * 120)
    print("TEMPLATE EXTRACTION")
    print("=" * 120)
    
    # Use first component as anchor
    anchor_comp = found[0]
    anchor_x_mm_orig = anchor_comp['x_mm']
    anchor_y_mm = anchor_comp['y_mm']
    
    print(f"\nAnchor point: {anchor_comp['designator']} at X={anchor_x_mm_orig:.3f}mm, Y={anchor_y_mm:.3f}mm")
    
    # Build template dictionary - extract base designator (first level only)
    template_dict = {}
    for comp in found:
        designator_raw = comp['designator']
        
        # Extract base designator (before any $ or /)
        if '$' in designator_raw:
            base_des = designator_raw.split('$')[0]
        else:
            base_des = designator_raw
        
        # Calculate relative positions
        rel_x = comp['x_mm'] - anchor_x_mm_orig
        rel_y = comp['y_mm'] - anchor_y_mm
        angle = comp['angle']
        
        template_dict[base_des] = (rel_x, rel_y, angle)
    
    # Save template
    template_file = 'IMC_template_E_x_y_rot.txt'
    with open(template_file, 'w') as f:
        f.write("# Template E - First-level hierarchy\n")
        f.write(f"# Anchor: {anchor_comp['designator']} at X={anchor_x_mm_orig:.3f}mm, Y={anchor_y_mm:.3f}mm\n\n")
        for des, (rel_x, rel_y, angle) in sorted(template_dict.items()):
            f.write(f"{des:<30} X={rel_x:>8.3f}mm Y={rel_y:>8.3f}mm Angle={angle:>3.0f}°\n")
    
    print(f"\n✓ Template saved to: {template_file}")
    
    # Save as Python dictionary
    dict_file = 'IMC_template_E_dict.py'
    with open(dict_file, 'w') as f:
        f.write("# IMC Template E Dictionary (first-level hierarchy)\n")
        f.write(f"# Anchor: {anchor_comp['designator']} at X={anchor_x_mm_orig:.3f}mm, Y={anchor_y_mm:.3f}mm\n\n")
        f.write("TEMPLATE_IMC_E = {\n")
        for des, (rel_x, rel_y, angle) in sorted(template_dict.items()):
            f.write(f"    '{des}': ({rel_x:>8.3f}, {rel_y:>8.3f}, {int(angle)}),\n")
        f.write("}\n\n")
        f.write(f"# Anchor configuration\n")
        f.write(f"ANCHOR_X_MM = {anchor_x_mm_orig:.3f}\n")
        f.write(f"ANCHOR_Y_MM = {anchor_y_mm:.3f}\n")
    
    print(f"✓ Dictionary saved to: {dict_file}")
    
    print("\n" + "=" * 120)
    print("TEMPLATE DICTIONARY:")
    print("-" * 100)
    for des, (rel_x, rel_y, angle) in sorted(template_dict.items()):
        print(f"  '{des}': ({rel_x:>8.3f}, {rel_y:>8.3f}, {int(angle)}),")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Extract template from Inverted_MAML_IMC.epru
User-specified area: X: 0-14mm, Y: 300-325mm
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
    print("EXTRACT TEMPLATE FROM Inverted_MAML_IMC.epru")
    print("=" * 120)
    
    epru_file = 'Inverted_MAML_IMC.epru'
    
    print(f"\nParsing: {epru_file}")
    components, designators = extract_all_components(epru_file)
    print(f"  -> Found {len(components)} total components")
    print(f"  -> Found {len(designators)} designators")
    
    # Search area
    x_min, x_max, y_min, y_max = 0, 14, 300, 325
    
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
        
        # Find anchor (lowest Y, then lowest X)
        anchor_comp = min(found, key=lambda c: (c['y_mm'], c['x_mm']))
        anchor_x_mm = anchor_comp['x_mm']
        anchor_y_mm = anchor_comp['y_mm']
        
        print(f"\n" + "=" * 120)
        print(f"TEMPLATE EXTRACTION")
        print("=" * 120)
        print(f"Anchor point: {anchor_comp['designator']} at X={anchor_x_mm:.3f}mm, Y={anchor_y_mm:.3f}mm\n")
        
        # Generate template file
        output_file = 'IMC_template_x_y_rot.txt'
        with open(output_file, 'w') as f:
            f.write("IMC TEMPLATE - USER SPECIFIED AREA (X:0-14mm, Y:300-325mm)\n")
            f.write("=" * 100 + "\n")
            f.write(f"Anchor: {anchor_comp['designator']} at X={anchor_x_mm:.3f}mm, Y={anchor_y_mm:.3f}mm\n")
            f.write(f"Search Area: X 0-14mm, Y 300-325mm\n")
            f.write("=" * 100 + "\n\n")
            f.write("Template components (sorted by Y, X):\n")
            f.write(f"{'Designator':<35} {'Rel_X (mm)':<14} {'Rel_Y (mm)':<14} {'Angle':<8} {'X (mm)':<12} {'Y (mm)':<12}\n")
            f.write("-" * 100 + "\n")
            
            for comp in sorted(found, key=lambda c: (c['y_mm'], c['x_mm'])):
                rel_x = comp['x_mm'] - anchor_x_mm
                rel_y = comp['y_mm'] - anchor_y_mm
                f.write(f"{comp['designator']:<35} {rel_x:>13.3f} {rel_y:>13.3f} {comp['angle']:>7.0f}° {comp['x_mm']:>11.3f} {comp['y_mm']:>11.3f}\n")
        
        print(f"✓ Template saved to: {output_file}\n")
        
        # Generate Python dictionary
        py_file = 'IMC_template_dict.py'
        with open(py_file, 'w') as f:
            f.write("# IMC Template Dictionary\n")
            f.write(f"# Anchor: {anchor_comp['designator']} at X={anchor_x_mm:.3f}mm, Y={anchor_y_mm:.3f}mm\n\n")
            f.write("TEMPLATE_IMC = {\n")
            
            for comp in sorted(found, key=lambda c: (c['y_mm'], c['x_mm'])):
                rel_x = comp['x_mm'] - anchor_x_mm
                rel_y = comp['y_mm'] - anchor_y_mm
                f.write(f"    '{comp['designator']}': ({rel_x:.3f}, {rel_y:.3f}, {comp['angle']:.0f}),\n")
            
            f.write("}\n\n")
            f.write(f"# Anchor configuration\n")
            f.write(f"ANCHOR_X_MM = {anchor_x_mm:.3f}\n")
            f.write(f"ANCHOR_Y_MM = {anchor_y_mm:.3f}\n")
            f.write(f"ANCHOR_DESIGNATOR = '{anchor_comp['designator']}'\n")
        
        print(f"✓ Dictionary saved to: {py_file}\n")
        
        # Show template
        print(f"TEMPLATE DICTIONARY:")
        print("-" * 100)
        for comp in sorted(found, key=lambda c: (c['y_mm'], c['x_mm'])):
            rel_x = comp['x_mm'] - anchor_x_mm
            rel_y = comp['y_mm'] - anchor_y_mm
            print(f"  '{comp['designator']}': ({rel_x:>7.3f}, {rel_y:>7.3f}, {comp['angle']:>5.0f}),")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Analyze Inverted_MAML_IMC.epru - Extract template from area X:0-14mm, Y:300-325mm
"""

import json

def mil_to_mm(mil):
    return mil / 39.3701

def mm_to_mil(mm):
    return mm * 39.3701

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
    print("INVERTED_MAML_IMC.epru - TEMPLATE EXTRACTION")
    print("=" * 120)
    
    epru_file = 'Inverted_MAML_IMC.epru'
    
    print(f"\nParsing: {epru_file}")
    components, designators = extract_all_components(epru_file)
    print(f"  -> Found {len(components)} total components")
    print(f"  -> Found {len(designators)} designators")
    
    # Get actual ranges
    if not components:
        print("ERROR: No components found!")
        return
    
    all_x_mm = [c['x_mm'] for c in components.values()]
    all_y_mm = [c['y_mm'] for c in components.values()]
    min_x_mm, max_x_mm = min(all_x_mm), max(all_x_mm)
    min_y_mm, max_y_mm = min(all_y_mm), max(all_y_mm)
    
    print(f"\n" + "=" * 120)
    print(f"COORDINATE RANGES (MM):")
    print(f"  X: {min_x_mm:>8.2f} to {max_x_mm:>8.2f} mm")
    print(f"  Y: {min_y_mm:>8.2f} to {max_y_mm:>8.2f} mm")
    print("=" * 120)
    
    # Search your area
    x_min, x_max, y_min, y_max = 0, 14, 300, 325
    
    print(f"\nSearching area: X {x_min}-{x_max}mm, Y {y_min}-{y_max}mm")
    found = search_area(components, designators, x_min, x_max, y_min, y_max)
    
    print(f"✓ Found {len(found)} components\n")
    
    if found:
        print(f"{'Designator':<35} {'X (mm)':<12} {'Y (mm)':<12} {'Angle':<8} {'Locked':<8}")
        print("-" * 100)
        for comp in found[:30]:
            locked_str = "✓" if comp['locked'] else " "
            print(f"{comp['designator']:<35} {comp['x_mm']:>11.2f} {comp['y_mm']:>11.2f} {comp['angle']:>7.0f}° {locked_str:<8}")
        if len(found) > 30:
            print(f"... and {len(found)-30} more")
    else:
        print("No components found in this area.")

if __name__ == '__main__':
    main()

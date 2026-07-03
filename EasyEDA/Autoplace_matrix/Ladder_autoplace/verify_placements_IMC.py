#!/usr/bin/env python3
"""
Verify the autoplaced_output_IMC.epru file
Sample components to confirm placements were applied correctly
"""

import json

def mil_to_mm(mil):
    return mil / 39.3701

def extract_components(epru_file):
    components = {}
    designators = {}
    
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
                    components[comp_id] = {
                        'x_mil': data.get('x', 0),
                        'y_mil': data.get('y', 0),
                        'angle': data.get('angle', 0),
                    }
            except Exception:
                continue
    
    return components, designators

def main():
    print("=" * 120)
    print("VERIFY AUTOPLACED_OUTPUT_IMC")
    print("=" * 120)
    
    original_file = 'Inverted_MAML_IMC.epru'
    output_file = 'autoplaced_output_IMC.epru'
    
    print(f"\nLoading original file: {original_file}")
    orig_comps, orig_des = extract_components(original_file)
    
    print(f"Loading output file: {output_file}")
    out_comps, out_des = extract_components(output_file)
    
    print(f"\nOriginal: {len(orig_comps)} components, {len(orig_des)} designators")
    print(f"Output: {len(out_comps)} components, {len(out_des)} designators")
    
    # Sample verification - check a few components
    sample_designators = [
        'R16$CBB17/CBB1',  # Anchor (should be unchanged)
        'R16$CBB17/CBB2',  # Should have Y offset
        'R16$CBB18/CBB1',  # Different block
        'C193$CBB20/CBB8', # Last block
    ]
    
    print(f"\n" + "=" * 120)
    print("SAMPLE VERIFICATION")
    print("=" * 120)
    
    for des in sample_designators:
        # Find component in both files
        orig_comp_id = None
        out_comp_id = None
        
        for comp_id, d in orig_des.items():
            if d == des:
                orig_comp_id = comp_id
                break
        
        for comp_id, d in out_des.items():
            if d == des:
                out_comp_id = comp_id
                break
        
        if orig_comp_id and out_comp_id:
            orig = orig_comps[orig_comp_id]
            out = out_comps[out_comp_id]
            
            orig_x_mm = mil_to_mm(orig['x_mil'])
            orig_y_mm = mil_to_mm(orig['y_mil'])
            out_x_mm = mil_to_mm(out['x_mil'])
            out_y_mm = mil_to_mm(out['y_mil'])
            
            print(f"\n{des}")
            print(f"  Original: X={orig_x_mm:>8.3f}mm, Y={orig_y_mm:>8.3f}mm, Angle={orig['angle']:>4.0f}°")
            print(f"  Output:   X={out_x_mm:>8.3f}mm, Y={out_y_mm:>8.3f}mm, Angle={out['angle']:>4.0f}°")
            
            # Calculate expected
            if des == 'R16$CBB17/CBB1':
                exp_x, exp_y, exp_a = 3.683, 310.769, 180
            elif des == 'R16$CBB17/CBB2':
                exp_x, exp_y, exp_a = 3.683, 298.269, 180  # Y - 12.5mm
            elif des == 'R16$CBB18/CBB1':
                exp_x, exp_y, exp_a = 3.683, 310.769, 180
            elif des == 'C193$CBB20/CBB8':
                exp_x, exp_y, exp_a = 11.557, 233.175, 0  # Different block
            
            print(f"  Expected: X={exp_x:>8.3f}mm, Y={exp_y:>8.3f}mm, Angle={exp_a:>4.0f}°")
            
            match = (abs(out_x_mm - exp_x) < 0.01 and 
                    abs(out_y_mm - exp_y) < 0.01 and 
                    out['angle'] == exp_a)
            
            status = "✓ MATCH" if match else "✗ MISMATCH"
            print(f"  Status: {status}")
        else:
            print(f"\n{des}: NOT FOUND in one or both files")
    
    print(f"\n" + "=" * 120)
    print("✓ Verification complete")
    print("=" * 120)

if __name__ == '__main__':
    main()

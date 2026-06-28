#!/usr/bin/env python3
import json

# Ankarpunkter för referensblocken [1,1]
ANCHORS = {
    'matrix3': (991.00, 5547.00),
    'matrix8': (989.50, 5292.00),
    'matrix33': (1242.50, 5558.75)
}

def parse_epru_file(filepath):
    designators = {}
    components = []
    
    with open(filepath, 'rb') as f:
        for line in f:
            line = line.decode('utf-8', errors='replace').strip()
            if not line or '||' not in line: continue
            try:
                parts = line.split('||')
                meta, data = json.loads(parts[0]), json.loads(parts[1].rstrip('|'))
                
                if meta.get('type') == 'ATTR' and data.get('key') == 'Designator':
                    designators[meta.get('id')] = data.get('value', '')
                elif meta.get('type') == 'COMPONENT':
                    components.append({
                        'id': meta.get('id'),
                        'x': data.get('x', 0),
                        'y': data.get('y', 0),
                        'angle': data.get('angle', 0),
                        'locked': data.get('locked', False),
                        'rb': data.get('attrs', {}).get('Reuse Block', ''),
                        'cid': data.get('attrs', {}).get('Channel ID', '')
                    })
            except: continue
    return designators, components

def main():
    filepath = '/home/olle/Downloads/Inverted_MAML_IMC/Inverted_MAML_IMC.epru'
    designators, components = parse_epru_file(filepath)
    
    with open('Template_designator_all_matrices_ANGLES.txt', 'w') as f:
        f.write("TEMPLATE BLOCKS WITH ROTATION ANGLES\n")
        f.write("================================================================================\n\n")
        
        for rb, (ax, ay) in ANCHORS.items():
            f.write(f"MATRIX {rb} [1,1] Block (anchor: {ax:.2f}, {ay:.2f} mil)\n")
            f.write("================================================================================\n")
            f.write(f"{'Designator':<20} {'Rel_X':<10} {'Rel_Y':<10} {'Angle':<10}\n")
            
            # Hämta komponenter för detta referensblock
            block_comps = [c for c in components if c['rb'] == rb and c['locked'] is True]
            
            for comp in block_comps:
                rel_x = comp['x'] - ax
                rel_y = comp['y'] - ay
                des = designators.get(comp['id'], comp['cid'])
                f.write(f"{des:<20} {rel_x:<10.1f} {rel_y:<10.1f} {comp['angle']:<10}\n")
            f.write("\n")
            
    print("Klart! Template_designator_all_matrices_ANGLES.txt har skapats med korrekta vinklar och positioner.")

if __name__ == '__main__':
    main()
# Turns OpenStreetMap round El Campín (Estadio Nemesio Camacho, Bogotá) into
# the plan tools/campin_build.py and tools/campin_assets.py work from:
# tools/campin/osm.json, in metres, turned so the pitch lies on the axes.
#   python3 tools/campin_osm.py <dir with the tiles>       (fetches them first if missing)
# The tiles are nine pieces of the OSM API's map call (each under its limit
# of 50.000 nodes) round the stadium, 1.5 x 1.5 km. Data © OpenStreetMap
# contributors, ODbL.
#
# The frame: the origin on the middle of OSM's pitch (way 226327160); its
# long axis runs 6.6 degrees east of north. x along the pitch towards the
# north end (Calle 57), y towards the Tribuna Occidental (west, Avenida NQS:
# the match camera's side), so the Tribuna Oriental with IDRD BOGOTÁ in its
# seats and the hills of Monserrate behind it lie at -y.
import json, math, os, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'campin', 'osm.json')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
TILES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'campin_osm_tiles')     # tens of MB of XML: not in the repo
LON = (-74.0843, -74.0796, -74.0749, -74.0702)
LAT = (4.6392, 4.6437, 4.6482, 4.6527)
os.makedirs(TILES, exist_ok=True)
for i in range(3):
    for j in range(3):
        f = os.path.join(TILES, 'x%dy%d.xml' % (i, j))
        if os.path.exists(f) and os.path.getsize(f) > 10000:
            continue
        url = 'https://api.openstreetmap.org/api/0.6/map?bbox=%.4f,%.4f,%.4f,%.4f' % (LON[i], LAT[j], LON[i + 1], LAT[j + 1])
        subprocess.run(['curl', '-s', '-m', '180', '-A', 'stadium-model-builder/1.0', '-o', f, url], check=True)
        time.sleep(1)

nodes, ways, rels, tree_nodes = {}, {}, {}, []
for i in range(3):
    for j in range(3):
        root = ET.parse(os.path.join(TILES, 'x%dy%d.xml' % (i, j))).getroot()
        for n in root.iter('node'):
            nodes[n.get('id')] = (float(n.get('lat')), float(n.get('lon')))
            tags = {t.get('k'): t.get('v') for t in n.iter('tag')}
            if tags.get('natural') == 'tree':
                tree_nodes.append(n.get('id'))
        for w in root.iter('way'):
            ways[w.get('id')] = ({t.get('k'): t.get('v') for t in w.iter('tag')}, [nd.get('ref') for nd in w.iter('nd')])
        for r in root.iter('relation'):
            rels[r.get('id')] = ({t.get('k'): t.get('v') for t in r.iter('tag')},
                                 [(m.get('type'), m.get('ref'), m.get('role')) for m in r.iter('member')])

# the frame from the pitch: its middle and its long axis
PITCH = '226327160'
pc = [nodes[r] for r in ways[PITCH][1][:-1]]
LAT0 = sum(p[0] for p in pc) / len(pc)
LON0 = sum(p[1] for p in pc) / len(pc)
KY = 111132.954 - 559.822 * math.cos(2 * math.radians(LAT0))
KX = 111412.84 * math.cos(math.radians(LAT0)) - 93.5 * math.cos(3 * math.radians(LAT0))
en = [((lo - LON0) * KX, (la - LAT0) * KY) for la, lo in pc]
sides = [(en[(k + 1) % 4][0] - en[k][0], en[(k + 1) % 4][1] - en[k][1]) for k in range(4)]
longest = max(sides, key=lambda v: math.hypot(*v))
if longest[1] < 0:
    longest = (-longest[0], -longest[1])
L_ = math.hypot(*longest)
EX = (longest[0] / L_, longest[1] / L_)        # towards the north end
EY = (-EX[1], EX[0])                           # towards the west (EX turned a quarter left)
TURN = math.degrees(math.atan2(EX[0], EX[1]))
print('pitch', [round(math.hypot(*v), 1) for v in sides], 'turn %.2f deg east of north' % TURN)


def local(ref):
    lat, lon = nodes[ref]
    e, n = (lon - LON0) * KX, (lat - LAT0) * KY
    return [round(e * EX[0] + n * EX[1], 2), round(e * EY[0] + n * EY[1], 2)]


def pts_of(refs):
    if not all(r in nodes for r in refs):
        return None
    return [local(r) for r in refs]


WAYS = {'226327160': 'pitch', '24020167': 'stadium_outer', '336679692': 'stadium_inner', '42828687': 'complex'}
SKIP_BUILDINGS = {'24020167', '1485142916'}     # the stadium itself; the new stadium, only begun in 2026
out = {'origin': [LAT0, LON0], 'turn_deg': round(TURN, 3), 'ways': {}, 'buildings': [], 'parts': [], 'roads': [], 'rail': [],
       'platforms': [], 'parking': [], 'grass': [], 'park': [], 'residential': [], 'pitches': [], 'water': [], 'trees': [],
       'tree_rows': [], 'walls': [], 'busway': [], 'squares': []}
used_outer = set()
for rid, (tags, mem) in rels.items():
    if tags.get('type') != 'multipolygon':
        continue
    outers = [(m[1], ways[m[1]]) for m in mem if m[0] == 'way' and m[2] == 'outer' and m[1] in ways]
    if 'building' in tags:
        for m in mem:
            if m[0] == 'way' and m[2] == 'outer':
                used_outer.add(m[1])
        if tags.get('building') in ('stadium', 'grandstand', 'roof') or any(w in SKIP_BUILDINGS for w, _ in outers):
            continue
        for wid, (tw, refs) in outers:
            p = pts_of(refs)
            if p and len(p) > 3:
                out['buildings'].append({'type': tags.get('building'), 'levels': tags.get('building:levels'), 'height': tags.get('height'),
                                         'roof': tags.get('roof:shape'), 'name': tags.get('name'), 'pts': p})
    if tags.get('highway') == 'pedestrian' or tags.get('place') == 'square':
        for wid, (tw, refs) in outers:
            p = pts_of(refs)
            if p:
                out['squares'].append(p)
for wid, (tags, refs) in ways.items():
    p = pts_of(refs)
    if not p or len(p) < 2:
        continue
    if wid in WAYS:
        out['ways'][WAYS[wid]] = p
    if 'building' in tags and wid not in used_outer and wid not in SKIP_BUILDINGS and len(p) > 3:
        out['buildings'].append({'type': tags['building'], 'levels': tags.get('building:levels'), 'height': tags.get('height'),
                                 'roof': tags.get('roof:shape'), 'min_level': tags.get('building:min_level'), 'name': tags.get('name'), 'pts': p})
    elif tags.get('building:part') and len(p) > 3:
        out['parts'].append({'levels': tags.get('building:levels'), 'min_level': tags.get('building:min_level'),
                             'material': tags.get('building:material'), 'colour': tags.get('building:colour'), 'pts': p})
    if 'highway' in tags and tags.get('area') != 'yes' and tags['highway'] not in ('platform', 'elevator'):
        rec = {'type': tags['highway'], 'name': tags.get('name'), 'layer': tags.get('layer'), 'lanes': tags.get('lanes'),
               'bridge': tags.get('bridge'), 'tunnel': tags.get('tunnel'), 'pts': p}
        if tags.get('name') == 'TransMilenio' or tags.get('busway') or tags.get('access') == 'no' and tags.get('bus') == 'designated':
            out['busway'].append(rec)
        else:
            out['roads'].append(rec)
    if tags.get('highway') == 'pedestrian' and tags.get('area') == 'yes':
        out['squares'].append(p)
    if tags.get('amenity') == 'parking' and tags.get('parking') in (None, 'surface'):
        out['parking'].append(p)
    if tags.get('landuse') in ('grass', 'meadow', 'village_green') or tags.get('leisure') == 'garden':
        out['grass'].append(p)
    if tags.get('leisure') in ('park', 'playground') or tags.get('landuse') in ('forest', 'recreation_ground') or tags.get('natural') in ('wood', 'scrub'):
        out['park'].append(p)
    if tags.get('landuse') in ('residential',):
        out['residential'].append(p)
    if tags.get('leisure') == 'pitch' and wid != PITCH:
        out['pitches'].append({'sport': tags.get('sport'), 'surface': tags.get('surface'), 'pts': p})
    if tags.get('natural') == 'water' or tags.get('waterway') in ('canal', 'river', 'stream'):
        out['water'].append(p)
    if tags.get('natural') == 'tree_row':
        out['tree_rows'].append(p)
out['trees'] = [local(r) for r in tree_nodes]
# only what lies round the stadium: the backdrop covers 640 x 640 m
L = 340
inb = lambda pts: any(abs(x) < L and abs(y) < L for x, y in pts)
for k in ('buildings', 'parts', 'roads', 'busway', 'pitches'):
    out[k] = [b for b in out[k] if inb(b['pts'])]
for k in ('platforms', 'parking', 'grass', 'park', 'residential', 'water', 'tree_rows', 'walls', 'squares'):
    out[k] = [g for g in out[k] if inb(g)]
out['trees'] = [t for t in out['trees'] if abs(t[0]) < L and abs(t[1]) < L]
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print({k: (len(v) if isinstance(v, list) else (list(v) if isinstance(v, dict) else v)) for k, v in out.items()})

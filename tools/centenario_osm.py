# Turns OpenStreetMap round the Estadio Centenario (Parque Batlle, Montevideo)
# into the plan tools/centenario_build.py and tools/centenario_assets.py work
# from: tools/centenario/osm.json, in metres, turned so the pitch lies on the axes.
#   python3 tools/centenario_osm.py <dir with the tiles>       (fetches them first if missing)
# The tiles are nine pieces of the OSM API's map call (each under its limit
# of 50.000 nodes) round the stadium, 1.5 x 1.5 km. Data © OpenStreetMap
# contributors, ODbL.
#
# The frame: the origin on the middle of OSM's pitch (way 179533172, 104.8 x
# 68.1 m); its long axis runs 59.11 degrees south of east. x along the pitch
# towards the Colombes (north-north-west), y towards the Tribuna América
# (west-south-west, the match camera's side), so the Tribuna Olímpica with
# the Torre de los Homenajes is at -y and the Amsterdam at -x.
import json, math, os, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'centenario', 'osm.json')
TILES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'centenario_osm_tiles')     # 40 MB of XML: not in the repo
LON = (-56.1610, -56.1556, -56.1502, -56.1448)
LAT = (-34.8990, -34.8960, -34.8930, -34.8900)
os.makedirs(TILES, exist_ok=True)
for i in range(3):
    for j in range(3):
        f = os.path.join(TILES, 'x%dy%d.xml' % (i, j))
        if os.path.exists(f) and os.path.getsize(f) > 10000:
            continue
        url = 'https://api.openstreetmap.org/api/0.6/map?bbox=%.4f,%.4f,%.4f,%.4f' % (LON[i], LAT[j], LON[i + 1], LAT[j + 1])
        subprocess.run(['curl', '-s', '-m', '120', '-A', 'stadium-model-builder/1.0', '-o', f, url], check=True)
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

LAT0, LON0 = -34.89451175, -56.1528198
KY = 111132.954 - 559.822 * math.cos(2 * math.radians(LAT0))
KX = 111412.84 * math.cos(math.radians(LAT0)) - 93.5 * math.cos(3 * math.radians(LAT0))
TH = math.radians(-59.11)
EX = (-math.cos(TH), -math.sin(TH))         # towards the Colombes
EY = (math.sin(TH), -math.cos(TH))         # towards the Tribuna América


def local(ref):
    lat, lon = nodes[ref]
    e, n = (lon - LON0) * KX, (lat - LAT0) * KY
    return [round(e * EX[0] + n * EX[1], 2), round(e * EY[0] + n * EY[1], 2)]


def pts_of(refs):
    if not all(r in nodes for r in refs):
        return None
    return [local(r) for r in refs]


def ring_of(rid):
    # a multipolygon's outer ways joined end to end into one closed ring of node ids
    segs = [list(ways[m[1]][1]) for m in rels[rid][1] if m[0] == 'way' and m[2] == 'outer' and m[1] in ways]
    ring_ = segs.pop(0)
    while segs:
        for k, sg in enumerate(segs):
            if sg[0] == ring_[-1]:
                ring_ += sg[1:]; segs.pop(k); break
            if sg[-1] == ring_[-1]:
                ring_ += sg[::-1][1:]; segs.pop(k); break
        else:
            break
    return ring_


STANDS = {'8725750': 'olimpica', '8725752': 'america', '8725751': 'colombes', '8725754': 'amsterdam',
          '8725748': 'platea_olimpica', '8725749': 'platea_america', '8725753': 'stadium', '8725772': 'roof'}
WAYS = {'186567918': 'field', '179533172': 'pitch', '1552527230': 'tower75', '1552527231': 'tower100', '1552527232': 'wing_a',
        '1552527233': 'wing_b', '627287793': 'platea_olimpica_front', '627287801': 'olimpica_inner', '37514651': 'olimpica_outer',
        '627287796': 'platea_america_front', '627287805': 'america_inner', '627287802': 'colombes_inner', '627287799': 'colombes_outer',
        '627287807': 'amsterdam_inner', '627287806': 'amsterdam_outer', '627287803': 'america_outer', '627289766': 'america_outer_b',
        '627289767': 'america_outer_c', '627289768': 'roof_inner'}
out = {'origin': [LAT0, LON0], 'turn_deg': 59.11, 'stadium': None, 'buildings': [], 'parts': [], 'roads': [], 'rail': [],
       'platforms': [], 'parking': [], 'grass': [], 'park': [], 'residential': [], 'pitches': [], 'water': [], 'trees': [],
       'tree_rows': [], 'walls': []}
used_outer = set()
for rid, (tags, mem) in rels.items():
    if tags.get('type') != 'multipolygon':
        continue
    outers = [ways[m[1]] for m in mem if m[0] == 'way' and m[2] == 'outer' and m[1] in ways]
    if 'building' in tags:
        for m in mem:
            if m[0] == 'way' and m[2] == 'outer':
                used_outer.add(m[1])
        if tags.get('building') in ('stadium', 'grandstand', 'roof'):
            continue                                         # the stadium itself: built from 'stands'
        for tw, refs in outers:
            p = pts_of(refs)
            if p and len(p) > 3:
                out['buildings'].append({'type': tags.get('building'), 'levels': tags.get('building:levels'), 'height': tags.get('height'),
                                         'roof': tags.get('roof:shape'), 'pts': p})
for wid, (tags, refs) in ways.items():
    p = pts_of(refs)
    if not p or len(p) < 2:
        continue
    if wid in WAYS:
        out.setdefault('ways', {})[WAYS[wid]] = p
    if 'building' in tags and wid not in used_outer and len(p) > 3:
        out['buildings'].append({'type': tags['building'], 'levels': tags.get('building:levels'), 'height': tags.get('height'),
                                 'roof': tags.get('roof:shape'), 'min_level': tags.get('building:min_level'), 'pts': p})
    elif tags.get('building:part') and len(p) > 3:
        out['parts'].append({'levels': tags.get('building:levels'), 'min_level': tags.get('building:min_level'),
                             'material': tags.get('building:material'), 'colour': tags.get('building:colour'), 'pts': p})
    if 'highway' in tags and tags.get('area') != 'yes' and tags['highway'] not in ('platform', 'elevator'):
        out['roads'].append({'type': tags['highway'], 'name': tags.get('name'), 'layer': tags.get('layer'),
                             'bridge': tags.get('bridge'), 'tunnel': tags.get('tunnel'), 'pts': p})
    if tags.get('railway') in ('rail', 'light_rail') and tags.get('area') != 'yes':
        out['rail'].append({'pts': p, 'bridge': tags.get('bridge'), 'tunnel': tags.get('tunnel'), 'service': tags.get('service')})
    if tags.get('railway') == 'platform' or (tags.get('public_transport') == 'platform' and tags.get('train') == 'yes'):
        out['platforms'].append(p)
    if tags.get('amenity') == 'parking' and tags.get('parking') in (None, 'surface'):
        out['parking'].append(p)
    if tags.get('landuse') in ('grass', 'meadow', 'village_green') or tags.get('leisure') == 'garden':
        out['grass'].append(p)
    if tags.get('leisure') in ('park', 'playground') or tags.get('landuse') in ('forest', 'recreation_ground') or tags.get('natural') in ('wood', 'scrub'):
        out['park'].append(p)
    if tags.get('landuse') in ('residential',):
        out['residential'].append(p)
    if tags.get('leisure') == 'pitch':
        out['pitches'].append({'sport': tags.get('sport'), 'surface': tags.get('surface'), 'pts': p})
    if tags.get('natural') == 'water' or tags.get('waterway') in ('canal', 'river'):
        out['water'].append(p)
    if tags.get('leisure') == 'track':
        out.setdefault('tracks', []).append(p)
    if tags.get('natural') == 'tree_row':
        out['tree_rows'].append(p)
    if tags.get('barrier') in ('wall',) and tags.get('wall') == 'noise_barrier':
        out['walls'].append(p)
out['trees'] = [local(r) for r in tree_nodes]
for rid, (tags, mem) in rels.items():
    if tags.get('leisure') == 'track':
        for m in mem:
            if m[0] == 'way' and m[1] in ways:
                pp = pts_of(ways[m[1]][1])
                if pp:
                    out.setdefault('tracks', []).append(pp)
out['stands'] = {}
for rid, nm in STANDS.items():
    if rid in rels:
        out['stands'][nm] = pts_of(ring_of(rid))
out['stadium'] = out['stands'].get('stadium')
# only what lies round the stadium: the backdrop covers 640 x 640 m
L = 340
inb = lambda pts: any(abs(x) < L and abs(y) < L for x, y in pts)
out['tracks'] = [g for g in out.get('tracks', []) if any(abs(x) < L and abs(y) < L for x, y in g)]
for k in ('buildings', 'parts', 'roads', 'rail', 'pitches'):
    out[k] = [b for b in out[k] if inb(b['pts'])]
for k in ('platforms', 'parking', 'grass', 'park', 'residential', 'water', 'tree_rows', 'walls'):
    out[k] = [g for g in out[k] if inb(g)]
out['trees'] = [t for t in out['trees'] if abs(t[0]) < L and abs(t[1]) < L]
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()})

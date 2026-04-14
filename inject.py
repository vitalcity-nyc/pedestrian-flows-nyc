"""Inject borough corridor data and simplified outlines into index.html."""
import json
from shapely.geometry import shape

BORO = json.load(open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/boroughs.geojson'))
DATA = json.load(open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/by_borough.json'))

# Build simplified outlines: tolerance in degrees (~100m)
outlines = {}
for f in BORO['features']:
    name = f['properties'].get('name') or f['properties'].get('BoroName')
    g = shape(f['geometry']).simplify(0.002, preserve_topology=True)
    rings = []
    if g.geom_type == 'Polygon':
        polys = [g]
    else:
        polys = list(g.geoms)
    for p in polys:
        ring = [[round(x,5),round(y,5)] for (x,y) in p.exterior.coords]
        if len(ring) > 4:
            rings.append(ring)
    outlines[name] = rings

# Smaller corridor payload
corridors = {"boroughs": {}}
for b, cs in DATA['boroughs'].items():
    corridors['boroughs'][b] = [{
        "peak_wkdyMD": c['peak_wkdyMD'],
        "lon": c['lon'], "lat": c['lat'],
        "wkdyAM": c.get('wkdyAM'), "wkdyPM": c.get('wkdyPM'),
        "wkndMD": c.get('wkndMD'), "wkndPM": c.get('wkndPM'),
    } for c in cs[:10]]

html = open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html').read()
html = html.replace('/*__BORODATA__*/null', json.dumps(corridors))
html = html.replace('/*__OUTLINES__*/ {}', json.dumps(outlines))
open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html','w').write(html)
print('injected; outline sizes:', {k: sum(len(r) for r in v) for k,v in outlines.items()})

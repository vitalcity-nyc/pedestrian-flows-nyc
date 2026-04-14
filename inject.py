"""Inject borough corridor data and simplified outlines into index.html."""
import json
from shapely.geometry import shape

BORO = json.load(open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/boroughs.geojson'))
DATA = json.load(open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/by_borough.json'))

# Build simplified outlines: tolerance in degrees (~100m)
outlines = {}
for f in BORO['features']:
    name = f['properties'].get('name') or f['properties'].get('BoroName')
    g = shape(f['geometry']).simplify(0.0005, preserve_topology=True)
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
        "lines": c.get('lines', [])[:15],
    } for c in cs[:10]]

import re
html = open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html').read()
html = re.sub(r'const BORO_DATA = [^;]+;',
              'const BORO_DATA = ' + json.dumps(corridors) + ';', html, count=1)
html = re.sub(r'const BORO_OUTLINES = [^;]+;',
              'const BORO_OUTLINES = ' + json.dumps(outlines) + ';', html, count=1)
open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html','w').write(html)
print('injected; outline sizes:', {k: sum(len(r) for r in v) for k,v in outlines.items()})

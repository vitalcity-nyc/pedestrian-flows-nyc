#!/bin/bash
set -e
cd "$(dirname "$0")"
SRC="/Users/joshgreenman/Downloads/kepler.gl_NYC_pednetwork_estimates_counts_2018-2019_4326pub.geojson.csv"
OUT_GEO="/tmp/pedflows.geojsonl"
OUT_MB="/tmp/pedflows.mbtiles"
OUT_PM="/Users/joshgreenman/Experiments/pedestrian-flows-nyc/pedflows.pmtiles"

echo "=> streaming CSV -> line-delimited geojson..."
python3 - <<'PY'
import csv, json, sys
csv.field_size_limit(sys.maxsize)
SRC = "/Users/joshgreenman/Downloads/kepler.gl_NYC_pednetwork_estimates_counts_2018-2019_4326pub.geojson.csv"
OUT = "/tmp/pedflows.geojsonl"
with open(SRC, newline='') as f, open(OUT, 'w') as w:
    n = 0
    for row in csv.DictReader(f):
        try:
            gj = json.loads(row['_geojson'])
        except Exception:
            continue
        p = gj.get('properties', {})
        # trim to the 6 time-slot integers
        try:
            props = {
                'am':  int(float(p.get('predwkdyAM') or 0)),
                'md':  int(float(p.get('predwkdyMD') or 0)),
                'pm':  int(float(p.get('predwkdyPM') or 0)),
                'wam': int(float(p.get('predwkndAM') or 0)),
                'wmd': int(float(p.get('predwkndMD') or 0)),
                'wpm': int(float(p.get('predwkndPM') or 0)),
            }
        except Exception:
            continue
        props['peak'] = max(props.values())
        feat = { 'type':'Feature', 'geometry': gj['geometry'], 'properties': props }
        w.write(json.dumps(feat, separators=(',',':')))
        w.write('\n')
        n += 1
        if n % 50000 == 0: print('  ', n, 'features')
print('wrote', n, 'features')
PY

echo "=> tippecanoe -> mbtiles..."
tippecanoe -o "$OUT_MB" --force \
  -l segs \
  -Z 9 -z 15 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  --no-feature-limit --no-tile-size-limit \
  --simplification=3 \
  --read-parallel \
  "$OUT_GEO"

echo "=> mbtiles -> pmtiles..."
python3 -c "from pmtiles.convert import mbtiles_to_pmtiles; mbtiles_to_pmtiles('$OUT_MB','$OUT_PM', maxzoom=15)"

ls -lh "$OUT_PM"

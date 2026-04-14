"""Per-borough aggregation: top corridors + borough totals."""
import ijson, json, math
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.prepared import prep

SRC = "/Users/joshgreenman/Downloads/NYC_pednetwork_estimates_counts_2018-2019.geojson"
BORO = json.load(open("/Users/joshgreenman/Experiments/pedestrian-flows-nyc/boroughs.geojson"))

tx = Transformer.from_crs(6538, 4326, always_xy=True)

boros = []  # list of (name, prepared_geom, bounds)
for f in BORO["features"]:
    name = f["properties"].get("BoroName") or f["properties"].get("name")
    geom = shape(f["geometry"]).buffer(0)
    boros.append((name, prep(geom), geom.bounds))

def which_boro(lon, lat):
    p = Point(lon, lat)
    for name, pg, b in boros:
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
            if pg.contains(p):
                return name
    return None

# Per-borough lists of candidate segments (wkdyMD, lon, lat, coords)
by_boro = {n: [] for (n,_,_) in boros}
totals_by_boro = {n: {"wkdyMD":0.0, "wkdyPM":0.0, "wkndPM":0.0, "segs":0} for (n,_,_) in boros}

n=0
with open(SRC, "rb") as f:
    for feat in ijson.items(f, "features.item"):
        n+=1
        p = feat.get("properties", {})
        md = p.get("predwkdyMD") or 0
        try: md = float(md)
        except: md = 0
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        flat = []
        if geom.get("type") == "LineString":
            flat = coords
        elif geom.get("type") == "MultiLineString":
            for ls in coords: flat.extend(ls)
        if not flat: continue
        mid = flat[len(flat)//2]
        try: lon, lat = tx.transform(mid[0], mid[1])
        except Exception: continue
        b = which_boro(lon, lat)
        if not b: continue

        # transform full path (subsample) for rendering later if needed
        totals_by_boro[b]["segs"] += 1
        for k,fld in [("wkdyMD","predwkdyMD"),("wkdyPM","predwkdyPM"),("wkndPM","predwkndPM")]:
            v = p.get(fld)
            try: totals_by_boro[b][k] += float(v or 0)
            except: pass

        if md > 200:  # only keep plausible candidates
            # transform all vertices for the segment line
            line_ll = []
            for c in flat:
                try:
                    lo, la = tx.transform(c[0], c[1])
                    line_ll.append([round(lo,5), round(la,5)])
                except: pass
            by_boro[b].append((md, lon, lat, line_ll,
                               p.get("predwkdyAM"), p.get("predwkdyPM"),
                               p.get("predwkndMD"), p.get("predwkndPM")))
        if n % 50000 == 0: print("processed", n)

# For each borough, cluster segments into "corridors" by proximity (greedy 300m)
import math
def haversine(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    R=6371000
    p1=math.radians(lat1); p2=math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    x=math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

CORRIDOR_RADIUS_M = 250
out = {"boroughs": {}, "totals_by_boro": totals_by_boro}
for b, segs in by_boro.items():
    segs.sort(reverse=True, key=lambda s: s[0])
    corridors = []  # each: {peak, center, lines[]}
    for s in segs:
        md, lon, lat, line, am, pm, wmd, wpm = s
        placed=False
        for co in corridors:
            if haversine((lon,lat), co["center"]) < CORRIDOR_RADIUS_M:
                co["lines"].append(line)
                if md > co["peak"]:
                    co["peak"]=md; co["center"]=(lon,lat)
                    co["wkdyAM"]=am; co["wkdyPM"]=pm
                    co["wkndMD"]=wmd; co["wkndPM"]=wpm
                placed=True; break
        if not placed:
            corridors.append({"peak":md,"center":(lon,lat),
                              "lines":[line],
                              "wkdyAM":am,"wkdyPM":pm,"wkndMD":wmd,"wkndPM":wpm})
        if len(corridors) >= 60: break  # we only need top ~10
    top = corridors[:10]
    out["boroughs"][b] = [{
        "peak_wkdyMD": int(c["peak"]),
        "lon": round(c["center"][0],5),
        "lat": round(c["center"][1],5),
        "wkdyAM": c["wkdyAM"], "wkdyPM": c["wkdyPM"],
        "wkndMD": c["wkndMD"], "wkndPM": c["wkndPM"],
        "lines": c["lines"][:12],
    } for c in top]

json.dump(out, open("/Users/joshgreenman/Experiments/pedestrian-flows-nyc/by_borough.json","w"), indent=1)
print("done", n)
for b, segs in by_boro.items():
    print(f"  {b}: {len(segs)} candidates, top corridor {segs[0][0] if segs else 0}")

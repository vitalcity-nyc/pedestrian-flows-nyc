"""Stream-aggregate the MIT City Form Lab pedestrian network geojson."""
import ijson, json, heapq
from pyproj import Transformer

SRC = "/Users/joshgreenman/Downloads/NYC_pednetwork_estimates_counts_2018-2019.geojson"
# EPSG 6538 -> WGS84
tx = Transformer.from_crs(6538, 4326, always_xy=True)

TIME_FIELDS = ["predwkdyAM","predwkdyMD","predwkdyPM","predwkndAM","predwkndMD","predwkndPM"]
COUNT_FIELDS = ["Wkdy_AM_CT","Wkdy_MD_CT","Wkdy_PM_CT","Wknd_AM_CT","Wknd_MD_CT","Wknd_PM_CT"]
OD_FIELDS = ["HME_SCH","HME_MTA","HME_PRK","HME_JOB","HME_AMN","JOB_AMN","JOB_MTA","AMN_AMN","AMN_MTA"]

totals = {k:0.0 for k in TIME_FIELDS+COUNT_FIELDS+OD_FIELDS}
n_segs = 0
n_count_wkdy = 0
n_count_wknd = 0
# top-N segments by weekday midday predicted volume
top_heap = []  # (val, idx, props, midpoint_lonlat)

# distribution buckets for weekday MD
buckets = [0,10,50,100,250,500,1000,2500,5000,10000,100000]
bucket_counts = [0]*(len(buckets)-1)

with open(SRC, "rb") as f:
    for feat in ijson.items(f, "features.item"):
        n_segs += 1
        p = feat.get("properties", {})
        for k in TIME_FIELDS+OD_FIELDS:
            v = p.get(k)
            if v is not None:
                try: totals[k] += float(v)
                except: pass
        for k in COUNT_FIELDS:
            v = p.get(k)
            if v is not None:
                try: totals[k] += float(v)
                except: pass
        if p.get("CountLoc") == 1: n_count_wkdy += 1
        if p.get("CntLocWKND") == 1: n_count_wknd += 1

        md = p.get("predwkdyMD") or 0
        try: md = float(md)
        except: md = 0
        # bucket
        for i in range(len(buckets)-1):
            if buckets[i] <= md < buckets[i+1]:
                bucket_counts[i] += 1; break

        # top N — need midpoint for map
        if md > 0:
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []
            # MultiLineString or LineString
            flat = []
            if geom.get("type") == "LineString":
                flat = coords
            elif geom.get("type") == "MultiLineString":
                for ls in coords: flat.extend(ls)
            if flat:
                mid = flat[len(flat)//2]
                try:
                    lon, lat = tx.transform(mid[0], mid[1])
                except Exception:
                    lon, lat = None, None
                entry = (md, n_segs, {
                    "wkdyMD": md,
                    "wkdyAM": p.get("predwkdyAM"),
                    "wkdyPM": p.get("predwkdyPM"),
                    "wkndMD": p.get("predwkndMD"),
                }, [lon, lat])
                if len(top_heap) < 50:
                    heapq.heappush(top_heap, entry)
                else:
                    heapq.heappushpop(top_heap, entry)

        if n_segs % 50000 == 0:
            print(f"  processed {n_segs:,} segments...")

top = sorted(top_heap, reverse=True)
out = {
    "n_segments": n_segs,
    "n_count_locations_weekday": n_count_wkdy,
    "n_count_locations_weekend": n_count_wknd,
    "totals": totals,
    "bucket_edges": buckets,
    "bucket_counts_wkdyMD": bucket_counts,
    "top_segments_wkdyMD": [
        {"wkdyMD": v, "coord": c, **props} for (v,_,props,c) in top
    ],
}
with open("/Users/joshgreenman/Experiments/pedestrian-flows-nyc/aggregates.json","w") as f:
    json.dump(out, f, indent=2, default=str)
print("done", n_segs)

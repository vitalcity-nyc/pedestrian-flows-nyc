import json, time, urllib.request, urllib.parse
P = "/Users/joshgreenman/Experiments/pedestrian-flows-nyc/highlights.json"
d = json.load(open(P))
def rg(lat, lon):
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "zoom": 17, "addressdetails": 1})
    req = urllib.request.Request("https://nominatim.openstreetmap.org/reverse?"+q,
        headers={"User-Agent": "vitalcity-pedflows/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        j = json.loads(r.read())
    a = j.get("address", {})
    road = a.get("road") or a.get("pedestrian") or a.get("footway") or ""
    hood = a.get("neighbourhood") or a.get("suburb") or a.get("quarter") or a.get("city_district") or ""
    boro = a.get("borough") or a.get("city_district") or ""
    return road, hood, boro
for x in d:
    if x.get('road'): continue
    try:
        road, hood, boro = rg(x['lat'], x['lon'])
        x['road']=road; x['hood']=hood; x['boro']=boro
        print(f"#{x['rank']:2d} {road} / {hood} / {boro}")
    except Exception as e:
        print("err", e); x['road']=''; x['hood']=''; x['boro']=''
    time.sleep(1.1)
json.dump(d, open(P,"w"), indent=1)

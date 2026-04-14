"""Reverse-geocode each corridor center via Nominatim and add a 'label' field."""
import json, time, urllib.request, urllib.parse

PATH = "/Users/joshgreenman/Experiments/pedestrian-flows-nyc/by_borough.json"
d = json.load(open(PATH))

def rg(lat, lon):
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "zoom": 17, "addressdetails": 1})
    url = "https://nominatim.openstreetmap.org/reverse?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "vitalcity-pedflows/1.0 (editorial)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        j = json.loads(r.read())
    a = j.get("address", {})
    road = a.get("road") or a.get("pedestrian") or a.get("footway") or ""
    hood = a.get("neighbourhood") or a.get("suburb") or a.get("quarter") or a.get("city_district") or ""
    if road and hood: return f"{road}, {hood}"
    if road: return road
    if hood: return hood
    return j.get("display_name", "").split(",")[0]

for boro, cs in d["boroughs"].items():
    for i, c in enumerate(cs):
        if c.get("label"): continue
        try:
            c["label"] = rg(c["lat"], c["lon"])
            print(f"{boro} #{i+1}: {c['label']}")
        except Exception as e:
            c["label"] = ""
            print(f"{boro} #{i+1}: ERROR {e}")
        time.sleep(1.1)  # Nominatim usage policy

json.dump(d, open(PATH, "w"), indent=1)
print("done")

"""Scan the CSV and pick ~18 editorially distinct segments across NYC.

Story categories (each seeded with top-N after spatial de-dup):
  - Busiest overall (peak of all six time slots)
  - Weekday morning rush champion (highest wkdyAM)
  - Weekday evening rush champion (highest wkdyPM)
  - Weekend nightlife peak (highest wkndPM)
  - Biggest weekend-over-weekday flip (wknd total / wkdy total, min volume)
  - Biggest weekday-only corridor (wkdy total / wknd total, min volume)
  - Morning-skewed corridor (AM / PM ratio)
  - Outer-borough champion per borough (busiest non-Manhattan)
"""
import csv, json, math, sys
csv.field_size_limit(sys.maxsize)

SRC = "/Users/joshgreenman/Downloads/kepler.gl_NYC_pednetwork_estimates_counts_2018-2019_4326pub.geojson.csv"

segs = []  # each: dict with mid, line, counts
with open(SRC, newline='') as f:
    r = csv.DictReader(f)
    for i, row in enumerate(r):
        gj = json.loads(row['_geojson'])
        coords = gj['geometry']['coordinates']
        if not coords or len(coords) < 2: continue
        mid = coords[len(coords)//2]
        p = gj['properties']
        try:
            am = float(p.get('predwkdyAM') or 0)
            md = float(p.get('predwkdyMD') or 0)
            pm = float(p.get('predwkdyPM') or 0)
            wam = float(p.get('predwkndAM') or 0)
            wmd = float(p.get('predwkndMD') or 0)
            wpm = float(p.get('predwkndPM') or 0)
        except: continue
        peak = max(am, md, pm, wam, wmd, wpm)
        if peak < 50: continue  # trim floor
        segs.append({
            'mid': [round(mid[0],6), round(mid[1],6)],
            'line': [[round(c[0],5), round(c[1],5)] for c in coords],
            'am': am, 'md': md, 'pm': pm,
            'wam': wam, 'wmd': wmd, 'wpm': wpm,
            'peak': peak,
        })
print("segments loaded (>=50 peak):", len(segs))

def hav(a, b):
    R=6371000
    lo1,la1=a; lo2,la2=b
    p1=math.radians(la1); p2=math.radians(la2)
    dp=math.radians(la2-la1); dl=math.radians(lo2-lo1)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

def pick_top(scored, n, min_sep_m=500, already=None):
    already = list(already or [])
    picked = []
    for s, score, *extra in scored:
        p = s['mid']
        if any(hav(p, q['mid']) < min_sep_m for q in already+picked):
            continue
        picked.append(s)
        if len(picked) >= n: break
    return picked

def tag(seg, category, detail):
    seg['category'] = category
    seg['detail'] = detail
    return seg

# --- Busiest overall
busy = sorted(segs, key=lambda s: -s['peak'])
top_busy = pick_top([(s, s['peak']) for s in busy], 3)
for i, s in enumerate(top_busy):
    tag(s, 'Busiest overall', f"Peak {int(s['peak'])}/hr — ranks #{i+1} citywide")

# --- Morning rush
am_rank = sorted(segs, key=lambda s: -s['am'])
top_am = pick_top([(s, s['am']) for s in am_rank], 2, already=top_busy)
for s in top_am:
    tag(s, 'Weekday morning rush', f"{int(s['am'])}/hr on weekday mornings (8–10 a.m.)")

# --- Evening rush
pm_rank = sorted(segs, key=lambda s: -s['pm'])
top_pm = pick_top([(s, s['pm']) for s in pm_rank], 2, already=top_busy+top_am)
for s in top_pm:
    tag(s, 'Weekday evening rush', f"{int(s['pm'])}/hr on weekday evenings (5–7 p.m.)")

# --- Weekend nightlife peak
wpm_rank = sorted(segs, key=lambda s: -s['wpm'])
top_wpm = pick_top([(s, s['wpm']) for s in wpm_rank], 2, already=top_busy+top_am+top_pm)
for s in top_wpm:
    tag(s, 'Weekend night peak', f"{int(s['wpm'])}/hr Saturday–Sunday evenings")

# --- Biggest weekend flip (wknd / wkdy, must have decent volume)
def wknd_ratio(s):
    wkdy = s['am']+s['md']+s['pm']
    wknd = s['wam']+s['wmd']+s['wpm']
    if wkdy < 200: return -1
    return wknd / max(wkdy, 1)
flip = sorted(segs, key=lambda s: -wknd_ratio(s))
top_flip = pick_top([(s, wknd_ratio(s)) for s in flip if wknd_ratio(s) > 1.2], 3,
                    already=top_busy+top_am+top_pm+top_wpm)
for s in top_flip:
    r = wknd_ratio(s)
    tag(s, 'Weekend destination', f"{r:.1f}× busier on weekends than weekdays")

# --- Biggest weekday-only corridor
def wkdy_ratio(s):
    wkdy = s['am']+s['md']+s['pm']
    wknd = s['wam']+s['wmd']+s['wpm']
    if wkdy < 400: return -1
    return wkdy / max(wknd, 1)
office = sorted(segs, key=lambda s: -wkdy_ratio(s))
top_office = pick_top([(s, wkdy_ratio(s)) for s in office if wkdy_ratio(s) > 2], 2,
                      already=top_busy+top_am+top_pm+top_wpm+top_flip)
for s in top_office:
    r = wkdy_ratio(s)
    tag(s, 'Office-hours only', f"{r:.1f}× busier on weekdays — quiet weekends")

# --- Outer-borough champions (use lon/lat bounding boxes as rough proxy; real check later)
# Manhattan roughly lon [-74.02,-73.91], lat [40.70,40.88]
def in_manhattan(p):
    lo, la = p
    return -74.03 <= lo <= -73.91 and 40.70 <= la <= 40.88
outer = [s for s in segs if not in_manhattan(s['mid'])]
outer_rank = sorted(outer, key=lambda s: -s['peak'])
taken = top_busy+top_am+top_pm+top_wpm+top_flip+top_office
top_outer = pick_top([(s, s['peak']) for s in outer_rank], 4, min_sep_m=2500, already=taken)
for s in top_outer:
    tag(s, 'Outer-borough hotspot', f"Peak {int(s['peak'])}/hr — top outside Manhattan")

picks = top_busy + top_am + top_pm + top_wpm + top_flip + top_office + top_outer
print(f"picked {len(picks)} highlights")

out = []
for i, s in enumerate(picks):
    out.append({
        'rank': i+1,
        'lon': s['mid'][0], 'lat': s['mid'][1],
        'category': s['category'], 'detail': s['detail'],
        'am': int(s['am']), 'md': int(s['md']), 'pm': int(s['pm']),
        'wam': int(s['wam']), 'wmd': int(s['wmd']), 'wpm': int(s['wpm']),
        'peak': int(s['peak']),
        'line': s['line'],
    })

json.dump(out, open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/highlights.json','w'), indent=1)
print("wrote highlights.json")

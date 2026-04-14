"""Inject highlights.json into index.html."""
import json, re
DATA = json.load(open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/highlights.json'))
html = open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html').read()
pat = re.compile(r'const DATA = /\*__HIGHLIGHTS__\*/\[[^;]*\];', re.DOTALL)
repl = 'const DATA = /*__HIGHLIGHTS__*/' + json.dumps(DATA, ensure_ascii=False) + ';'
html = pat.sub(lambda m: repl, html, count=1)
open('/Users/joshgreenman/Experiments/pedestrian-flows-nyc/index.html','w').write(html)
print('injected', len(DATA), 'highlights')

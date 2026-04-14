"""Range-capable static server (pmtiles needs HTTP byte serving)."""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from RangeHTTPServer import RangeRequestHandler
from http.server import ThreadingHTTPServer
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8824
print(f"serving pedestrian-flows-nyc on :{port} (range-capable)")
ThreadingHTTPServer(("", port), RangeRequestHandler).serve_forever()

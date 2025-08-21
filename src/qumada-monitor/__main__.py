import argparse

from .app import make_app

p = argparse.ArgumentParser(description="Dash front-end for your measurement WebSocket")
p.add_argument("--ws", default="ws://127.200.200.9:6789", help="WebSocket URL, e.g. ws://localhost:8765")
p.add_argument("--host", default="127.0.0.1", help="Dash host to bind")
p.add_argument("--port", default=8050, type=int, help="Dash port (default: 8050)")
p.add_argument("--debug", default=False, action="store_true", help="Enable debug mode")
args = p.parse_args()

app = make_app(args.ws)
app.run(host=args.host, port=args.port, debug=args.debug)

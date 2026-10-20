"""Entry point for python -m sca.web."""

import argparse
from sca.web.app import create_app

def main():
    parser = argparse.ArgumentParser(prog="sca-web", description="SCA Web Analyzer Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()
    print(f"Starting SCA Web Server at http://{args.host}:{args.port}")
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()

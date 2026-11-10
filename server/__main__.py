"""Run the API (and the built web app, if present):  python -m server  [--port 8000] [--reload]"""

import argparse

import uvicorn


def main() -> None:
    """Parse the command line and start uvicorn."""
    parser = argparse.ArgumentParser(description="TerraPulse API + web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart on code changes (development)")
    args = parser.parse_args()
    uvicorn.run("server.app:create_app", factory=True, host=args.host, port=args.port, reload=args.reload,
                log_level="info")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Chat Arena - Startup Script

Run this script to start the Chat Arena server.

Usage:
    python run.py

Environment variables:
    HOST - Server host (default: 0.0.0.0)
    PORT - Server port (default: 8000)
    OPENAI_API_KEY - OpenAI API key for Whisper speech-to-text fallback
"""

import uvicorn
import sys
import os
import argparse
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Chat Arena server")
    parser.add_argument(
        "--conversations-dir",
        default=None,
        help="override conversations directory path explicitly",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="disable uvicorn reload even in local mode",
    )
    return parser.parse_args()


def resolve_conversations_dir(args: argparse.Namespace) -> Path:
    if args.conversations_dir:
        return Path(args.conversations_dir).expanduser().resolve()
    return (PROJECT_ROOT / "server" / "data" / "conversations").resolve()


def main():
    args = parse_args()
    conversations_dir = resolve_conversations_dir(args)
    conversations_dir.mkdir(parents=True, exist_ok=True)

    os.environ["CHAT_ARENA_CONVERSATIONS_DIR"] = str(conversations_dir)

    from server.config import HOST, PORT

    reload_enabled = not args.no_reload

    print("=" * 50)
    print("  Chat Arena - Real-time Research Chat Platform")
    print("=" * 50)
    print()
    print(f"  Conversations dir: {conversations_dir}")
    print(f"  Starting server at http://{HOST}:{PORT}")
    print(f"  Admin page: http://{HOST}:{PORT}/admin")
    print()
    print("  Press Ctrl+C to stop the server")
    print("=" * 50)
    print()

    uvicorn.run(
        "server.main:app",
        host=HOST,
        port=PORT,
        reload=reload_enabled,
        log_level="info"
    )


if __name__ == "__main__":
    main()

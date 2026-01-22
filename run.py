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

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.config import HOST, PORT


def main():
    print("=" * 50)
    print("  Chat Arena - Real-time Research Chat Platform")
    print("=" * 50)
    print()
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
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

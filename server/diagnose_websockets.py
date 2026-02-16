#!/usr/bin/env python3
"""
Diagnostic script to identify WebSocket connection issues.
Run this alongside your server to monitor connection state.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from websocket_manager import manager


async def monitor_connections(interval: float = 5.0):
    """Periodically monitor and report connection state."""
    while True:
        try:
            await asyncio.sleep(interval)
            
            # Get current state
            num_connections = len(manager.connections)
            num_sessions = len(manager.sessions)
            num_ai_sessions = len(manager.ai_sessions)
            
            # Count paired vs unpaired
            paired_count = sum(1 for s in manager.sessions.values() if s.paired)
            unpaired_count = num_sessions - paired_count
            
            # Check for stale connections
            stale_connections = check_stale_connections()
            
            # Build report
            report = {
                "timestamp": datetime.now().isoformat(),
                "active_connections": num_connections,
                "active_sessions": num_sessions,
                "paired_users": paired_count,
                "waiting_users": unpaired_count,
                "ai_sessions": num_ai_sessions,
                "stale_connections": len(stale_connections),
                "queue_size": len(manager.pairing_service.queue) if hasattr(manager, 'pairing_service') else 0,
            }
            
            # Alert if discrepancy detected
            if num_connections != num_sessions:
                report["⚠️_WARNING"] = f"Mismatch! {num_connections} connections but {num_sessions} sessions"
            
            if stale_connections:
                report["⚠️_STALE_CONNECTIONS"] = stale_connections
            
            print(json.dumps(report, indent=2))
            
        except Exception as e:
            print(f"[ERROR] Monitor error: {e}")


def check_stale_connections() -> list[str]:
    """Check for connections without corresponding sessions."""
    stale = []
    for user_id in manager.connections.keys():
        if user_id not in manager.sessions:
            stale.append(user_id)
    return stale


def get_connection_details() -> Dict[str, Any]:
    """Get detailed connection information."""
    details = {
        "timestamp": datetime.now().isoformat(),
        "connections": {},
        "sessions": {},
    }
    
    for user_id, ws in manager.connections.items():
        details["connections"][user_id] = {
            "type": type(ws).__name__,
            "state": ws.client_state.name if hasattr(ws, 'client_state') else "unknown",
        }
    
    for user_id, session in manager.sessions.items():
        details["sessions"][user_id] = {
            "paired": session.paired,
            "partner_id": session.partner_id,
            "session_id": session.session_id,
            "is_ai_partner": session.is_ai_partner,
        }
    
    return details


async def simulate_load(num_users: int = 5):
    """Simulate multiple user connections for testing."""
    print(f"[TEST] Simulating {num_users} users connecting...")
    
    # This is a placeholder - you'd need a real WebSocket client
    # For now, just shows the structure
    print("Note: Actual load testing requires WebSocket clients")
    print("Consider using tools like:")
    print("  - locust with WebSocket support")
    print("  - websocket-client library")
    print("  - artillery.io")


if __name__ == "__main__":
    print("WebSocket Diagnostics")
    print("=" * 50)
    asyncio.run(monitor_connections())

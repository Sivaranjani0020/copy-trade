"""
logger.py
Centralized logging system.
- Program logs: describe what each file/module does.
- Runtime logs: record actions (client enabled, order placed, SL/Target hit).
- All logs stored in Supabase for audit and future reference.
"""

import supabase
from datetime import datetime
from config.settings import SUPABASE_URL, SUPABASE_KEY

# Supabase setup
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def log_program_event(event: str, details: dict = None):
    """
    Log program-level events (e.g., 'Web app started', 'Clients logged in').
    """
    try:
        supabase_client.table("program_logs").insert({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details or {}
        }).execute()
        print(f"[PROGRAM LOG] {event} | {details}")
    except Exception as e:
        print(f"[ERROR] Failed to log program event: {event} | {e}")

def log_order_event(client_id: str, action: str, parsed_call: dict, response: dict):
    """
    Log runtime order events (e.g., 'OrderPlaced', 'AutoExit_SL').
    """
    try:
        supabase_client.table("order_logs").insert({
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "action": action,
            "symbol": parsed_call.get("symbol"),
            "token": parsed_call.get("token"),
            "side": parsed_call.get("side"),
            "qty": parsed_call.get("qty"),
            "sl": parsed_call.get("sl"),
            "target": parsed_call.get("target"),
            "response": str(response)
        }).execute()
        print(f"[ORDER LOG] {client_id} | {action} | {parsed_call.get('symbol')} | {response}")
    except Exception as e:
        print(f"[ERROR] Failed to log order event for {client_id}: {action} | {e}")

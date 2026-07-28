"""
client_manager.py

Manages follower client sessions.

Responsibilities:
- Load enabled follower clients from Supabase.
- Login each enabled follower client.
- Store each client's configured lots.
- Return active follower sessions.

This module does not place orders or handle
copy trading logic.
"""

from helper_funct.client_login import login_xts
from services.logger import log_program_event
from config.settings import SUPABASE_URL, SUPABASE_KEY
import supabase

# Supabase client
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def load_enabled_clients():
    """
    Fetch enabled clients from Supabase table 'enabled_clients'.
    Returns a list of client_ids.
    """
    response = (
        supabase_client
        .table("enabled_clients")
        .select("client_id, lots")
        .eq("enabled_flag", True)
        .execute()
    )

    clients = response.data

    log_program_event(
        "Loaded enabled clients",
        details={"count": len(clients)}
    )

    return clients

def login_clients(client_ids=None):
    """
    Perform login for all enabled clients or a provided list.
    Returns dict of client_id → session objects.
    """

    if client_ids is None:
        client_ids = load_enabled_clients()

    sessions = {}

    for client in client_ids:

        # Supports both old style (list of client_ids)
        # and new style (list of dicts with lots)
        if isinstance(client, dict):
            cid = client["client_id"]
            lots = client.get("lots", 1)
        else:
            cid = client
            lots = 1

        try:
            session = login_xts(cid)

            # Store lots with the session
            session["lots"] = lots

            sessions[cid] = session

            log_program_event(
                "Client logged in",
                details={
                    "client_id": cid,
                    "lots": lots
                }
            )

        except Exception as e:

            log_program_event(
                "Login failed",
                details={
                    "client_id": cid,
                    "error": str(e)
                }
            )

    return sessions
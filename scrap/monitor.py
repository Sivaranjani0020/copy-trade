"""
monitor.py
Monitors live positions for all enabled clients.
- Connects to market data via helper_funct/client_market_details.py.
- Continuously checks LTP against SL/Target.
- Places exit orders when conditions are met.
- Logs all monitoring actions into Supabase (program_logs + order_logs).
"""

import time
import threading
from helper_funct.client_market_details import fetch_ltp
from helper_funct.client_order_funct import place_square_off_order, place_square_off_buy_order
from services.logger import log_order_event, log_program_event
from config.settings import SUPABASE_URL, SUPABASE_KEY
import supabase

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)


def monitor_loop(sessions):
    """
    Continuous monitoring loop for all active calls in Supabase.
    """
    segment = 2  # NSEFO segment

    log_program_event("Monitoring started", details={"clients": list(sessions.keys())})

    while True:
        # Get all OPEN calls from Supabase
        active_calls = supabase_client.table("active_calls").select("*").eq("status", "OPEN").execute().data

        for cid, sess in sessions.items():
            market_bt = sess["Market_Xt"]
            interactive_bt = sess["Interactive_Xt"]

            for call in active_calls:
                ltp = fetch_ltp(market_bt, segment, call["token"])
                if ltp is None:
                    continue

                # Check SL/Target
                if call["side"] == "BUY":
                    if ltp <= call["sl"]:
                        resp = place_square_off_order(interactive_bt, call["token"], cid, call["qty"])
                        log_order_event(cid, "AutoExit_SL", call, resp)
                        supabase_client.table("active_calls").update({"status": "CLOSED"}).eq("id", call["id"]).execute()
                    elif ltp >= call["target"]:
                        resp = place_square_off_order(interactive_bt, call["token"], cid, call["qty"])
                        log_order_event(cid, "AutoExit_Target", call, resp)
                        supabase_client.table("active_calls").update({"status": "CLOSED"}).eq("id", call["id"]).execute()

                elif call["side"] == "SELL":
                    if ltp >= call["sl"]:
                        resp = place_square_off_buy_order(interactive_bt, call["token"], cid, call["qty"])
                        log_order_event(cid, "AutoExit_SL", call, resp)
                        supabase_client.table("active_calls").update({"status": "CLOSED"}).eq("id", call["id"]).execute()
                    elif ltp <= call["target"]:
                        resp = place_square_off_buy_order(interactive_bt, call["token"], cid, call["qty"])
                        log_order_event(cid, "AutoExit_Target", call, resp)
                        supabase_client.table("active_calls").update({"status": "CLOSED"}).eq("id", call["id"]).execute()

        time.sleep(5)  # Poll every 5 seconds


def start_monitoring(sessions, parsed_call):
    """
    Start monitoring in a background thread so Flask remains responsive.
    """
    thread = threading.Thread(target=monitor_loop, args=(sessions,), daemon=True)
    thread.start()
    log_program_event("Monitoring thread launched", details={"clients": list(sessions.keys())})


"""
exit_manager.py

Squares off selected follower orders.

Responsibilities:
- Receive a follower order from the dashboard.
- Place the opposite LIMIT order (LTP ± 1).
- Update the follower position status.

This module only handles manual square-off
for follower accounts.
"""

from helper_funct.client_order_funct import place_limit_order
from helper_funct.client_market_details import fetch_ltp

from services.copy_position_manager import update_position, close_position
from services.logger import (
    log_order_event,
    log_program_event
)


def exit_position(position, sessions):
    """
    Square off a follower order.
    """
    print("\n===== EXIT POSITION CALLED =====")
    print(position)
    client_id = position["client_id"]

    session = sessions.get(client_id)

    if not session:
        return {
            "status": "failed",
            "message": "Client session not found"
        }

    interactive_xt = session["Interactive_Xt"]
    market_xt = session.get("Market_Xt")  # ensure Market_Xt client is stored in sessions

    exit_side = "SELL" if position["side"] == "BUY" else "BUY"

    # Fetch live LTP from market API
    ltp = None
    if market_xt:
        ltp = fetch_ltp(market_xt, segment=2, token=position["instrument_id"])

    # Fallback if LTP is missing or invalid
    if not ltp or ltp <= 0:
        ltp = position.get("entry_price", 1)

    # Decide limit price based on exit side
    if exit_side == "SELL":
        limit_price = ltp - 1 if ltp > 1 else ltp
    else:
        limit_price = ltp + 1

    response = place_limit_order(
        bt=interactive_xt,
        ins_token=position["instrument_id"],
        cl_id=client_id,
        qty=position["qty"],
        side=exit_side,
        lmt_price=limit_price
    )

    log_program_event(
        "Follower Square Off",
        details={
            "client_id": client_id,
            "master_order_id": position.get("master_order_id"),
            "response": response
        }
    )

    if response.get("type") == "success":
        # Update follower position status only (Positions tab)
        update_position(position["app_order_id"], status="Closed")
        # Or use close_position if you want to zero out qty/side
        # close_position(client_id, position["symbol"])

        log_order_event(
            client_id,
            "Follower Square Off",
            position,
            {"status": "Closed"}
        )

    return response

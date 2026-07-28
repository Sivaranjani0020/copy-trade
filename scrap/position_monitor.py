"""
position_monitor.py

Monitors only MASTER positions.

Followers are exited whenever the corresponding
master position hits SL / Target.
"""

import threading
import time

from helper_funct.client_market_details import fetch_ltp

from services.logger import log_program_event

from services.master_position_manager import (
    get_master_positions,
    update_master_ltp,
    update_master_position
)

from services.position_manager import (
    get_positions
)

from services.exit_manager import exit_position


_monitor_running = False


def monitor_positions(master_session, follower_sessions):

    global _monitor_running

    if _monitor_running:
        return

    _monitor_running = True

    def run():

        while True:

            try:

                market_xt = master_session["Market_Xt"]

                master_positions = get_master_positions()

                follower_positions = get_positions()

                for master in master_positions:

                    if master["status"] != "Filled":
                        continue

                    ltp = fetch_ltp(
                        market_xt,
                        2,
                        master["instrument_id"]
                    )

                    if ltp is None:
                        continue

                    update_master_ltp(
                        master["app_order_id"],
                        ltp
                    )

                    side = master["side"].upper()

                    sl = master.get("sl")
                    target = master.get("target")

                    exit_required = False

                    if side == "BUY":

                        if target and ltp >= target:
                            exit_required = True

                        elif sl and ltp <= sl:
                            exit_required = True

                    else:

                        if target and ltp <= target:
                            exit_required = True

                        elif sl and ltp >= sl:
                            exit_required = True

                    if not exit_required:
                        continue

                    log_program_event(
                        "Master Exit Triggered",
                        details={
                            "master_order_id": master["app_order_id"],
                            "symbol": master["symbol"],
                            "ltp": ltp
                        }
                    )

                    for follower in follower_positions:

                        if (
                            follower["master_order_id"]
                            !=
                            master["app_order_id"]
                        ):
                            continue

                        exit_position(
                            follower,
                            follower_sessions
                        )

                    update_master_position(
                        master["app_order_id"],
                        status="Closed"
                    )

                time.sleep(2)

            except Exception as e:

                log_program_event(
                    "Position Monitor Error",
                    details={
                        "error": str(e)
                    }
                )

                time.sleep(2)

    threading.Thread(
        target=run,
        daemon=True
    ).start()
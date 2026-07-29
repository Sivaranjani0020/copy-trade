"""
copy_trading_service.py

Initializes the copy trading service.

Responsibilities:
- Log in all enabled follower clients.
- Log in the master trading account.
- Download the latest master contract data.
- Start the master socket listener.

This module only performs startup tasks. Once the socket starts,
it continuously listens for master orders and copies them to the
enabled follower clients.
"""

from services.client_manager import login_clients
from helper_funct.client_login import login_xts
from helper_funct.client_master_download import load_master
from helper_funct.master_client import get_master_client
from services.socket_listener import start_socket
from services.logger import log_program_event


def start_copy_trading():
    """
    Starts the copy trading service.
    """

    # Login all enabled follower clients
    follower_sessions = login_clients()

    if not follower_sessions:
        log_program_event(
            "No enabled follower clients",
            details={}
        )
        return

    # Login master client
    master_client = get_master_client()
    print("MASTER CLIENT:", master_client)

    master_session = login_xts(master_client)
    print("MASTER SESSION:", master_session)

    # Download latest master contract
    master_df = load_master(master_session["Market_Xt"])

    # Start listening for master orders
    start_socket(
        master_session,
        follower_sessions,
        master_df
    )

    log_program_event(
        "Copy trading service started",
        details={
            "master": master_client,
            "followers": list(follower_sessions.keys())
        }
    )


if __name__ == "__main__":
    start_copy_trading()
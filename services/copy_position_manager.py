"""
copy_position_manager.py

Maintains only COPY TRADING positions.

This module is the single source of truth for
all follower positions.
"""

from threading import Lock

_positions = []

_position_lock = Lock()


def add_position(position):
    """
    Add a newly filled follower position.
    """

    with _position_lock:

        # Prevent duplicate positions
        for existing in _positions:

            if str(existing["app_order_id"]) == str(position["app_order_id"]):
                return

        _positions.append(position)


def get_positions():
    """
    Return all copy trading positions.
    """

    with _position_lock:
        return list(_positions)


def update_position(app_order_id, **kwargs):
    """
    Update an existing position.
    """

    with _position_lock:

        for position in _positions:

            if str(position["app_order_id"]) == str(app_order_id):

                position.update(kwargs)
                return


def close_position(client_id, symbol):
    """
    Close an open position for the given client and symbol.
    """

    with _position_lock:

        for position in _positions:

            if (
                position["client_id"] == client_id
                and position["symbol"] == symbol
                and position["status"] == "Open"
            ):

                position["qty"] = 0
                position["side"] = "-"
                position["status"] = "Closed"

                return
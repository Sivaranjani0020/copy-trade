"""
position_manager.py

Stores all follower orders in memory.

Responsibilities:
- Store copied follower orders.
- Prevent duplicate orders.
- Return follower orders for the dashboard.
- Return selected orders for manual square-off.

This module does not calculate P&L, LTP, stop-loss,
target or monitor positions.
"""

from threading import Lock


# Stores all follower orders
_positions = []

# Prevents race conditions
_position_lock = Lock()


def add_position(position):
    """
    Store a follower order.
    """

    with _position_lock:

        position.setdefault("status", "PendingNew")

        for existing in _positions:

            if (
                existing["client_id"] == position["client_id"]
                and
                str(existing["app_order_id"]) == str(position["app_order_id"])
            ):
                return

        _positions.append(position)


def get_positions():
    """
    Return all follower orders.
    """

    with _position_lock:
        return list(_positions)


def get_position(client_id, app_order_id):
    """
    Return a single follower order.
    """

    with _position_lock:

        for position in _positions:

            if (
                position["client_id"] == client_id
                and
                str(position["app_order_id"]) == str(app_order_id)
            ):
                return position

    return None


def update_status(client_id, app_order_id, status):
    """
    Update follower order status.
    """

    with _position_lock:

        for position in _positions:

            if (
                position["client_id"] == client_id
                and
                str(position["app_order_id"]) == str(app_order_id)
            ):

                position["status"] = status
                return


def get_selected_positions(selected_orders):
    """
    Return follower orders selected for Square Off.

    selected_orders format:

    [
        {
            "client_id": "...",
            "app_order_id": "..."
        }
    ]
    """

    selected = []

    with _position_lock:

        for order in selected_orders:

            position = get_position(
                order["client_id"],
                order["app_order_id"]
            )

            if position:
                selected.append(position)

    return selected


def remove_position(client_id, app_order_id):
    """
    Remove a follower order after it is completely closed.
    """

    global _positions

    with _position_lock:

        _positions = [

            position

            for position in _positions

            if not (

                position["client_id"] == client_id

                and

                str(position["app_order_id"]) == str(app_order_id)

            )

        ]
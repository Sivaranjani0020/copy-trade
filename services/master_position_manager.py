"""
master_position_manager.py

Stores all master orders received from the socket.

Responsibilities:
- Store master orders.
- Update existing master orders.
- Prevent duplicate orders.
- Provide master orders for the dashboard.

This module does not monitor positions,
calculate P&L or track stop-loss/target.
"""

from threading import Lock


# Stores all master orders
_master_positions = []

# Prevents race conditions
_master_lock = Lock()


def add_master_position(position):
    """
    Store a new master order.
    """

    with _master_lock:

        for existing in _master_positions:

            if str(existing["app_order_id"]) == str(position["app_order_id"]):
                return

        position.setdefault("status", "PendingNew")

        _master_positions.append(position)


def get_master_positions():
    """
    Return all master orders.
    """

    with _master_lock:
        return list(_master_positions)


def get_master_position(app_order_id):
    """
    Return a single master order.
    """

    with _master_lock:

        for position in _master_positions:

            if str(position["app_order_id"]) == str(app_order_id):
                return position

    return None


def update_master_position(app_order_id, **kwargs):
    """
    Update an existing master order.
    """

    with _master_lock:

        for position in _master_positions:

            if str(position["app_order_id"]) == str(app_order_id):

                position.update(kwargs)

                return


def remove_master_position(app_order_id):
    """
    Remove a master order.
    """

    global _master_positions

    with _master_lock:

        _master_positions = [

            position

            for position in _master_positions

            if str(position["app_order_id"]) != str(app_order_id)

        ]


def update_master_order(order):
    """
    Create or update a master order from websocket events.
    """

    app_order_id = order.get("AppOrderID")

    position = get_master_position(app_order_id)

    if position is None:

        add_master_position({

            "app_order_id": app_order_id,

            "symbol": order.get("TradingSymbol"),

            "side": order.get("OrderSide"),

            "qty": order.get("OrderQuantity"),

            "entry_price": (
                order.get("OrderAverageTradedPriceAPI")
                or order.get("OrderPrice")
            ),

            "status": order.get("OrderStatus"),

            "instrument_id": order.get("ExchangeInstrumentID")

        })

    else:

        update_master_position(

            app_order_id,

            status=order.get("OrderStatus"),

            entry_price=(
                order.get("OrderAverageTradedPriceAPI")
                or order.get("OrderPrice")
            )

        )
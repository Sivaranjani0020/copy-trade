"""
master_copy_position_manager.py

Maintains only MASTER positions.

Single source of truth for all master positions.
"""

from threading import Lock

_positions = []

_position_lock = Lock()


def add_position(position):
    """
    Add a new master position.
    Prevent duplicate AppOrderID.
    """

    with _position_lock:

        for existing in _positions:

            if str(existing["app_order_id"]) == str(position["app_order_id"]):
                return

        _positions.append(position)


def get_positions():
    """
    Return all master positions.
    """

    with _position_lock:
        return list(_positions)


def close_position(symbol):
    """
    Close the currently open position for this symbol.
    """

    with _position_lock:

        for position in reversed(_positions):

            if (
                position["symbol"] == symbol
                and position["status"] == "Open"
            ):

                position["status"] = "Closed"

                return True

    return False


def process_master_fill(order):
    """
    Called whenever a master order becomes FILLED.

    BUY:
        - closes existing SELL position
        - otherwise opens BUY position

    SELL:
        - closes existing BUY position
        - otherwise opens SELL position
    """

    symbol = order["TradingSymbol"]
    side = order["OrderSide"].upper()

    closed = close_position(symbol)

    if closed:
        return

    add_position({

        "app_order_id": order["AppOrderID"],

        "instrument_id": order["ExchangeInstrumentID"],

        "symbol": symbol,

        "side": side,

        "qty": order["OrderQuantity"],

        "product": order["ProductType"],

        "entry_price": (
            order.get("OrderAverageTradedPriceAPI")
            or order.get("OrderPrice")
        ),

        "ltp": 0,

        "pnl": 0,

        "status": "Open"

    })
    print("Added/Updated Master Position")
    print(_positions)
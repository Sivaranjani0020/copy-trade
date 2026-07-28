# from services.logger import log_program_event
# from helper_funct.client_master_download import get_multiplier_by_token
# from helper_funct.client_order_funct import place_market_order
# from services.position_manager import get_positions, add_position
#
# print(get_positions())
#
# def copy_order(order, follower_sessions, master_df):
#     """
#     Handles copying a master order to follower clients.
#     """
#
#     log_program_event(
#         "Master order received",
#         details={
#             "client_id": order.get("ClientID"),
#             "symbol": order.get("TradingSymbol"),
#             "side": order.get("OrderSide"),
#             "status": order.get("OrderStatus"),
#             "quantity": order.get("OrderQuantity")
#         }
#     )
#
#     print("\n========== COPY EXECUTOR ==========")
#
#     if order.get("OrderUniqueIdentifier") == "COPY_ORDER":
#         print("Ignoring copied order")
#         return
#
#     # Copy only newly placed orders
#     # print("Master order filled. Copying to followers...")
#     print("New master order received.")
#     print("Master order filled. Copying to followers...")
#
#     master_order_id = order.get("AppOrderID")
#     # Extract required order details
#     exchange_segment = {
#         "NSECM": 1,
#         "NSEFO": 2,
#         "BSECM": 11,
#         "BSEFO": 12
#     }.get(order.get("ExchangeSegment"))
#     instrument_id = order.get("ExchangeInstrumentID")
#     side = order.get("OrderSide")
#     order_type = order.get("OrderType")
#     product_type = order.get("ProductType")
#     price = order.get("OrderPrice")
#     master_qty = order.get("OrderQuantity")
#     symbol = order.get("TradingSymbol")
#
#     sl = order.get("StopLoss")
#     target = order.get("Target")
#     multiplier = get_multiplier_by_token(master_df, instrument_id)
#     master_lots = int(master_qty) // multiplier
#
#     print(f"Multiplier  : {multiplier}")
#     print(f"Master Lots : {master_lots}")
#     print(f"Symbol      : {symbol}")
#     print(f"Instrument  : {instrument_id}")
#     print(f"Side        : {side}")
#     print(f"Order Type  : {order_type}")
#     print(f"Product Type: {product_type}")
#     print(f"Price       : {price}")
#     print(f"Master Qty  : {master_qty}")
#
#     for client_id, session in follower_sessions.items():
#         client_lots = session["lots"]
#
#         client_qty = client_lots * multiplier
#
#         print("\n------------ FOLLOWER ------------")
#         print(f"Client ID    : {client_id}")
#         print(f"Follower Lots: {client_lots}")
#         print(f"Order Qty    : {client_qty}")
#
#         interactive_xt = session["Interactive_Xt"]
#
#         response = place_market_order(
#             bt=interactive_xt,
#             ins_token=instrument_id,
#             cl_id=client_id,
#             qty=client_qty,
#             side=side
#         )
#
#         print(response)
#
#         if response["type"] == "success":
#             add_position({
#                 "master_order_id": master_order_id,
#                 "client_id": client_id,
#                 "app_order_id": response["result"]["AppOrderID"],
#
#                 "exchange_segment": exchange_segment,
#                 "instrument_id": instrument_id,
#
#                 "symbol": symbol,
#                 "side": side,
#
#                 "qty": client_qty,
#
#                 "entry_price": price,
#                 "ltp": price,
#
#                 "sl": sl,
#                 "target": target,
#
#                 "pnl": 0,
#
#                 "status": "PendingNew"
#             })

"""
copy_executor.py

Copies every FILLED master order to all enabled follower clients.

Responsibilities:
- Ignore already copied orders.
- Calculate follower order quantity based on configured lots.
- Place MARKET orders for enabled followers.
- Store follower orders for dashboard display.

This module does not handle stop-loss, target,
position monitoring or exit management.
"""

from services.logger import log_program_event
from helper_funct.client_master_download import (
    get_multiplier_by_token,
    get_tick_size_by_token
)
from helper_funct.client_order_funct import place_market_order, place_limit_order
from services.position_manager import (
    add_position,
    get_positions
)
from services.order_log_manager import check_follower_order, save_follower_order

def copy_order(order, socket_client):
    """
    Copies a filled master order to all enabled follower clients.
    """

    # Ignore copied follower orders
    if str(order.get("OrderUniqueIdentifier", "")).startswith("COPY_ORDER"):
        return

    # Copy only filled orders
    if order.get("OrderStatus") != "Filled":
        return

    follower_sessions = socket_client.follower_sessions
    master_df = socket_client.master_df

    master_order_id = order.get("AppOrderID")

    # Prevent duplicate copying
    for position in get_positions():

        if str(position["master_order_id"]) == str(master_order_id):
            return

    instrument_id = order.get("ExchangeInstrumentID")
    symbol = order.get("TradingSymbol")
    side = order.get("OrderSide").upper()

    entry_price = (
        order.get("OrderAverageTradedPriceAPI")
        or order.get("OrderPrice")
    )

    multiplier = get_multiplier_by_token(
        master_df,
        instrument_id
    )

    tick_size = get_tick_size_by_token(
        master_df,
        instrument_id
    )

    log_program_event(
        "Copying master order",
        details={
            "order_id": master_order_id,
            "symbol": symbol,
            "side": side
        }
    )

    for client_id, session in follower_sessions.items():

        print("\n========== FOLLOWER ==========")
        print("Client:", client_id)
        print("Lots:", session["lots"])

        client_lots = session["lots"]
        client_qty = client_lots * multiplier

        interactive_xt = session["Interactive_Xt"]
        print("Instrument:", instrument_id)
        print("Qty:", client_qty)
        print("Side:", side)
        print("Sending market order...")
        if side == "BUY":
            limit_price = float(entry_price) * 1.04
        else:
            limit_price = float(entry_price) * 0.96

        # Round to nearest valid tick size
        limit_price = round(limit_price / tick_size) * tick_size
        limit_price = round(limit_price, 2)

        print("Entry Price :", entry_price)
        print("Limit Price :", limit_price)

        response = place_limit_order(
            bt=interactive_xt,
            ins_token=instrument_id,
            cl_id=client_id,
            qty=client_qty,
            lmt_price=limit_price,
            side=side
        )
        print("Market Order Response:")
        print(response)
        if response["type"] != "success":
            print("Follower order FAILED")
            print(response)
            continue

        result = response["result"]

        save_follower_order(
            master_order_id=master_order_id,
            client_id=client_id,
            app_order_id=result["AppOrderID"],
            symbol=symbol,
            side=side,
            qty=client_qty,
            entry_price=entry_price,
            status=result.get("OrderStatus", "PendingNew")
        )
        add_position({

            "master_order_id": master_order_id,

            "client_id": client_id,

            "app_order_id": result["AppOrderID"],

            "instrument_id": instrument_id,

            "symbol": symbol,

            "side": side,

            "qty": client_qty,

            "entry_price": entry_price,

            "status": result.get(
                "OrderStatus",
                "PendingNew"
            )

        })
        check_follower_order(
            interactive_xt,
            master_order_id,
            client_id,
            result["AppOrderID"],side
        )
        log_program_event(
            "Follower order placed",
            details={
                "client_id": client_id,
                "order_id": result["AppOrderID"],
                "symbol": symbol,
                "qty": client_qty
            }
        )
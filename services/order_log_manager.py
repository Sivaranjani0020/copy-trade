import supabase
from config.settings import SUPABASE_URL, SUPABASE_KEY
from services.copy_position_manager import add_position as add_copy_position, close_position
supabase_client = supabase.create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def save_follower_order(
    master_order_id,
    client_id,
    app_order_id,
    symbol,
    side,
    qty,
    entry_price,
    status
):

    supabase_client.table("order_logs").insert({
        "master_order_id": master_order_id,
        "client_id": client_id,
        "app_order_id": app_order_id,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "entry_price": entry_price,
        "status": status
    }).execute()

def update_follower_order_status(app_order_id, status):

    supabase_client.table("order_logs").update({

        "status": status

    }).eq(

        "app_order_id",
        app_order_id

    ).execute()

import time

# from services.order_log_manager import update_follower_order_status
from services.position_manager import get_positions


def check_follower_order(
    interactive_xt,
    master_order_id,
    client_id,
    app_order_id, side
):

    for _ in range(2):

        time.sleep(2)

        response = interactive_xt.get_order_book()

        if response["type"] != "success":
            continue

        orders = response["result"]

        for order in orders:

            if str(order["AppOrderID"]) == str(app_order_id):

                status = order["OrderStatus"]

                update_follower_order_status(
                    app_order_id,
                    status
                )
                if status == "Filled":

                    if order["OrderSide"].upper() == "BUY":

                        add_copy_position({

                            "master_order_id": master_order_id,

                            "client_id": client_id,

                            "app_order_id": app_order_id,

                            "instrument_id": order["ExchangeInstrumentID"],

                            "symbol": order["TradingSymbol"],

                            "side": order["OrderSide"],

                            "product": order["ProductType"],

                            "qty": order["OrderQuantity"],

                            "entry_price": order["OrderAverageTradedPrice"],

                            "ltp": 0,

                            "pnl": 0,

                            "status": "Open"

                        })

                    else:

                        close_position(
                            client_id,
                            order["TradingSymbol"]
                        )
                for position in get_positions():

                    if str(position["app_order_id"]) == str(app_order_id):

                        position["status"] = status

                break
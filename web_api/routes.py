"""
routes.py

Flask routes for the Copy Trading web application.

Responsibilities:
- Display all trading clients.
- Enable or disable follower clients.
- Update follower lot sizes.
- Login enabled follower clients.
- Display master and follower orders.
- Provide live dashboard data.
- Square off selected follower orders.

This module only handles the web interface and delegates
all trading operations to the service layer.
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify

from services.client_manager import login_clients
from services.logger import log_program_event
from services.position_manager import (
    get_positions,
    get_selected_positions
)
from config.settings import SUPABASE_URL, SUPABASE_KEY
import supabase
from services.master_position_manager import get_master_positions
from services.copy_position_manager import get_positions as get_copy_positions
from helper_funct.client_market_details import fetch_ltp
import services.socket_listener as socket_listener
from services.master_copy_position_manager import (
    get_positions as get_master_copy_positions
)
from services.exit_manager import exit_position
supabase_client = supabase.create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


app = Flask(__name__)


# -------------------------------
# Global sessions
# -------------------------------

sessions = {}

# Master contract dataframe
# master_df = None


# -------------------------------
# Position Manager
# We will connect this after you send the file
# -------------------------------

# from services.position_manager import position_manager



# -------------------------------
# 1. Client Selection Page
# -------------------------------

@app.route("/")
def index():

    clients = (
        supabase_client
        .table("xt_login_credentials")
        .select("client_id")
        .execute()
        .data
    )


    enabled_clients = (
        supabase_client
        .table("enabled_clients")
        .select("client_id, enabled_flag, lots")
        .execute()
        .data
    )


    enabled_set = {
        row["client_id"]
        for row in enabled_clients
        if row["enabled_flag"]
    }


    lots_map = {
        row["client_id"]: row.get("lots", 1)
        for row in enabled_clients
    }


    for client in clients:
        client["lots"] = lots_map.get(
            client["client_id"],
            1
        )


    log_program_event(
        "Client list loaded",
        details={
            "count": len(clients)
        }
    )


    return render_template(
        "index.html",
        clients=clients,
        enabled_set=enabled_set
    )



# -------------------------------
# 2. Enable / Disable Clients
# -------------------------------

@app.route("/toggle_client", methods=["POST"])
def toggle_client():

    client_id = request.form["client_id"]

    enabled = (
        request.form.get("enabled")
        == "true"
    )


    supabase_client.table("enabled_clients")\
        .update(
            {
                "enabled_flag": enabled
            }
        )\
        .eq(
            "client_id",
            client_id
        )\
        .execute()


    log_program_event(
        "Client toggled",
        details={
            "client_id": client_id,
            "enabled": enabled
        }
    )


    return "", 200




# -------------------------------
# 3. Update Lots
# -------------------------------

@app.route("/update_lots", methods=["POST"])
def update_lots():

    client_id = request.form["client_id"]

    lots = int(
        request.form["lots"]
    )


    if lots < 1:
        lots = 1


    supabase_client.table("enabled_clients")\
        .update(
            {
                "lots": lots
            }
        )\
        .eq(
            "client_id",
            client_id
        )\
        .execute()


    log_program_event(
        "Lots updated",
        details={
            "client_id": client_id,
            "lots": lots
        }
    )


    return "", 200




# -------------------------------
# 4. Login Enabled Clients
# -------------------------------

@app.route("/login", methods=["POST"])
def login_clients_route():

    global sessions

    enabled_clients = (
        supabase_client
        .table("enabled_clients")
        .select("client_id, lots")
        .eq("enabled_flag", True)
        .execute()
    )

    sessions = login_clients(enabled_clients.data)
    print("SESSIONS KEYS:", sessions.keys())
    print("SESSIONS:", sessions)

    from services.socket_listener import socket_client

    if socket_client:
        socket_client.follower_sessions = sessions
        print("Follower sessions updated in socket")

    log_program_event(
        "Clients logged in",
        details={
            "clients": list(sessions.keys())
        }
    )

    return redirect(url_for("dashboard"))

# -------------------------------
# 5. Dashboard
# -------------------------------

@app.route("/dashboard")
def dashboard():

    master_positions = get_master_positions()
    positions = get_positions()

    log_program_event(
        "Dashboard viewed",
        details={
            "clients": list(sessions.keys())
        }
    )

    return render_template(
        "dashboard.html",
        master_positions=master_positions,
        positions=positions
    )


# -------------------------------
# 6. Positions API
# Dashboard will call this every 2 sec
# -------------------------------

# @app.route("/positions-data")
# def positions_data():
#
#     return jsonify({
#         "master_positions": get_master_positions(),
#         "positions": get_positions()
#     })
@app.route("/positions-data")
def positions_data():

    master = get_master_positions()
    follower = get_positions()

    print("\n========== POSITIONS API ==========")
    print(master)
    print("==================================\n")

    return jsonify({
        "master_positions": master,
        "positions": follower
    })

@app.route("/copy-positions")
def copy_positions():
    positions = get_copy_positions()

    for pos in positions:
        if pos["status"] != "Open":
            continue

        session = sessions.get(pos["client_id"])
        if not session or "Market_Xt" not in session:
            continue

        market_xt = session["Market_Xt"]
        ltp = fetch_ltp(market_xt, 2, pos["instrument_id"])
        if ltp is None:
            continue

        pos["ltp"] = ltp

        if pos["side"].upper() == "BUY":
            pos["pnl"] = round((ltp - float(pos["entry_price"])) * int(pos["qty"]), 2)
        else:
            pos["pnl"] = round((float(pos["entry_price"]) - ltp) * int(pos["qty"]), 2)

    return jsonify(positions)


@app.route("/master-copy-positions")
def master_copy_positions():
    positions = get_master_copy_positions()
    print("MASTER ROUTE")

    # Use sessions instead of relying on socket_listener
    master_session = sessions.get("master")  # replace "master" with your actual master client_id
    if not master_session or "Market_Xt" not in master_session:
        return jsonify({"status": "failed", "message": "Master Market_Xt not initialized"})

    market_xt = master_session["Market_Xt"]

    for position in positions:
        if position["status"] != "Open":
            continue

        ltp = fetch_ltp(market_xt, 2, position["instrument_id"])
        if ltp is None:
            continue

        position["ltp"] = ltp
        if position["side"].upper() == "BUY":
            position["pnl"] = round((ltp - float(position["entry_price"])) * int(position["qty"]), 2)
        else:
            position["pnl"] = round((float(position["entry_price"]) - ltp) * int(position["qty"]), 2)

    return jsonify(positions)

# -------------------------------
# 7. Cancel Selected Positions
# -------------------------------

@app.route("/cancel/<client_id>/<instrument_id>", methods=["POST"])
def cancel_position(client_id, instrument_id):
    positions = get_positions()
    position = next(
        (p for p in positions if p["client_id"] == client_id and str(p["instrument_id"]) == str(instrument_id)),
        None
    )
    if not position:
        return jsonify({"status": "failed", "message": "Position not found"})

    response = exit_position(position, sessions)

    log_program_event(
        "Position cancelled",
        details={"client_id": client_id, "instrument_id": instrument_id, "response": response}
    )

    return jsonify({"status": "completed", "response": response})


# -------------------------------
# Startup
# -------------------------------

if __name__ == "__main__":

    log_program_event(
        "Web app started",
        details={}
    )


    app.run(
        debug=True
    )
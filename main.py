# """
# main.py
# Entry point for trading automation project.
# Responsibilities:
# - Launch the Flask web interface.
# - Web interface handles:
#     - Enable/disable clients (xt_login_credentials + enabled_clients).
#     - Perform login using services/client_manager.py.
#     - Accept research calls via web_app.
#     - Pass parsed calls to services/order_orchestrator.py.
#     - Start services/monitor.py for SL/Target exits.
#     - Log all actions in Supabase (program_logs + order_logs).
# """
#
# from web_api.routes import app
#
# def main():
#     """
#     Starts the Flask web interface.
#     All backend actions (login, call parsing, order execution, monitoring)
#     are triggered by routes inside web_app/routes.py.
#     """
#     app.run(
#         debug=True,       # shows errors in browser during development
#         host="0.0.0.0",   # accessible from local network if needed
#         port=5000
#     )
#
# if __name__ == "__main__":
#     main()

"""
main.py
Entry point for trading automation project.
"""

from threading import Thread

from web_api.routes import app
from services.copy_trading_service import start_copy_trading


def main():

    # Start copy trading service in background
    Thread(
        target=start_copy_trading,
        daemon=True
    ).start()

    # Start Flask
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
        use_reloader=False
    )


if __name__ == "__main__":
    main()
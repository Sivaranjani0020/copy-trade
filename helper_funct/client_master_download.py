"""
client_master_download.py
Handles daily master contract download and lookup.
- Download master once per day (before market opens).
- Save to master_data.csv.
- Load from CSV for all lookups.
"""

import os
import pandas as pd
from datetime import datetime

MASTER_FILE = "master_data.csv"
MASTER_DATE_FILE = "master_date.txt"

COLUMNS = [
    "ExchangeSegment", "Token", "LotSize", "Symbol",
    "DisplayName", "InstrumentType", "Series", "ISIN",
    "LastTradedPrice", "Change", "OpenInterest", "TickSize",
    "Multiplier", "Decimals", "UniqueId", "Underlying",
    "Expiry", "Strike", "OptionType", "Description",
    "Active", "Tradable", "SymbolName"
]

def download_master(market_xt):
    """
    Download master contracts from API and save to CSV.
    """
    resp = market_xt.get_master(exchangeSegmentList=["NSEFO" or "NFO"])
    if resp.get("type") != "success":
        raise Exception("Master download failed")

    result_data = resp["result"]
    rows = result_data.strip().split("\n")
    parsed = [row.split("|") for row in rows]
    parsed = [row for row in parsed if len(row) == len(COLUMNS)]

    df = pd.DataFrame(parsed, columns=COLUMNS)
    df["Expiry"] = pd.to_datetime(df["Expiry"], errors="coerce")
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")

    df.to_csv(MASTER_FILE, index=False)
    print(f"Master data saved at: {os.path.abspath(MASTER_FILE)}")

    # Save today’s date marker
    with open(MASTER_DATE_FILE, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))
    print(f"Master date marker saved at: {os.path.abspath(MASTER_DATE_FILE)}")

    return df

def load_master(market_xt=None):
    """
    Load master contracts.
    - If file missing or outdated, download fresh.
    - Otherwise, load from CSV.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # If no file or outdated → download fresh
    if not os.path.exists(MASTER_FILE) or not os.path.exists(MASTER_DATE_FILE):
        if not market_xt:
            raise FileNotFoundError("Master file missing and no market_xt provided")
        return download_master(market_xt)

    with open(MASTER_DATE_FILE, "r") as f:
        saved_date = f.read().strip()

    if saved_date != today:
        if not market_xt:
            raise RuntimeError("Master outdated and no market_xt provided")
        return download_master(market_xt)

    # Load from CSV
    df = pd.read_csv(MASTER_FILE)
    df["Expiry"] = pd.to_datetime(df["Expiry"], errors="coerce")
    df["Strike"] = pd.to_numeric(df["Strike"], errors="coerce")
    print(f"Master data saved at {os.path.abspath(MASTER_FILE)} with {len(df)} rows")

    return df

import pandas as pd

def get_option_contract_by_date(df, symbol, strike, callput, expiry_date):
    """
    Resolve option contract by symbol, strike, call/put, and expiry date.
    Returns a filtered DataFrame.
    """
    # Handle option type flexibly
    if isinstance(callput, str):
        option_type = 3 if callput.upper() == "CE" else 4
    else:
        option_type = int(callput)

    # Filter contracts
    filtered = df[
        (df["Symbol"].astype(str).str.upper() == symbol.upper()) &
        (df["Strike"] == float(strike)) &
        (df["OptionType"] == option_type)
    ].copy()

    if filtered.empty:
        return None

    # Normalize expiry comparison
    filtered["ExpiryDate"] = pd.to_datetime(filtered["Expiry"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M")
    filtered = filtered[filtered["ExpiryDate"] == expiry_date]

    if filtered.empty:
        return None

    return filtered  # return DataFrame

def get_multiplier_by_token(df, token):
    """
    Returns the market lot size (Multiplier) for the given instrument token.
    """
    contract = df[df["Token"].astype(int) == int(token)]

    if contract.empty:
        raise Exception(f"Token {token} not found in master contract.")

    return int(contract.iloc[0]["Multiplier"])

def get_tick_size_by_token(df, token):
    """
    Returns TickSize for the given instrument token.
    """
    contract = df[
        df["Token"].astype(int) == int(token)
    ]

    if contract.empty:
        raise Exception(f"Token {token} not found in master contract.")

    return float(contract.iloc[0]["TickSize"])

# def get_option_contract_by_date(df, symbol, strike, callput, expiry_date):
#     """
#     Resolve option contract by symbol, strike, call/put, and expiry date.
#     """
#     option_type = "3" if callput.upper() == "CE" else "4"
#
#     filtered = df[
#         (df["Symbol"].astype(str).str.upper() == symbol.upper()) &
#         (df["Strike"] == float(strike)) &
#         (df["OptionType"].astype(str) == option_type)
#     ].copy()
#
#     if filtered.empty:
#         raise Exception(f"No contract found for {symbol} {strike} {callput}")
#
#     filtered["ExpiryDate"] = filtered["Expiry"].dt.strftime("%Y-%m-%d")
#     filtered = filtered[filtered["ExpiryDate"] == expiry_date]
#
#     if filtered.empty:
#         raise Exception(f"No contract found for expiry {expiry_date}")
#
#     contract = filtered.iloc[0]
#     return {
#         "token": int(contract["Token"]),
#         "lot_size": int(contract["LotSize"]),
#         "multiplier": int(contract["Multiplier"]),
#         "expiry": str(contract["Expiry"]),
#         "symbol": contract["Symbol"]
#     }

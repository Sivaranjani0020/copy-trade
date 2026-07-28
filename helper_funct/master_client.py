import supabase
from config.settings import SUPABASE_URL, SUPABASE_KEY

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def get_master_client():
    response = (
        supabase_client
        .table("master_client")
        .select("client_id")
        .eq("enabled", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError("No enabled master client found.")

    return response.data[0]["client_id"]
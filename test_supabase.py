import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

def test_connection():
    if not URL or not KEY or "your-project-url" in URL:
        print("❌ Error: Supabase URL or Key not set correctly in .env")
        return

    try:
        supabase = create_client(URL, KEY)
        # Test basic connection
        supabase.table("users").select("id", count="exact").limit(1).execute()
        print("✅ Successfully connected to Supabase!")
        
        # Check tables
        tables = ["users", "projects", "project_versions"]
        for table in tables:
            try:
                supabase.table(table).select("count", count="exact").limit(1).execute()
                print(f"✅ Table '{table}' found.")
            except Exception as e:
                print(f"❌ Table '{table}' error: {e}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    test_connection()

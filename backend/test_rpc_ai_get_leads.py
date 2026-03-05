"""
Test ai_get_leads RPC function directly
"""
import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.supabase import get_supabase_client
from app.config import settings

async def test_ai_get_leads():
    """Test ai_get_leads RPC function"""
    try:
        supabase = get_supabase_client()
        
        # Test user ID (replace with actual user ID)
        user_id = "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8"
        
        print(f"🧪 Testing ai_get_leads RPC function...")
        print(f"   User ID: {user_id}")
        print(f"   Date filter: today")
        
        from datetime import date
        today = str(date.today())
        
        # Test 1: Get leads for today
        print(f"\n📞 Test 1: Get leads for today ({today})")
        result = supabase.rpc(
            "ai_get_leads",
            {
                "p_user_id": user_id,
                "p_filters": {},
                "p_date_from": today,
                "p_date_to": today,
                "p_limit": 100,
                "p_user_role": "staff"
            }
        ).execute()
        
        print(f"   Response: {result.data}")
        print(f"   Type: {type(result.data)}")
        
        # Test 2: Get all leads (no date filter)
        print(f"\n📞 Test 2: Get all leads (no date filter)")
        result2 = supabase.rpc(
            "ai_get_leads",
            {
                "p_user_id": user_id,
                "p_filters": {},
                "p_date_from": None,
                "p_date_to": None,
                "p_limit": 10,
                "p_user_role": "staff"
            }
        ).execute()
        
        print(f"   Response: {result2.data}")
        
        # Check if RPC function exists
        print(f"\n✅ RPC function exists and responds")
        if result.data and isinstance(result.data, dict):
            if "success" in result.data:
                print(f"   Success: {result.data.get('success')}")
            if "data" in result.data:
                print(f"   Data keys: {result.data.get('data', {}).keys()}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's a function not found error
        error_str = str(e)
        if "function" in error_str.lower() and "does not exist" in error_str.lower():
            print(f"\n⚠️  RPC function 'ai_get_leads' might not exist in database")
            print(f"   Please run migration: 20250117000003_fix_ai_get_leads_role.sql")

if __name__ == "__main__":
    asyncio.run(test_ai_get_leads())

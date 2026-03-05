#!/usr/bin/env python3
"""
Test RPC Functions from External Script
สามารถรัน script นี้เพื่อทดสอบ RPC function จากภายนอกได้

Usage:
    python test_rpc_function.py
"""

import os
import sys
from datetime import date

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.supabase import get_supabase_client
from app.config import settings


def test_ai_get_daily_summary():
    """Test ai_get_daily_summary RPC function"""
    print("=" * 60)
    print("🧪 Testing: ai_get_daily_summary")
    print("=" * 60)
    
    try:
        supabase = get_supabase_client()
        
        # Test with different roles
        test_user_id = "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8"
        test_date = str(date.today())
        
        print(f"\n📋 Test Parameters:")
        print(f"   User ID: {test_user_id}")
        print(f"   Date: {test_date}")
        
        # Test 1: Staff role
        print(f"\n📊 Test 1: Staff Role")
        result1 = supabase.rpc(
            "ai_get_daily_summary",
            {
                "p_user_id": test_user_id,
                "p_date": test_date,
                "p_user_role": "staff"
            }
        ).execute()
        print(f"   ✅ Result: {result1.data}")
        
        # Test 2: Admin role
        print(f"\n📊 Test 2: Admin Role")
        result2 = supabase.rpc(
            "ai_get_daily_summary",
            {
                "p_user_id": test_user_id,
                "p_date": test_date,
                "p_user_role": "admin"
            }
        ).execute()
        print(f"   ✅ Result: {result2.data}")
        
        # Test 3: Default parameters
        print(f"\n📊 Test 3: Default Parameters (no role, no date)")
        result3 = supabase.rpc(
            "ai_get_daily_summary",
            {
                "p_user_id": test_user_id
            }
        ).execute()
        print(f"   ✅ Result: {result3.data}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_get_lead_status():
    """Test ai_get_lead_status RPC function"""
    print("\n" + "=" * 60)
    print("🧪 Testing: ai_get_lead_status")
    print("=" * 60)
    
    try:
        supabase = get_supabase_client()
        
        test_user_id = "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8"
        test_lead_name = "test"
        
        print(f"\n📋 Test Parameters:")
        print(f"   Lead Name: {test_lead_name}")
        print(f"   User ID: {test_user_id}")
        
        result = supabase.rpc(
            "ai_get_lead_status",
            {
                "p_lead_name": test_lead_name,
                "p_user_id": test_user_id
            }
        ).execute()
        
        print(f"\n✅ Result: {result.data}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_ai_get_team_kpi():
    """Test ai_get_team_kpi RPC function"""
    print("\n" + "=" * 60)
    print("🧪 Testing: ai_get_team_kpi")
    print("=" * 60)
    
    try:
        supabase = get_supabase_client()
        
        test_user_id = "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8"
        
        print(f"\n📋 Test Parameters:")
        print(f"   User ID: {test_user_id}")
        
        result = supabase.rpc(
            "ai_get_team_kpi",
            {
                "p_user_id": test_user_id,
                "p_team_id": None
            }
        ).execute()
        
        print(f"\n✅ Result: {result.data}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("   RPC Function Test Script")
    print("🚀" * 30 + "\n")
    
    # Test all functions
    results = []
    
    results.append(test_ai_get_daily_summary())
    results.append(test_ai_get_lead_status())
    results.append(test_ai_get_team_kpi())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"   Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("   ✅ All tests passed!")
    else:
        print("   ⚠️  Some tests failed. Check errors above.")
    print("=" * 60 + "\n")

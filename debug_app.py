#!/usr/bin/env python3
"""
Debug script to test individual components
"""

def test_imports():
    """Test if all imports work"""
    print("🧪 Testing imports...")
    
    try:
        import settings
        print("✅ settings imported successfully")
        print(f"   STRATEGY_NAME: {settings.STRATEGY_NAME}")
        print(f"   MULTI_INSTRUMENT_MODE: {settings.MULTI_INSTRUMENT_MODE}")
        if hasattr(settings, 'INSTRUMENTS'):
            print(f"   INSTRUMENTS: {settings.INSTRUMENTS}")
        if hasattr(settings, 'INSTRUMENT'):
            print(f"   INSTRUMENT: {settings.INSTRUMENT}")
    except Exception as e:
        print(f"❌ settings import failed: {e}")
        return False
    
    try:
        import backtest
        print("✅ backtest imported successfully")
    except Exception as e:
        print(f"❌ backtest import failed: {e}")
        return False
    
    try:
        import trade
        print("✅ trade imported successfully")
    except Exception as e:
        print(f"❌ trade import failed: {e}")
        return False
    
    try:
        import strategy
        print("✅ strategy imported successfully")
    except Exception as e:
        print(f"❌ strategy import failed: {e}")
        return False
    
    try:
        from strategy_selector import get_available_strategies, get_strategy_info
        print("✅ strategy_selector imported successfully")
        strategies = get_available_strategies()
        print(f"   Available strategies: {len(strategies)}")
    except Exception as e:
        print(f"❌ strategy_selector import failed: {e}")
        return False
    
    return True

def test_template_rendering():
    """Test template rendering"""
    print("\n🧪 Testing template rendering...")
    
    try:
        from fastapi.templating import Jinja2Templates
        from fastapi import Request
        
        templates = Jinja2Templates(directory="templates")
        print("✅ Templates initialized successfully")
        
        # Test if dashboard.html exists
        import os
        if os.path.exists("templates/dashboard.html"):
            print("✅ dashboard.html exists")
        else:
            print("❌ dashboard.html not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 OANDA Trading Bot - Debug Tests")
    print("=" * 50)
    
    success = True
    success &= test_imports()
    success &= test_template_rendering()
    
    if success:
        print("\n✅ All tests passed! Web app should work.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
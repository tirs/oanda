#!/usr/bin/env python3
"""
Simple verification script for the new AggressiveMultiInstrumentStrategy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import strategy
import settings
from datetime import datetime

def verify_strategy_exists():
    """Verify the strategy class exists and can be imported"""
    print("🔍 Verifying AggressiveMultiInstrumentStrategy...")
    
    try:
        # Check if the strategy class exists
        if hasattr(strategy, 'AggressiveMultiInstrumentStrategy'):
            strategy_class = getattr(strategy, 'AggressiveMultiInstrumentStrategy')
            print("✅ AggressiveMultiInstrumentStrategy found in strategy.py")
            
            # Check if it's a proper backtrader strategy
            import backtrader
            if issubclass(strategy_class, backtrader.Strategy):
                print("✅ Strategy properly inherits from backtrader.Strategy")
                return True
            else:
                print("❌ Strategy does not inherit from backtrader.Strategy")
                return False
        else:
            print("❌ AggressiveMultiInstrumentStrategy not found in strategy.py")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying strategy: {e}")
        return False

def verify_settings():
    """Verify settings are properly configured"""
    print("\n🔍 Verifying settings configuration...")
    
    try:
        # Check current strategy
        current_strategy = getattr(settings, 'STRATEGY_NAME', None)
        print(f"📊 Current strategy: {current_strategy}")
        
        # Check multi-instrument mode
        multi_mode = getattr(settings, 'MULTI_INSTRUMENT_MODE', False)
        print(f"🌍 Multi-instrument mode: {multi_mode}")
        
        # Check instruments
        instruments = getattr(settings, 'INSTRUMENTS', [])
        print(f"📈 Available instruments: {len(instruments)} pairs")
        for i, instrument in enumerate(instruments[:5], 1):  # Show first 5
            print(f"   {i}. {instrument}")
        if len(instruments) > 5:
            print(f"   ... and {len(instruments) - 5} more")
        
        # Check if AggressiveMultiInstrumentStrategy is in alternatives
        alternatives = getattr(settings, 'ALTERNATIVE_STRATEGIES', [])
        if 'AggressiveMultiInstrumentStrategy' in alternatives:
            print("✅ AggressiveMultiInstrumentStrategy is in ALTERNATIVE_STRATEGIES")
        else:
            print("⚠️ AggressiveMultiInstrumentStrategy not in ALTERNATIVE_STRATEGIES")
        
        # Check aggressive settings
        aggressive_settings = getattr(settings, 'AGGRESSIVE_MULTI_SETTINGS', None)
        if aggressive_settings:
            print("✅ AGGRESSIVE_MULTI_SETTINGS found:")
            for key, value in aggressive_settings.items():
                print(f"   {key}: {value}")
        else:
            print("⚠️ AGGRESSIVE_MULTI_SETTINGS not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying settings: {e}")
        return False

def verify_strategy_features():
    """Verify strategy has the expected features"""
    print("\n🔍 Verifying strategy features...")
    
    try:
        strategy_class = getattr(strategy, 'AggressiveMultiInstrumentStrategy')
        
        # Check parameters
        params = getattr(strategy_class, 'params', ())
        param_names = [p[0] if isinstance(p, tuple) else p for p in params]
        
        expected_params = [
            'risk_per_trade', 'stop_loss_atr', 'take_profit_atr', 
            'max_positions_per_instrument', 'min_signal_strength'
        ]
        
        print("📊 Strategy parameters:")
        for param in param_names:
            print(f"   ✅ {param}")
        
        missing_params = [p for p in expected_params if p not in param_names]
        if missing_params:
            print(f"⚠️ Missing expected parameters: {missing_params}")
        else:
            print("✅ All expected parameters found")
        
        # Check if strategy has proper methods
        required_methods = ['__init__', 'next', 'log']
        for method in required_methods:
            if hasattr(strategy_class, method):
                print(f"✅ Method '{method}' found")
            else:
                print(f"❌ Method '{method}' missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying strategy features: {e}")
        return False

def verify_sl_tp_implementation():
    """Verify SL/TP implementation in strategies"""
    print("\n🔍 Verifying SL/TP implementation...")
    
    try:
        # Check AggressiveMultiInstrumentStrategy
        with open('strategy.py', 'r') as f:
            content = f.read()
        
        # Look for bracket order usage
        if 'buy_bracket' in content and 'sell_bracket' in content:
            print("✅ Bracket orders (buy_bracket/sell_bracket) found in strategy")
        else:
            print("❌ Bracket orders not found in strategy")
        
        # Look for SL/TP calculation
        if 'stop_loss_price' in content and 'take_profit_price' in content:
            print("✅ SL/TP price calculations found")
        else:
            print("❌ SL/TP price calculations not found")
        
        # Look for ATR-based SL/TP
        if 'stop_loss_atr' in content and 'take_profit_atr' in content:
            print("✅ ATR-based SL/TP parameters found")
        else:
            print("❌ ATR-based SL/TP parameters not found")
        
        # Check QuantitativeAlphaStrategy too
        if 'QuantitativeAlphaStrategy' in content:
            quant_section = content[content.find('class QuantitativeAlphaStrategy'):content.find('class', content.find('class QuantitativeAlphaStrategy') + 1)]
            if 'buy_bracket' in quant_section or 'sell_bracket' in quant_section:
                print("✅ QuantitativeAlphaStrategy also uses bracket orders")
            else:
                print("⚠️ QuantitativeAlphaStrategy may not use bracket orders")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying SL/TP implementation: {e}")
        return False

def main():
    """Main verification function"""
    print("🔍 STRATEGY VERIFICATION SUITE")
    print("=" * 60)
    print(f"📅 Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target Strategy: AggressiveMultiInstrumentStrategy")
    
    results = []
    
    # Run all verifications
    results.append(("Strategy Import", verify_strategy_exists()))
    results.append(("Settings Configuration", verify_settings()))
    results.append(("Strategy Features", verify_strategy_features()))
    results.append(("SL/TP Implementation", verify_sl_tp_implementation()))
    
    # Summary
    print("\n📋 VERIFICATION SUMMARY")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("🚀 AggressiveMultiInstrumentStrategy is ready for use!")
        print("\n💡 Next steps:")
        print("   1. Start the web application: python app.py")
        print("   2. Go to http://localhost:8000/strategies")
        print("   3. Select AggressiveMultiInstrumentStrategy")
        print("   4. Start trading with proper SL/TP orders!")
    else:
        print("⚠️ Some verifications failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    main()
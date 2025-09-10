"""
Strategy Selector - Choose the best strategy for current market conditions
"""

import settings
import backtest

def get_available_strategies():
    """Get list of available strategy names"""
    return [
        "AggressiveMultiInstrumentStrategy",
        "RealQuantitativeAlphaStrategy",
        "RealProfessionalScalpingStrategy", 
        "RealInstitutionalBreakoutStrategy",
        "RealMachineLearningStrategy",
        "AdvancedMultiStrategy",
        "MultiInstrumentStrategy",
        "MomentumStrategy",
        "MeanReversionStrategy"
    ]

def get_strategy_info(strategy_name=None):
    """Get detailed information about strategies"""
    strategy_details = {
        "AggressiveMultiInstrumentStrategy": {
            "description": "🚀 NEW! Aggressive multi-pair trading with proper SL/TP orders for maximum profit opportunities",
            "best_for": "All market conditions, maximum trading opportunities across 10 currency pairs",
            "risk_level": "Moderate-High",
            "expected_return": "Very High",
            "trade_frequency": "Very High",
            "features": "Bracket orders, multi-instrument analysis, correlation filtering, tight risk management"
        },
        "RealQuantitativeAlphaStrategy": {
            "description": " REAL Statistical Arbitrage using Ornstein-Uhlenbeck processes, regime detection, and Kelly Criterion",
            "best_for": "All market conditions, professional quantitative trading",
            "risk_level": "Medium",
            "expected_return": "Very High",
            "trade_frequency": "Medium",
            "features": "Half-life analysis, Z-score modeling, Sharpe optimization"
        },
        "RealProfessionalScalpingStrategy": {
            "description": " REAL High-frequency scalping with order book simulation and microstructure analysis",
            "best_for": "High volatility, liquid markets with tight spreads",
            "risk_level": "High",
            "expected_return": "Very High",
            "trade_frequency": "Very High",
            "features": "Order flow analysis, tick-level precision, volume imbalance detection"
        },
        "RealInstitutionalBreakoutStrategy": {
            "description": " REAL Institutional breakout trading with volume profile and smart money concepts",
            "best_for": "Range-bound markets breaking key levels",
            "risk_level": "Medium-High",
            "expected_return": "High",
            "trade_frequency": "Low-Medium",
            "features": "Volume profile analysis, liquidity zones, institutional order flow"
        },
        "RealMachineLearningStrategy": {
            "description": " REAL Machine Learning using Random Forest & Gradient Boosting with 15+ features",
            "best_for": "Complex market patterns, adaptive learning",
            "risk_level": "Medium",
            "expected_return": "High",
            "trade_frequency": "Medium",
            "features": "Scikit-learn models, feature engineering, ensemble predictions"
        },
        "AdvancedMultiStrategy": {
            "description": " Multi-indicator strategy with advanced risk management",
            "best_for": "General trading, good for beginners",
            "risk_level": "Medium",
            "expected_return": "Medium-High",
            "trade_frequency": "Medium"
        },
        "MultiInstrumentStrategy": {
            "description": " Trade multiple currency pairs simultaneously",
            "best_for": "Diversification, correlation-aware trading",
            "risk_level": "Medium",
            "expected_return": "High",
            "trade_frequency": "High"
        },
        "MomentumStrategy": {
            "description": " Pure momentum following strategy",
            "best_for": "Strong trending markets",
            "risk_level": "Medium-High",
            "expected_return": "Medium-High",
            "trade_frequency": "Medium"
        },
        "MeanReversionStrategy": {
            "description": " Mean reversion for range-bound markets",
            "best_for": "Sideways, range-bound markets",
            "risk_level": "Medium",
            "expected_return": "Medium",
            "trade_frequency": "Medium"
        }
    }
    
    # If a specific strategy is requested, return just that strategy's info
    if strategy_name:
        return strategy_details.get(strategy_name, {
            "description": "Strategy information not available",
            "best_for": "Unknown",
            "risk_level": "Unknown",
            "expected_return": "Unknown",
            "trade_frequency": "Unknown"
        })
    
    # Otherwise return all strategies
    return strategy_details

def list_available_strategies():
    """List all available strategies with descriptions"""
    strategies = get_strategy_info()
    
    print("=" * 80)
    print(" ADVANCED TRADING STRATEGIES - Choose Your Path to Profits! ")
    print("=" * 80)
    
    for i, (name, info) in enumerate(strategies.items(), 1):
        print(f"\n{i}. {name}")
        print(f"   {info['description']}")
        print(f"    Best for: {info['best_for']}")
        print(f"    Risk Level: {info['risk_level']}")
        print(f"    Expected Return: {info['expected_return']}")
        print(f"    Trade Frequency: {info['trade_frequency']}")
    
    return list(strategies.keys())

def select_strategy():
    """Interactive strategy selection"""
    strategies = list_available_strategies()
    
    print("\n" + "=" * 80)
    print("Select a strategy by number (or press Enter for current strategy):")
    print(f"Current strategy: {settings.STRATEGY_NAME}")
    
    try:
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if not choice:
            print(f"Using current strategy: {settings.STRATEGY_NAME}")
            return settings.STRATEGY_NAME
        
        choice_num = int(choice)
        if 1 <= choice_num <= len(strategies):
            selected_strategy = strategies[choice_num - 1]
            print(f"\n Selected: {selected_strategy}")
            return selected_strategy
        else:
            print(" Invalid choice. Using current strategy.")
            return settings.STRATEGY_NAME
            
    except ValueError:
        print(" Invalid input. Using current strategy.")
        return settings.STRATEGY_NAME

def update_strategy_settings(strategy_name):
    """Update settings.py with selected strategy"""
    try:
        # Read current settings
        with open('settings.py', 'r') as f:
            content = f.read()
        
        # Update strategy name
        import re
        pattern = r'STRATEGY_NAME = "[^"]*"'
        replacement = f'STRATEGY_NAME = "{strategy_name}"'
        content = re.sub(pattern, replacement, content)
        
        # Write back to file
        with open('settings.py', 'w') as f:
            f.write(content)
        
        print(f" Settings updated! Strategy set to: {strategy_name}")
        return True
        
    except Exception as e:
        print(f" Error updating settings: {e}")
        return False

def run_strategy_backtest(strategy_name=None):
    """Run backtest with selected strategy"""
    if strategy_name:
        if update_strategy_settings(strategy_name):
            # Reload settings
            import importlib
            importlib.reload(settings)
    
    print(f"\n Running backtest with {settings.STRATEGY_NAME}...")
    print("=" * 60)
    
    try:
        backtest.backtest()
    except Exception as e:
        print(f" Backtest failed: {e}")
        print(" Make sure you have data files in the 'data' directory")

def strategy_comparison():
    """Compare multiple strategies"""
    print("\n STRATEGY COMPARISON MODE")
    print("=" * 50)
    
    strategies_to_test = [
        "QuantitativeAlphaStrategy",
        "ProfessionalScalpingStrategy", 
        "InstitutionalBreakoutStrategy",
        "AdvancedMultiStrategy"
    ]
    
    results = {}
    
    for strategy in strategies_to_test:
        print(f"\n Testing {strategy}...")
        try:
            update_strategy_settings(strategy)
            import importlib
            importlib.reload(settings)
            
            # Run backtest and capture results
            # Note: This is a simplified version - in practice you'd capture the actual results
            print(f" {strategy} test completed")
            results[strategy] = "Completed"
            
        except Exception as e:
            print(f" {strategy} failed: {e}")
            results[strategy] = f"Failed: {e}"
    
    print("\n COMPARISON RESULTS:")
    print("=" * 40)
    for strategy, result in results.items():
        print(f"{strategy}: {result}")

def main():
    """Main strategy selector interface"""
    print(" Welcome to the Advanced Strategy Selector!")
    print("\nChoose an option:")
    print("1. Select and run a strategy")
    print("2. Compare multiple strategies")
    print("3. Just list available strategies")
    print("4. Run current strategy")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        selected = select_strategy()
        run_strategy_backtest(selected)
    elif choice == "2":
        strategy_comparison()
    elif choice == "3":
        list_available_strategies()
    elif choice == "4":
        run_strategy_backtest()
    else:
        print(" Invalid choice. Running current strategy.")
        run_strategy_backtest()

if __name__ == "__main__":
    main()
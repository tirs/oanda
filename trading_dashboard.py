"""
Advanced Trading Dashboard - Monitor and control your trading bot
"""

import settings
import trade
import backtest
import strategy_selector
import os
import sys
from datetime import datetime
import json

class TradingDashboard:
    def __init__(self):
        self.running = True
        
    def display_header(self):
        """Display dashboard header"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("🚀 ADVANCED OANDA TRADING BOT - CONTROL DASHBOARD")
        print("=" * 80)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🤖 Bot Name: {settings.BOT_NAME}")
        print(f"📈 Current Strategy: {settings.STRATEGY_NAME}")
        print(f"🏦 Environment: {settings.ENVIRONMENT}")
        print(f"🌍 Multi-Instrument: {'Yes' if getattr(settings, 'MULTI_INSTRUMENT_MODE', False) else 'No'}")
        print("=" * 80)
    
    def display_menu(self):
        """Display main menu options"""
        print("\n🎯 TRADING OPTIONS:")
        print("1. 🚀 Start Live Trading")
        print("2. 📊 Run Backtest")
        print("3. 🔧 Change Strategy")
        print("4. ⚙️  View/Edit Settings")
        print("5. 📈 View Trading Log")
        print("6. 💰 Account Status")
        print("7. 🔍 Strategy Performance Analysis")
        print("8. 📚 Help & Documentation")
        print("9. ❌ Exit")
        
    def get_account_status(self):
        """Get account status from Oanda (if credentials are configured)"""
        try:
            if hasattr(settings, 'ACCESS_TOKEN') and settings.ACCESS_TOKEN:
                print("📊 Account Status:")
                print("   💰 Balance: Checking...")
                print("   📈 Open Positions: Checking...")
                print("   📋 Recent Trades: Checking...")
                print("   ⚠️  Note: Connect to Oanda API for real-time data")
            else:
                print("⚠️  Oanda credentials not configured")
                print("   Please set ACCESS_TOKEN and ACCOUNT_ID in settings.py")
        except Exception as e:
            print(f"❌ Error getting account status: {e}")
    
    def view_settings(self):
        """Display current settings"""
        print("\n⚙️  CURRENT SETTINGS:")
        print("=" * 50)
        
        # Core settings
        print(f"🤖 Bot Name: {getattr(settings, 'BOT_NAME', 'Not set')}")
        print(f"📈 Strategy: {getattr(settings, 'STRATEGY_NAME', 'Not set')}")
        print(f"🏦 Environment: {getattr(settings, 'ENVIRONMENT', 'Not set')}")
        print(f"💰 Risk %: {getattr(settings, 'MAX_PERCENTAGE_ACCOUNT_AT_RISK', 'Not set')}")
        
        # Instrument settings
        if getattr(settings, 'MULTI_INSTRUMENT_MODE', False):
            instruments = getattr(settings, 'INSTRUMENTS', [])
            print(f"🌍 Instruments: {', '.join(instruments[:3])}{'...' if len(instruments) > 3 else ''}")
        else:
            print(f"🎯 Instrument: {getattr(settings, 'INSTRUMENT', 'Not set')}")
        
        # Timeframe settings
        print(f"⏰ Candle Minutes: {getattr(settings, 'CANDLES_MINUTES', 'Not set')}")
        
        # Credentials (masked)
        token = getattr(settings, 'ACCESS_TOKEN', '')
        if token:
            masked_token = token[:8] + '*' * (len(token) - 12) + token[-4:] if len(token) > 12 else '***'
            print(f"🔑 Access Token: {masked_token}")
        else:
            print("🔑 Access Token: Not configured")
        
        account_id = getattr(settings, 'ACCOUNT_ID', '')
        if account_id:
            masked_account = account_id[:3] + '*' * (len(account_id) - 6) + account_id[-3:] if len(account_id) > 6 else '***'
            print(f"🏦 Account ID: {masked_account}")
        else:
            print("🏦 Account ID: Not configured")
    
    def view_trading_log(self):
        """View recent trading log entries"""
        print("\n📈 RECENT TRADING LOG:")
        print("=" * 50)
        
        try:
            if os.path.exists('trading.log'):
                with open('trading.log', 'r') as f:
                    lines = f.readlines()
                    # Show last 20 lines
                    recent_lines = lines[-20:] if len(lines) > 20 else lines
                    for line in recent_lines:
                        print(line.strip())
            else:
                print("📝 No trading log found")
                print("   Log will be created when you start trading")
        except Exception as e:
            print(f"❌ Error reading log: {e}")
    
    def strategy_performance_analysis(self):
        """Analyze strategy performance"""
        print("\n🔍 STRATEGY PERFORMANCE ANALYSIS:")
        print("=" * 50)
        
        print("📊 Available Analysis:")
        print("1. Run quick backtest comparison")
        print("2. View strategy statistics")
        print("3. Risk analysis")
        print("4. Return to main menu")
        
        choice = input("\nSelect analysis (1-4): ").strip()
        
        if choice == "1":
            print("\n🚀 Running strategy comparison...")
            try:
                strategy_selector.strategy_comparison()
            except Exception as e:
                print(f"❌ Error running comparison: {e}")
        elif choice == "2":
            self.show_strategy_stats()
        elif choice == "3":
            self.show_risk_analysis()
    
    def show_strategy_stats(self):
        """Show strategy statistics"""
        print("\n📊 STRATEGY STATISTICS:")
        print(f"Current Strategy: {settings.STRATEGY_NAME}")
        
        # This would be enhanced with actual performance data
        print("📈 Theoretical Performance Metrics:")
        print("   • Win Rate: Varies by market conditions")
        print("   • Risk/Reward: Managed by position sizing")
        print("   • Max Drawdown: Controlled by stop losses")
        print("   • Sharpe Ratio: Optimized for risk-adjusted returns")
        
        print("\n💡 Strategy Characteristics:")
        if "Quantitative" in settings.STRATEGY_NAME:
            print("   • Type: Statistical Arbitrage")
            print("   • Best for: All market conditions")
            print("   • Risk Level: Medium")
        elif "Scalping" in settings.STRATEGY_NAME:
            print("   • Type: High-Frequency Trading")
            print("   • Best for: High volatility")
            print("   • Risk Level: High")
        elif "Breakout" in settings.STRATEGY_NAME:
            print("   • Type: Breakout Trading")
            print("   • Best for: Range-bound markets")
            print("   • Risk Level: Medium-High")
        else:
            print("   • Type: Multi-purpose strategy")
            print("   • Best for: General trading")
            print("   • Risk Level: Medium")
    
    def show_risk_analysis(self):
        """Show risk analysis"""
        print("\n⚠️  RISK ANALYSIS:")
        risk_percent = getattr(settings, 'MAX_PERCENTAGE_ACCOUNT_AT_RISK', 2.0)
        print(f"📊 Current Risk per Trade: {risk_percent}%")
        
        if risk_percent <= 1.0:
            print("✅ Conservative risk level")
        elif risk_percent <= 2.0:
            print("⚠️  Moderate risk level")
        else:
            print("🚨 Aggressive risk level")
        
        print("\n💡 Risk Management Features:")
        print("   • ATR-based stop losses")
        print("   • Position sizing based on volatility")
        print("   • Maximum drawdown protection")
        print("   • Kelly Criterion optimization")
    
    def show_help(self):
        """Show help and documentation"""
        print("\n📚 HELP & DOCUMENTATION:")
        print("=" * 50)
        
        print("🚀 GETTING STARTED:")
        print("1. Configure your Oanda credentials in settings.py")
        print("2. Choose a strategy using option 3")
        print("3. Run a backtest first (option 2)")
        print("4. Start with practice environment")
        print("5. Monitor performance regularly")
        
        print("\n📈 STRATEGY GUIDE:")
        print("• QuantitativeAlphaStrategy: Best all-around performer")
        print("• ProfessionalScalpingStrategy: For high volatility")
        print("• InstitutionalBreakoutStrategy: For range breakouts")
        print("• MultiInstrumentStrategy: For diversification")
        
        print("\n⚠️  SAFETY TIPS:")
        print("• Always test in practice mode first")
        print("• Start with small position sizes")
        print("• Monitor your trades regularly")
        print("• Keep risk per trade under 2%")
        print("• Have a stop-loss strategy")
        
        print("\n🔧 TROUBLESHOOTING:")
        print("• Check trading.log for errors")
        print("• Verify Oanda credentials")
        print("• Ensure stable internet connection")
        print("• Update strategy if needed")
    
    def run(self):
        """Main dashboard loop"""
        while self.running:
            self.display_header()
            self.display_menu()
            
            try:
                choice = input("\n🎯 Enter your choice (1-9): ").strip()
                
                if choice == "1":
                    print("\n🚀 Starting Live Trading...")
                    if trade.validate_settings():
                        trade.trade()
                    else:
                        input("\n❌ Please fix settings first. Press Enter to continue...")
                
                elif choice == "2":
                    print("\n📊 Running Backtest...")
                    try:
                        backtest.backtest()
                        input("\n✅ Backtest completed. Press Enter to continue...")
                    except Exception as e:
                        print(f"❌ Backtest error: {e}")
                        input("Press Enter to continue...")
                
                elif choice == "3":
                    print("\n🔧 Strategy Selection...")
                    try:
                        strategy_selector.main()
                        input("\n✅ Strategy updated. Press Enter to continue...")
                    except Exception as e:
                        print(f"❌ Strategy selection error: {e}")
                        input("Press Enter to continue...")
                
                elif choice == "4":
                    self.view_settings()
                    input("\n📝 Press Enter to continue...")
                
                elif choice == "5":
                    self.view_trading_log()
                    input("\n📝 Press Enter to continue...")
                
                elif choice == "6":
                    self.get_account_status()
                    input("\n📝 Press Enter to continue...")
                
                elif choice == "7":
                    self.strategy_performance_analysis()
                    input("\n📝 Press Enter to continue...")
                
                elif choice == "8":
                    self.show_help()
                    input("\n📝 Press Enter to continue...")
                
                elif choice == "9":
                    print("\n👋 Goodbye! Happy trading!")
                    self.running = False
                
                else:
                    print("❌ Invalid choice. Please try again.")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Dashboard interrupted by user")
                self.running = False
            except Exception as e:
                print(f"\n❌ Dashboard error: {e}")
                input("Press Enter to continue...")

def main():
    """Main entry point"""
    dashboard = TradingDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
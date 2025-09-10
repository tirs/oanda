"""
Quick Setup Script for Advanced Oanda Trading Bot
"""

import os
import sys
import settings

def check_dependencies():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'backtrader',
        'btoandav20', 
        'pandas',
        'numpy',
        'talib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("✅ All dependencies installed!")
        return True

def check_data_files():
    """Check if data files exist"""
    print("\n📊 Checking data files...")
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        print(f"❌ Data directory '{data_dir}' not found")
        return False
    
    required_files = [
        "EUR_USD.csv",
        "GBP_USD.csv", 
        "USD_JPY.csv",
        "AUD_USD.csv",
        "USD_CHF.csv"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(data_dir, file)
        if os.path.exists(file_path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing data files: {', '.join(missing_files)}")
        print("💡 Download historical data or use demo data for backtesting")
        return False
    else:
        print("✅ All data files found!")
        return True

def check_settings():
    """Check settings configuration"""
    print("\n⚙️  Checking settings...")
    
    # Check if critical settings exist
    critical_settings = {
        'BOT_NAME': 'Bot name',
        'STRATEGY_NAME': 'Trading strategy',
        'ENVIRONMENT': 'Trading environment',
        'INSTRUMENT': 'Trading instrument'
    }
    
    missing_settings = []
    for setting, description in critical_settings.items():
        if hasattr(settings, setting) and getattr(settings, setting):
            print(f"✅ {description}: {getattr(settings, setting)}")
        else:
            print(f"❌ {description} - NOT SET")
            missing_settings.append(setting)
    
    # Check Oanda credentials (optional for backtesting)
    if hasattr(settings, 'ACCESS_TOKEN') and settings.ACCESS_TOKEN:
        token_preview = settings.ACCESS_TOKEN[:8] + "***" + settings.ACCESS_TOKEN[-4:]
        print(f"✅ Oanda Access Token: {token_preview}")
    else:
        print("⚠️  Oanda Access Token - NOT SET (required for live trading)")
    
    if hasattr(settings, 'ACCOUNT_ID') and settings.ACCOUNT_ID:
        account_preview = settings.ACCOUNT_ID[:3] + "***" + settings.ACCOUNT_ID[-3:]
        print(f"✅ Oanda Account ID: {account_preview}")
    else:
        print("⚠️  Oanda Account ID - NOT SET (required for live trading)")
    
    return len(missing_settings) == 0

def setup_wizard():
    """Interactive setup wizard"""
    print("\n🧙‍♂️ SETUP WIZARD")
    print("=" * 40)
    
    print("Let's configure your trading bot step by step...")
    
    # Strategy selection
    print("\n📈 STRATEGY SELECTION:")
    strategies = [
        "QuantitativeAlphaStrategy",
        "ProfessionalScalpingStrategy", 
        "InstitutionalBreakoutStrategy",
        "MachineLearningMomentumStrategy",
        "MultiInstrumentStrategy",
        "AdvancedMultiStrategy"
    ]
    
    print("Available strategies:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    
    try:
        choice = int(input("\nSelect strategy (1-6): ")) - 1
        if 0 <= choice < len(strategies):
            selected_strategy = strategies[choice]
            print(f"✅ Selected: {selected_strategy}")
            
            # Update settings file
            update_settings_file('STRATEGY_NAME', selected_strategy)
        else:
            print("❌ Invalid choice")
    except ValueError:
        print("❌ Invalid input")
    
    # Environment selection
    print("\n🏦 ENVIRONMENT SELECTION:")
    print("1. Practice (Demo trading)")
    print("2. Live (Real money)")
    
    try:
        env_choice = int(input("\nSelect environment (1-2): "))
        if env_choice == 1:
            environment = "practice"
        elif env_choice == 2:
            environment = "live"
        else:
            print("❌ Invalid choice")
            environment = "practice"
        
        print(f"✅ Selected: {environment}")
        update_settings_file('ENVIRONMENT', environment)
    except ValueError:
        print("❌ Invalid input, defaulting to practice")
        update_settings_file('ENVIRONMENT', 'practice')

def update_settings_file(setting_name, value):
    """Update a setting in the settings.py file"""
    try:
        # Read current settings
        with open('settings.py', 'r') as f:
            content = f.read()
        
        # Update the setting
        import re
        if isinstance(value, str):
            pattern = rf'{setting_name} = ["\'].*?["\']'
            replacement = f'{setting_name} = "{value}"'
        else:
            pattern = rf'{setting_name} = .*'
            replacement = f'{setting_name} = {value}'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            # Add new setting if it doesn't exist
            content += f'\n{setting_name} = "{value}"\n'
        
        # Write back to file
        with open('settings.py', 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {setting_name} in settings.py")
        
    except Exception as e:
        print(f"❌ Error updating settings: {e}")

def create_demo_data():
    """Create demo data files for testing"""
    print("\n📊 Creating demo data files...")
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✅ Created {data_dir} directory")
    
    # Create minimal CSV files for testing
    demo_data = """Date,Open,High,Low,Close,Volume
2010-01-01,1.4300,1.4350,1.4250,1.4320,1000
2010-01-02,1.4320,1.4380,1.4280,1.4350,1100
2010-01-03,1.4350,1.4400,1.4300,1.4370,1200
"""
    
    instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
    
    for instrument in instruments:
        file_path = os.path.join(data_dir, f"{instrument}.csv")
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(demo_data)
            print(f"✅ Created demo data: {instrument}.csv")

def main():
    """Main setup function"""
    print("🚀 ADVANCED OANDA TRADING BOT - SETUP")
    print("=" * 50)
    
    print("This setup will help you configure your trading bot.")
    print("Let's check your current setup...\n")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check data files
    data_ok = check_data_files()
    
    # Check settings
    settings_ok = check_settings()
    
    print("\n" + "=" * 50)
    print("📋 SETUP SUMMARY:")
    
    if deps_ok and data_ok and settings_ok:
        print("✅ Your bot is ready to go!")
        print("\n🎯 Next steps:")
        print("1. Run a backtest: python main.py backtest")
        print("2. Use the dashboard: python trading_dashboard.py")
        print("3. Start live trading: python main.py trade")
    else:
        print("⚠️  Some issues need to be resolved:")
        
        if not deps_ok:
            print("❌ Install missing dependencies")
        
        if not data_ok:
            create_demo = input("\n📊 Create demo data files for testing? (y/n): ")
            if create_demo.lower() == 'y':
                create_demo_data()
        
        if not settings_ok:
            run_wizard = input("\n🧙‍♂️ Run setup wizard? (y/n): ")
            if run_wizard.lower() == 'y':
                setup_wizard()
    
    print("\n🎉 Setup complete!")
    print("💡 Use 'python trading_dashboard.py' for the full control panel")

if __name__ == "__main__":
    main()
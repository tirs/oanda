# 🚀 Advanced Oanda Trading Bot
===============================

**Professional-grade Python trading bot for Oanda with multiple advanced strategies!**

## 🏆 **NEW: Advanced Money-Making Strategies Included!**

This bot now includes **8 professional trading strategies** used by hedge funds and institutional traders:

### 💰 **Available Strategies:**
1. **QuantitativeAlphaStrategy** 🏆 - Statistical arbitrage with market regime detection
2. **ProfessionalScalpingStrategy** ⚡ - High-frequency scalping for quick profits  
3. **InstitutionalBreakoutStrategy** 🏢 - Volume-confirmed breakout trading
4. **MachineLearningMomentumStrategy** 🤖 - ML-inspired feature engineering
5. **MultiInstrumentStrategy** 🌍 - Trade multiple currency pairs simultaneously
6. **AdvancedMultiStrategy** 📊 - Multi-indicator with advanced risk management
7. **MomentumStrategy** 📈 - Pure momentum following
8. **MeanReversionStrategy** 🔄 - Range-bound market specialist

## ✨ **Key Features:**
- **Multi-instrument trading** - Trade up to 10 currency pairs simultaneously
- **Advanced risk management** - Kelly Criterion, ATR-based stops, volatility adjustment
- **Market regime detection** - Automatically adapts to trending/ranging/volatile markets
- **Professional indicators** - RSI, MACD, Bollinger Bands, Stochastic, Williams %R
- **Windows compatible** - Fixed curses dependency for Windows users
- **Strategy selector** - Easy GUI to choose and test different strategies

To install:
===========

	If you do not have TA-Lib installed, follow these steps:

	1. Get build essentials

	$ sudo apt-get install build-essential
	$ sudo apt-get install python3-dev
	$ sudo apt-get install python3-pip

	2. Build TA-Lib

	$ wget http://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz/download?use_mirror=iweb
	$ tar zxfv ta-lib-0.4.0-src.tar.gz
	$ cd ta-lib
	$ ./configure --prefix=/usr
	$ make
	$ sudo make install

	1.3 Install python wrapper

	$ sudo pip install Cython
	$ sudo pip install numpy
	$ sudo pip install TA-Lib

	2. Install the rest of dependencies

	$ pip install -r requirements.txt


## 🎯 **Quick Start - Choose Your Strategy:**

### **Option 1: Use the Strategy Selector (Recommended)**
```bash
python strategy_selector.py
```
This will show you all available strategies and let you choose the best one for current market conditions.

### **Option 2: Direct Backtest**
```bash
python main.py backtest
```

### **Option 3: Live Trading**
```bash
python main.py trade
```

## 📊 **Strategy Recommendations:**

- **📈 Trending Markets:** `MachineLearningMomentumStrategy` or `MomentumStrategy`
- **📉 Range-Bound Markets:** `QuantitativeAlphaStrategy` or `MeanReversionStrategy`  
- **⚡ High Volatility:** `ProfessionalScalpingStrategy`
- **🔄 Breakouts:** `InstitutionalBreakoutStrategy`
- **🌍 Diversification:** `MultiInstrumentStrategy`

## ⚙️ **Configuration:**

### **Single Instrument Mode:**
Edit `settings.py`:
```python
STRATEGY_NAME = "QuantitativeAlphaStrategy"  # Choose your strategy
MULTI_INSTRUMENT_MODE = False
```

### **Multi-Instrument Mode:**
```python
STRATEGY_NAME = "MultiInstrumentStrategy"
MULTI_INSTRUMENT_MODE = True
INSTRUMENTS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
```

## 💡 **Pro Tips:**
- Start with `QuantitativeAlphaStrategy` - it adapts to all market conditions
- Use `ProfessionalScalpingStrategy` during high volatility (news events)
- `MultiInstrumentStrategy` provides better diversification and risk management
- Always backtest before live trading!

## 🌐 **NEW: Professional Web Interface**

### 🚀 **Launch the Web Dashboard**
```bash
python run_web_app.py
```

**Features:**
- 📊 **Real-time Trading Dashboard** - Live monitoring of positions and performance
- 📈 **Interactive Charts** - Advanced analytics with Chart.js visualizations  
- ⚙️ **Strategy Management** - Switch between strategies with one click
- 💰 **Position Monitoring** - Real-time P&L and risk metrics
- 📱 **Responsive Design** - Works on desktop, tablet, and mobile
- 🔄 **WebSocket Updates** - Live data streaming without page refresh
- 🎛️ **Settings Panel** - Configure all trading parameters via web UI
- 📊 **Performance Analytics** - Detailed backtesting and performance reports

**Access Points:**
- 🏠 **Main Dashboard:** http://localhost:8002
- 📊 **Trading Interface:** http://localhost:8002/dashboard  
- 💼 **Positions:** http://localhost:8002/positions
- 📈 **Analytics:** http://localhost:8002/analytics
- ⚙️ **Settings:** http://localhost:8002/settings
- 📚 **API Docs:** http://localhost:8002/api/docs

### 🎯 **Quick Web Setup**
1. **Install web dependencies:**
   ```bash
   pip install -r requirements_web.txt
   ```

2. **Launch web interface:**
   ```bash
   python run_web_app.py
   ```

3. **Open browser to:** http://localhost:8002

## 🔧 **NEW: Enhanced Trading System**

### 🎛️ **Trading Dashboard**
Use the comprehensive control panel:
```bash
python trading_dashboard.py
```
Features:
- 📊 Real-time monitoring
- ⚙️ Settings management  
- 📈 Performance analysis
- 🔧 Strategy switching
- 📝 Trading logs
- 💰 Account status

### 🛠️ **Quick Setup**
First-time setup wizard:
```bash
python setup_bot.py
```
This will:
- ✅ Check dependencies
- 📊 Verify data files
- ⚙️ Configure settings
- 🧙‍♂️ Guide you through setup

### 📈 **Enhanced trade.py Features**
- **Multi-instrument support** - Trade multiple pairs simultaneously
- **Advanced error handling** - Comprehensive logging and recovery
- **Settings validation** - Prevents configuration errors
- **Safety confirmations** - Protects against accidental live trading
- **Performance monitoring** - Detailed trade logging

## �🔧 **Installation:**

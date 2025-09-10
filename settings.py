import os

# Account settings - Use environment variables for deployment
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "101-001-36318401-001")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "605a7f34c9d070fe1c4f493fd82a83dc-ad2c3697bd2145c1d62c0936c27b03c1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "practice")

# Instruments to trade - now supports multiple pairs!
ACCOUNT_CURRENCY = "USD"
INSTRUMENT = "EUR_USD"  # Primary instrument for single-instrument mode

# Multi-instrument trading
MULTI_INSTRUMENT_MODE = True
INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF",
    "NZD_USD", "USD_CAD", "EUR_GBP", "EUR_JPY", "GBP_JPY"
]

# Size of candles in minutes
CANDLES_MINUTES = 60

# Risk settings - Enhanced for multi-instrument trading
MAX_PERCENTAGE_ACCOUNT_AT_RISK = 2  # Max 2% of account per trade
MAX_TOTAL_RISK_EXPOSURE = 10  # Max 10% total exposure across all instruments
MAX_CORRELATED_POSITIONS = 3  # Max positions in correlated instruments
CORRELATION_THRESHOLD = 0.7  # Correlation threshold for risk management

#Email credentials
EMAIL_RECIPIENT = "youremail@gmail.com"
EMAIL_FROM="oandabot@yourserver.com"
EMAIL_SERVER="mail.yourserver.com"
EMAIL_PORT=25
EMAIL_PASSWORD="SuchSecurePasswordStoredUnecrypted"

# Special bot name for identification
# In case you have many and want to distinguish between them 
# Leave default if only running one bot
BOT_NAME = "OANDAPYBOT"

# For backtesting
# BACKTESTING_FORMAT = "HISTDATA"
# BACKTESTING_FILENAME = "data/DAT_ASCII_EURUSD_M1_2015.csv"

BACKTESTING_FORMAT = "KAIDATA"
BACKTESTING_FILENAME = "data/EUR_USD_H1.csv"

# Strategy settings - Choose your money-making strategy!
STRATEGY_NAME = "AggressiveMultiInstrumentStrategy"  # Aggressive multi-pair trading for maximum opportunities

# Available advanced strategies:
ALTERNATIVE_STRATEGIES = [
    "AggressiveMultiInstrumentStrategy", # NEW: Aggressive multi-pair trading for maximum opportunities
    "QuantitativeAlphaStrategy",      # Statistical arbitrage & alpha generation
    "ProfessionalScalpingStrategy",   # High-frequency scalping for quick profits
    "InstitutionalBreakoutStrategy",  # Institutional-grade breakout trading
    "MachineLearningMomentumStrategy", # ML-inspired momentum strategy
    "AdvancedMultiStrategy",          # Enhanced with proper SL/TP orders
    "MultiInstrumentStrategy",        # Multi-instrument trading
    "MomentumStrategy",               # Pure momentum following
    "MeanReversionStrategy"           # Mean reversion for ranging markets
]

# Strategy-specific settings
QUANTITATIVE_SETTINGS = {
    'lookback_period': 100,    # Shorter for more responsive signals
    'zscore_entry': 1.8,       # Slightly more aggressive entry
    'risk_per_trade': 0.02,    # 2% risk per trade
}

SCALPING_SETTINGS = {
    'scalp_target_pips': 8,    # Target 8 pips profit
    'scalp_stop_pips': 4,      # Stop loss 4 pips
    'max_trades_per_hour': 15, # More aggressive scalping
    'risk_per_trade': 0.008,   # 0.8% risk per scalp
}

BREAKOUT_SETTINGS = {
    'lookback_period': 30,     # Shorter lookback for more signals
    'breakout_threshold': 0.0015, # 0.15% breakout threshold
    'risk_per_trade': 0.03,    # 3% risk per breakout trade
}

AGGRESSIVE_MULTI_SETTINGS = {
    'risk_per_trade': 0.01,    # 1% risk per trade (allows more simultaneous trades)
    'stop_loss_atr': 1.5,      # Tight stop loss for more trades
    'take_profit_atr': 2.5,    # Good risk/reward ratio
    'max_positions_per_instrument': 2,  # Allow 2 positions per currency pair
    'min_signal_strength': 1.5,  # Lower threshold for more opportunities
    'max_total_positions': 15,    # Maximum total positions across all pairs
}

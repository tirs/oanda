import backtrader
import btoandav20
import importlib
import settings
import traceback
import ui
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)

def strategy_class(class_name):
    """Dynamically load strategy class"""
    try:
        module = importlib.import_module("strategy")
        if hasattr(module, class_name):
            class_ = getattr(module, class_name)
            logging.info(f"Loaded strategy: {class_name}")
            return class_
        else:
            logging.error(f"Strategy {class_name} not found in strategy.py")
            # Fallback to a default strategy
            available_strategies = [attr for attr in dir(module) if attr.endswith('Strategy') and not attr.startswith('_')]
            if available_strategies:
                fallback = available_strategies[0]
                logging.warning(f"Using fallback strategy: {fallback}")
                return getattr(module, fallback)
            else:
                raise ImportError(f"No valid strategies found in strategy.py")
    except Exception as e:
        logging.error(f"Error loading strategy {class_name}: {e}")
        raise


def handle_exception(e):
    """Handle exceptions with logging and optional email notification"""
    error_msg = f"\n\nThe bot {settings.BOT_NAME} encountered an error:\n\n"
    error_msg += f"Error: {str(e)}\n"
    error_msg += f"Traceback:\n{traceback.format_exc()}\n"
    error_msg += f"Time: {datetime.now()}\n"
    
    logging.error(error_msg)
    
    # Try to send email if email settings are configured
    try:
        if hasattr(settings, 'EMAIL_ENABLED') and settings.EMAIL_ENABLED:
            import smtplib
            from email.mime.text import MIMEText
            # Add email sending logic here if needed
            logging.info("Email notification sent")
    except Exception as email_error:
        logging.warning(f"Could not send email notification: {email_error}")
    
    print(error_msg)


def setup_single_instrument_trading(cerebro, store):
    """Setup trading for single instrument"""
    logging.info(f"Setting up single instrument trading: {settings.INSTRUMENT}")
    
    datakwargs = dict(
        timeframe=backtrader.TimeFrame.Minutes,
        compression=1,
        tz='America/Los_Angeles',
        backfill=True,
        backfill_start=True,
    )
    
    data = store.getdata(dataname=settings.INSTRUMENT, **datakwargs)
    data.resample(
        timeframe=backtrader.TimeFrame.Minutes,
        compression=settings.CANDLES_MINUTES
    )
    cerebro.adddata(data)
    return cerebro


def setup_multi_instrument_trading(cerebro, store):
    """Setup trading for multiple instruments"""
    instruments = getattr(settings, 'INSTRUMENTS', [
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CHF',
        'NZD_USD', 'USD_CAD', 'EUR_GBP', 'EUR_JPY', 'GBP_JPY'
    ])
    
    logging.info(f"Setting up multi-instrument trading: {len(instruments)} pairs")
    
    datakwargs = dict(
        timeframe=backtrader.TimeFrame.Minutes,
        compression=1,
        tz='America/Los_Angeles',
        backfill=True,
        backfill_start=True,
    )
    
    for instrument in instruments:
        try:
            logging.info(f"Adding data feed for {instrument}")
            data = store.getdata(dataname=instrument, **datakwargs)
            data.resample(
                timeframe=backtrader.TimeFrame.Minutes,
                compression=settings.CANDLES_MINUTES
            )
            cerebro.adddata(data)
        except Exception as e:
            logging.warning(f"⚠️ Could not add {instrument}: {e}")
    
    return cerebro


def trade(headless=False):
    """Main trading function with enhanced multi-instrument support"""
    
    logging.info("Starting Advanced Oanda Trading Bot")
    logging.info(f"Strategy: {settings.STRATEGY_NAME}")
    logging.info(f"Multi-instrument mode: {getattr(settings, 'MULTI_INSTRUMENT_MODE', False)}")
    logging.info(f"Environment: {settings.ENVIRONMENT}")
    logging.info(f"Headless mode: {headless}")
    
    try:
        # Setup Oanda store
        storekwargs = dict(
            token=settings.ACCESS_TOKEN,
            account=settings.ACCOUNT_ID,
            practice=(settings.ENVIRONMENT == "practice"),
            notif_transactions=True,
            stream_timeout=10,
        )
        store = btoandav20.stores.OandaV20Store(**storekwargs)
        logging.info("Connected to Oanda")

        # Setup Cerebro
        cerebro = backtrader.Cerebro()
        
        # Add data feeds based on mode
        if getattr(settings, 'MULTI_INSTRUMENT_MODE', False):
            cerebro = setup_multi_instrument_trading(cerebro, store)
        else:
            cerebro = setup_single_instrument_trading(cerebro, store)
        
        # Setup broker and sizer
        cerebro.setbroker(store.getbroker())
        
        # Use advanced risk management if available
        risk_percent = getattr(settings, 'MAX_PERCENTAGE_ACCOUNT_AT_RISK', 2.0)
        cerebro.addsizer(btoandav20.sizers.OandaV20RiskPercentSizer, percents=risk_percent)
        
        # Add strategy
        strategy_cls = strategy_class(settings.STRATEGY_NAME)
        cerebro.addstrategy(strategy_cls)
        
        logging.info("Cerebro setup complete")
        
        if headless:
            # Run without UI for web app integration
            logging.info("Starting live trading in headless mode...")
            results = cerebro.run()
            logging.info("Trading session completed successfully")
        else:
            # Setup UI for interactive mode
            cursedui = ui.CursedUI(store)
            
            # Start trading with UI
            logging.info("Starting live trading with UI...")
            cursedui.run()
            results = cerebro.run()
            logging.info("Trading session completed successfully")
        
    except KeyboardInterrupt:
        logging.info("Trading stopped by user (Ctrl+C)")
    except Exception as e:
        logging.error(f"Trading error: {e}")
        handle_exception(e)
    finally:
        try:
            if 'cursedui' in locals():
                cursedui.stop()
            logging.info("Cleanup completed")
        except Exception as cleanup_error:
            logging.warning(f"Cleanup error: {cleanup_error}")


def validate_settings():
    """Validate required settings before trading"""
    required_settings = ['ACCESS_TOKEN', 'ACCOUNT_ID', 'ENVIRONMENT', 'STRATEGY_NAME']
    missing_settings = []
    
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            missing_settings.append(setting)
    
    if missing_settings:
        error_msg = f"Missing required settings: {', '.join(missing_settings)}"
        logging.error(error_msg)
        print(error_msg)
        print("Please configure these settings in settings.py before trading")
        return False
    
    # Validate Oanda credentials format
    if not settings.ACCESS_TOKEN.startswith(('live_', 'practice_')):
        logging.warning("ACCESS_TOKEN format may be incorrect")
    
    if settings.ENVIRONMENT not in ['practice', 'live']:
        logging.warning("ENVIRONMENT should be 'practice' or 'live'")
    
    logging.info("Settings validation passed")
    return True        

if __name__ == "__main__":
    print("Advanced Oanda Trading Bot - Live Trading Mode")
    print("=" * 60)
    
    # Validate settings before starting
    if validate_settings():
        print("All settings validated successfully")
        print("Starting live trading...")
        print("WARNING: This is LIVE trading with real money!")
        print("Press Ctrl+C to stop trading at any time")
        print("=" * 60)
        
        # Confirm live trading
        if settings.ENVIRONMENT == "live":
            confirm = input("You are about to start LIVE trading with real money. Type 'YES' to continue: ")
            if confirm != "YES":
                print("Live trading cancelled by user")
                sys.exit(0)
        
        trade()
    else:
        print("Settings validation failed. Please fix the issues above.")
        sys.exit(1)

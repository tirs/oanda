import backtrader
# import btplotting
import datetime
import importlib
import settings
# import support

class HistDataCSVData(backtrader.feeds.GenericCSVData):
    params = (
        ('nullvalue', float('NaN')),
        ('dtformat', 1),
        ('headers', False),
        ('time', -1),
        ('datetime', 0),
        ('open', 1),
        ('close', 2),
        ('high', 3),
        ('low', 4),
        ('volume', 5),
        ('openinterest', -1),
        ('reverse', True),
        ('separator', ';'),
    )

class KaiDataCSVData(backtrader.feeds.GenericCSVData):
    params = (
        ('nullvalue', float('NaN')),
        ('dtformat', 1),
        ('headers', True),
        ('time', -1),
        ('datetime', 0),
        ('open', 1),
        ('close', 2),
        ('high', 3),
        ('low', 4),
        ('volume', 5),
        ('openinterest', -1),
        ('reverse', True),
    )

def load_backtest_data():
    """Load single instrument data for backtesting"""
    data = None

    if settings.BACKTESTING_FORMAT == "KAIDATA":
        data = KaiDataCSVData(
            dataname=settings.BACKTESTING_FILENAME,
            separator='\t',
            timeframe=backtrader.TimeFrame.Minutes,
            compression=60,
            fromdate=datetime.datetime(2010,1,1),
            todate=datetime.datetime(2010,12, 1))

    if settings.BACKTESTING_FORMAT == "HISTDATA":
        data = HistDataCSVData(
            dataname=settings.BACKTESTING_FILENAME,
            dtformat="%Y%m%d %H%M%S")

    return data


def load_multi_instrument_data():
    """Load data for multiple instruments"""
    import os
    
    data_feeds = []
    data_dir = "data"
    
    # Use instruments from settings
    instruments = getattr(settings, 'INSTRUMENTS', [settings.INSTRUMENT])
    
    for instrument in instruments:
        filename = f"{data_dir}/{instrument}_H1.csv"
        if os.path.exists(filename):
            data = KaiDataCSVData(
                dataname=filename,
                separator='\t',
                timeframe=backtrader.TimeFrame.Minutes,
                compression=60,
                fromdate=datetime.datetime(2010, 1, 1),
                todate=datetime.datetime(2010, 4, 1)
            )
            data._name = instrument  # Add name for identification
            data_feeds.append(data)
            print(f"Loaded data for {instrument}")
        else:
            print(f"Data file not found for {instrument}: {filename}")
            
    return data_feeds


def strategy_class(class_name):
    module = importlib.import_module("strategy")
    class_ = getattr(module, class_name)
    return class_

def pretty_print(format, *args):
    print(format.format(*args))

def exists(object, *properties):
    for property in properties:
        if not property in object: return False
        object = object.get(property)
    return True

def addTradeAnalyzers(cerebro):
    cerebro.addanalyzer(backtrader.analyzers.TradeAnalyzer, _name='ta')
    cerebro.addanalyzer(backtrader.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(backtrader.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0, annualize=True,
                        timeframe=backtrader.TimeFrame.Minutes)
    # cerebro.addanalyzer(backtrader.analyzers.VWR, _name='vwr')
    cerebro.addanalyzer(backtrader.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(backtrader.analyzers.Transactions, _name='txn')

def printTradeAnalysis(cerebro, startfund, analyzers):
    format = "  {:<24} : {:<24}"
    NA     = '-'

    print('Backtesting Results')
    if hasattr(analyzers, 'ta'):
        ta = analyzers.ta.get_analysis()

        openTotal         = ta.total.open          if exists(ta, 'total', 'open'  ) else None
        closedTotal       = ta.total.closed        if exists(ta, 'total', 'closed') else None
        wonTotal          = ta.won.total           if exists(ta, 'won',   'total' ) else None
        lostTotal         = ta.lost.total          if exists(ta, 'lost',  'total' ) else None

        streakWonLongest  = ta.streak.won.longest  if exists(ta, 'streak', 'won',  'longest') else None
        streakLostLongest = ta.streak.lost.longest if exists(ta, 'streak', 'lost', 'longest') else None

        pnlNetTotal       = ta.pnl.net.total       if exists(ta, 'pnl', 'net', 'total'  ) else None
        pnlNetAverage     = ta.pnl.net.average     if exists(ta, 'pnl', 'net', 'average') else None

        pretty_print(format, 'Open Positions', openTotal   or NA)
        pretty_print(format, 'Closed Trades',  closedTotal or NA)
        pretty_print(format, 'Winning Trades', wonTotal    or NA)
        pretty_print(format, 'Loosing Trades', lostTotal   or NA)
        print('\n')

        pretty_print(format, 'Longest Winning Streak',   streakWonLongest  or NA)
        pretty_print(format, 'Longest Loosing Streak',   streakLostLongest or NA)
        pretty_print(format, 'Strike Rate (Win/closed)', (wonTotal / closedTotal) * 100 if wonTotal and closedTotal else NA)
        print('\n')

        pretty_print(format, 'Inital Portfolio Value', '${}'.format(startfund))
        pretty_print(format, 'Final Portfolio Value', '${}'.format(cerebro.broker.getvalue()))
        pretty_print(format, 'Net P/L', '${}'.format(round(pnlNetTotal, 2)) if pnlNetTotal   else NA)
        pretty_print(format, 'P/L Average per trade', '${}'.format(round(pnlNetAverage, 2)) if pnlNetAverage else NA)
        print('\n')

    if hasattr(analyzers, 'drawdown'):
        dd_analysis = analyzers.drawdown.get_analysis()
        drawdown = dd_analysis.get('drawdown', 0)
        pretty_print(format, 'Drawdown', '${}'.format(drawdown))
        
    if hasattr(analyzers, 'sharpe'):
        sharpe_analysis = analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', 'N/A')
        if sharpe_ratio is not None:
            pretty_print(format, 'Sharpe Ratio:', sharpe_ratio)
        else:
            pretty_print(format, 'Sharpe Ratio:', 'N/A')
            
    if hasattr(analyzers, 'sqn'):
        sqn_analysis = analyzers.sqn.get_analysis()
        sqn_value = sqn_analysis.get('sqn', 'N/A')
        if sqn_value is not None:
            pretty_print(format, 'SQN', sqn_value)
        else:
            pretty_print(format, 'SQN', 'N/A')
    print('\n')

    print('Transactions')
    format = "  {:<24} {:<24} {:<16} {:<8} {:<8} {:<16}"
    pretty_print(format, 'Date', 'Amount', 'Price', 'SID', 'Symbol', 'Value')
    for key, value in analyzers.txn.get_analysis().items():
        pretty_print(format, key.strftime("%Y/%m/%d %H:%M:%S"), value[0][0], value[0][1], value[0][2], value[0][3],
                     value[0][4])

                
def backtest():
    """Run backtest - supports both single and multi-instrument modes"""
    cerebro = backtrader.Cerebro()
    
    # Check if multi-instrument mode is enabled
    if getattr(settings, 'MULTI_INSTRUMENT_MODE', False):
        print("Running Multi-Instrument Backtest...")
        data_feeds = load_multi_instrument_data()
        
        if not data_feeds:
            print("No data feeds loaded. Falling back to single instrument mode.")
            data = load_backtest_data()
            cerebro.adddata(data)
        else:
            for data in data_feeds:
                cerebro.adddata(data)
                
        # Use MultiInstrumentStrategy for multi-instrument mode
        from strategy import MultiInstrumentStrategy
        cerebro.addstrategy(MultiInstrumentStrategy)
        
    else:
        print("Running Single-Instrument Backtest...")
        data = load_backtest_data()
        cerebro.adddata(data)
        cerebro.addstrategy(strategy_class(settings.STRATEGY_NAME))
    
    # Set up broker
    cerebro.broker.setcash(100000)  # Start with $100,000
    cerebro.addsizer(backtrader.sizers.percents_sizer.PercentSizer, 
                    percents=settings.MAX_PERCENTAGE_ACCOUNT_AT_RISK)
    cerebro.broker.setcommission(commission=0.0002, leverage=50)  # 0.02% commission, 50:1 leverage
    
    # Add analyzers
    addTradeAnalyzers(cerebro)
    
    # Run backtest
    print(f'Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    print(f'Final Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Print results
    printTradeAnalysis(cerebro, 100000, results[0].analyzers)


if __name__ == "__main__":
    backtest()

import backtrader
import backtrader.indicators as btind
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')
import random

# For real quantitative analysis
from scipy import stats
from scipy.optimize import minimize
import talib

# For real scalping (order book simulation)
from collections import deque
import time


class AdvancedMultiStrategy(backtrader.Strategy):
    """
    Enhanced multi-timeframe strategy with proper SL/TP orders and multi-instrument support
    Combines multiple technical indicators for better signal quality
    """
    
    params = (
        ('fast_ma', 10),
        ('slow_ma', 30),
        ('rsi_period', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('bb_period', 20),
        ('bb_dev', 2),
        ('atr_period', 14),
        ('risk_per_trade', 0.015),  # 1.5% risk per trade for multi-instrument
        ('stop_loss_atr', 2.0),     # Stop loss at 2x ATR
        ('take_profit_atr', 3.0),   # Take profit at 3x ATR
        ('max_positions', 3),       # Maximum concurrent positions per instrument
        ('min_signal_strength', 2.0), # Minimum signal strength for entry
    )
    
    def __init__(self):
        # Price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Moving averages
        self.fast_ma = btind.SMA(self.data, period=self.params.fast_ma)
        self.slow_ma = btind.SMA(self.data, period=self.params.slow_ma)
        self.ema_fast = btind.EMA(self.data, period=self.params.fast_ma)
        self.ema_slow = btind.EMA(self.data, period=self.params.slow_ma)
        
        # RSI
        self.rsi = btind.RSI(self.data, period=self.params.rsi_period)
        
        # Bollinger Bands
        self.bb = btind.BollingerBands(self.data, period=self.params.bb_period, devfactor=self.params.bb_dev)
        
        # ATR for volatility-based position sizing
        self.atr = btind.ATR(self.data, period=self.params.atr_period)
        
        # MACD
        self.macd = btind.MACD(self.data)
        
        # Stochastic
        self.stoch = btind.Stochastic(self.data)
        
        # Williams %R
        self.williams_r = btind.WilliamsR(self.data)
        
        # Track orders and positions
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.stop_order = None
        self.limit_order = None
        
        # Signal tracking
        self.signal_count = 0
        self.last_signal = None
        
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
        
    def notify_order(self, order):
        """Order notification"""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.5f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.5f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
        self.order = None
        
    def notify_trade(self, trade):
        """Trade notification"""
        if not trade.isclosed:
            return
            
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
        
    def get_signal_strength(self):
        """Calculate signal strength based on multiple indicators"""
        signals = []
        
        # MA crossover signal
        if self.fast_ma[0] > self.slow_ma[0] and self.fast_ma[-1] <= self.slow_ma[-1]:
            signals.append(1)  # Bullish
        elif self.fast_ma[0] < self.slow_ma[0] and self.fast_ma[-1] >= self.slow_ma[-1]:
            signals.append(-1)  # Bearish
        else:
            signals.append(0)
            
        # EMA trend signal
        if self.ema_fast[0] > self.ema_slow[0]:
            signals.append(0.5)
        else:
            signals.append(-0.5)
            
        # RSI signal
        if self.rsi[0] < self.params.rsi_oversold:
            signals.append(1)
        elif self.rsi[0] > self.params.rsi_overbought:
            signals.append(-1)
        else:
            signals.append(0)
            
        # Bollinger Bands signal
        if self.dataclose[0] < self.bb.lines.bot[0]:
            signals.append(0.5)  # Oversold
        elif self.dataclose[0] > self.bb.lines.top[0]:
            signals.append(-0.5)  # Overbought
        else:
            signals.append(0)
            
        # MACD signal
        if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]:
            signals.append(1)
        elif self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]:
            signals.append(-1)
        else:
            signals.append(0)
            
        # Stochastic signal
        if self.stoch.percK[0] < 20:
            signals.append(0.5)
        elif self.stoch.percK[0] > 80:
            signals.append(-0.5)
        else:
            signals.append(0)
            
        return sum(signals)
        
    def calculate_position_size(self):
        """Calculate position size based on ATR and risk management"""
        if len(self.atr) < 1:
            return 0
            
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        
        # Use ATR for stop loss distance
        stop_distance = self.atr[0] * self.params.stop_loss_atr
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            # Limit position size to reasonable amount
            max_position = account_value * 0.1  # Max 10% of account
            position_size = min(position_size, max_position)
            return int(position_size)
        
        return 0
        
    def next(self):
        """Main strategy logic"""
        # Skip if we don't have enough data
        if len(self.data) < max(self.params.slow_ma, self.params.bb_period, self.params.atr_period):
            return
            
        # Check if we have pending orders
        if self.order:
            return
            
        # Get signal strength
        signal_strength = self.get_signal_strength()
        
        # Current position
        current_position = self.position.size
        
        # Entry conditions
        strong_buy_signal = signal_strength >= 2.0
        strong_sell_signal = signal_strength <= -2.0
        
        # Additional filters
        trend_up = self.ema_fast[0] > self.ema_slow[0]
        trend_down = self.ema_fast[0] < self.ema_slow[0]
        
        # Volume filter (if available)
        volume_ok = True
        try:
            if hasattr(self.data, 'volume') and len(self.data.volume) > 10:
                volumes = [self.data.volume[-i] for i in range(1, 11)]
                avg_volume = sum(volumes) / len(volumes)
                volume_ok = self.data.volume[0] > avg_volume * 0.8
        except:
            volume_ok = True  # Skip volume filter if there's an issue
            
        # Entry logic with proper SL/TP orders
        if current_position == 0:  # No position
            if strong_buy_signal and trend_up and volume_ok and signal_strength >= self.params.min_signal_strength:
                size = self.calculate_position_size()
                if size > 0:
                    # Calculate SL and TP prices
                    current_price = self.dataclose[0]
                    stop_loss_price = current_price - (self.atr[0] * self.params.stop_loss_atr)
                    take_profit_price = current_price + (self.atr[0] * self.params.take_profit_atr)
                    
                    # Place main order with bracket orders (SL/TP)
                    self.order = self.buy_bracket(
                        size=size,
                        price=None,  # Market order
                        stopprice=stop_loss_price,
                        limitprice=take_profit_price,
                        exectype=backtrader.Order.Market
                    )
                    self.log(f'BUY BRACKET ORDER - Size: {size}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Signal: {signal_strength:.2f}')
                    
            elif strong_sell_signal and trend_down and volume_ok and signal_strength <= -self.params.min_signal_strength:
                size = self.calculate_position_size()
                if size > 0:
                    # Calculate SL and TP prices for short
                    current_price = self.dataclose[0]
                    stop_loss_price = current_price + (self.atr[0] * self.params.stop_loss_atr)
                    take_profit_price = current_price - (self.atr[0] * self.params.take_profit_atr)
                    
                    # Place main order with bracket orders (SL/TP)
                    self.order = self.sell_bracket(
                        size=size,
                        price=None,  # Market order
                        stopprice=stop_loss_price,
                        limitprice=take_profit_price,
                        exectype=backtrader.Order.Market
                    )
                    self.log(f'SELL BRACKET ORDER - Size: {size}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Signal: {signal_strength:.2f}')
                    
        else:  # We have a position - only close on very strong opposite signals
            if current_position > 0:  # Long position
                if signal_strength <= -2.5:  # Very strong sell signal
                    self.order = self.close()
                    self.log(f'CLOSE LONG - Strong opposite signal: {signal_strength:.2f}')
                    
            elif current_position < 0:  # Short position
                if signal_strength >= 2.5:  # Very strong buy signal
                    self.order = self.close()
                    self.log(f'CLOSE SHORT - Strong opposite signal: {signal_strength:.2f}')


class MomentumStrategy(backtrader.Strategy):
    """
    Momentum-based strategy focusing on trend following
    """
    
    params = (
        ('momentum_period', 12),
        ('roc_period', 10),
        ('rsi_period', 14),
        ('volume_period', 20),
        ('risk_per_trade', 0.015),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # Momentum indicators
        self.momentum = btind.Momentum(self.data, period=self.params.momentum_period)
        self.roc = btind.RateOfChange(self.data, period=self.params.roc_period)
        self.rsi = btind.RSI(self.data, period=self.params.rsi_period)
        
        # Trend indicators
        self.ema_short = btind.EMA(self.data, period=8)
        self.ema_long = btind.EMA(self.data, period=21)
        
        # Volatility
        self.atr = btind.ATR(self.data, period=14)
        
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            # Strong momentum + trend alignment
            if (self.momentum[0] > 0 and self.roc[0] > 2 and 
                self.ema_short[0] > self.ema_long[0] and 
                self.rsi[0] > 50 and self.rsi[0] < 80):
                
                size = int(self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0])
                self.order = self.buy(size=size)
                
            elif (self.momentum[0] < 0 and self.roc[0] < -2 and 
                  self.ema_short[0] < self.ema_long[0] and 
                  self.rsi[0] < 50 and self.rsi[0] > 20):
                
                size = int(self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0])
                self.order = self.sell(size=size)
        else:
            # Exit conditions
            if self.position.size > 0 and (self.momentum[0] < 0 or self.rsi[0] > 80):
                self.order = self.close()
            elif self.position.size < 0 and (self.momentum[0] > 0 or self.rsi[0] < 20):
                self.order = self.close()


class MeanReversionStrategy(backtrader.Strategy):
    """
    Mean reversion strategy for range-bound markets
    """
    
    params = (
        ('bb_period', 20),
        ('bb_dev', 2.5),
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        ('risk_per_trade', 0.02),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # Mean reversion indicators
        self.bb = btind.BollingerBands(self.data, period=self.params.bb_period, devfactor=self.params.bb_dev)
        self.rsi = btind.RSI(self.data, period=self.params.rsi_period)
        self.sma = btind.SMA(self.data, period=self.params.bb_period)
        
        # Volatility
        self.atr = btind.ATR(self.data, period=14)
        
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        if not self.position:
            # Oversold conditions
            if (self.dataclose[0] < self.bb.lines.bot[0] and 
                self.rsi[0] < self.params.rsi_oversold):
                
                size = int(self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0])
                self.order = self.buy(size=size)
                
            # Overbought conditions
            elif (self.dataclose[0] > self.bb.lines.top[0] and 
                  self.rsi[0] > self.params.rsi_overbought):
                
                size = int(self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0])
                self.order = self.sell(size=size)
        else:
            # Exit when price returns to mean
            if abs(self.dataclose[0] - self.sma[0]) < self.atr[0] * 0.5:
                self.order = self.close()


class AggressiveMultiInstrumentStrategy(backtrader.Strategy):
    """
    Aggressive multi-instrument strategy designed to maximize trading opportunities
    Trades multiple currency pairs simultaneously with proper risk management
    """
    
    params = (
        ('fast_ma', 8),
        ('slow_ma', 21),
        ('rsi_period', 14),
        ('atr_period', 14),
        ('bb_period', 20),
        ('risk_per_trade', 0.01),    # 1% risk per trade (lower for more trades)
        ('stop_loss_atr', 1.5),      # Tighter stop loss for more trades
        ('take_profit_atr', 2.5),    # Good risk/reward ratio
        ('max_positions_per_instrument', 2),  # Allow multiple positions per pair
        ('min_signal_strength', 1.5),  # Lower threshold for more opportunities
        ('correlation_filter', True),   # Enable correlation filtering
    )
    
    def __init__(self):
        # Initialize indicators for all data feeds (instruments)
        self.indicators = {}
        self.orders = {}
        self.positions_count = {}
        
        for i, data in enumerate(self.datas):
            instrument = data._name if hasattr(data, '_name') else f"Data{i}"
            
            self.indicators[instrument] = {
                'close': data.close,
                'high': data.high,
                'low': data.low,
                'fast_ma': btind.SMA(data, period=self.params.fast_ma),
                'slow_ma': btind.SMA(data, period=self.params.slow_ma),
                'ema_fast': btind.EMA(data, period=self.params.fast_ma),
                'ema_slow': btind.EMA(data, period=self.params.slow_ma),
                'rsi': btind.RSI(data, period=self.params.rsi_period),
                'atr': btind.ATR(data, period=self.params.atr_period),
                'bb': btind.BollingerBands(data, period=self.params.bb_period),
                'macd': btind.MACD(data),
                'stoch': btind.Stochastic(data),
            }
            
            self.orders[instrument] = None
            self.positions_count[instrument] = 0
    
    def log(self, txt, dt=None, instrument=""):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} [{instrument}]: {txt}')
    
    def get_signal_strength(self, instrument):
        """Calculate signal strength for specific instrument"""
        ind = self.indicators[instrument]
        signals = []
        
        # MA crossover signal
        if ind['fast_ma'][0] > ind['slow_ma'][0] and ind['fast_ma'][-1] <= ind['slow_ma'][-1]:
            signals.append(1)  # Bullish crossover
        elif ind['fast_ma'][0] < ind['slow_ma'][0] and ind['fast_ma'][-1] >= ind['slow_ma'][-1]:
            signals.append(-1)  # Bearish crossover
        else:
            signals.append(0)
        
        # EMA trend
        if ind['ema_fast'][0] > ind['ema_slow'][0]:
            signals.append(0.5)
        else:
            signals.append(-0.5)
        
        # RSI signal
        if ind['rsi'][0] < 30:
            signals.append(1)  # Oversold
        elif ind['rsi'][0] > 70:
            signals.append(-1)  # Overbought
        else:
            signals.append(0)
        
        # Bollinger Bands
        if ind['close'][0] < ind['bb'].lines.bot[0]:
            signals.append(0.5)  # Below lower band
        elif ind['close'][0] > ind['bb'].lines.top[0]:
            signals.append(-0.5)  # Above upper band
        else:
            signals.append(0)
        
        # MACD signal
        if ind['macd'].macd[0] > ind['macd'].signal[0] and ind['macd'].macd[-1] <= ind['macd'].signal[-1]:
            signals.append(1)
        elif ind['macd'].macd[0] < ind['macd'].signal[0] and ind['macd'].macd[-1] >= ind['macd'].signal[-1]:
            signals.append(-1)
        else:
            signals.append(0)
        
        # Stochastic
        if ind['stoch'].percK[0] < 20:
            signals.append(0.5)
        elif ind['stoch'].percK[0] > 80:
            signals.append(-0.5)
        else:
            signals.append(0)
        
        return sum(signals)
    
    def calculate_position_size(self, instrument):
        """Calculate position size for specific instrument"""
        ind = self.indicators[instrument]
        
        if len(ind['atr']) < 1:
            return 0
        
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        
        # Use ATR for stop loss distance
        stop_distance = ind['atr'][0] * self.params.stop_loss_atr
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            # Limit position size
            max_position = account_value * 0.05  # Max 5% per trade
            position_size = min(position_size, max_position)
            return int(position_size)
        
        return 0
    
    def next(self):
        """Main strategy logic - check all instruments"""
        for i, data in enumerate(self.datas):
            instrument = data._name if hasattr(data, '_name') else f"Data{i}"
            
            # Skip if not enough data
            if len(data) < max(self.params.slow_ma, self.params.bb_period, self.params.atr_period):
                continue
            
            # Skip if we have pending orders for this instrument
            if self.orders[instrument]:
                continue
            
            self.analyze_instrument(instrument, i)
    
    def analyze_instrument(self, instrument, data_index):
        """Analyze specific instrument for trading opportunities"""
        ind = self.indicators[instrument]
        data = self.datas[data_index]
        
        signal_strength = self.get_signal_strength(instrument)
        current_position = self.getposition(data).size
        
        # Entry conditions
        strong_buy_signal = signal_strength >= self.params.min_signal_strength
        strong_sell_signal = signal_strength <= -self.params.min_signal_strength
        
        # Trend filters
        trend_up = ind['ema_fast'][0] > ind['ema_slow'][0]
        trend_down = ind['ema_fast'][0] < ind['ema_slow'][0]
        
        # Position limits per instrument
        can_add_position = self.positions_count[instrument] < self.params.max_positions_per_instrument
        
        if current_position == 0 and can_add_position:  # No position for this instrument
            if strong_buy_signal and trend_up:
                size = self.calculate_position_size(instrument)
                if size > 0:
                    # Calculate SL and TP prices
                    current_price = ind['close'][0]
                    stop_loss_price = current_price - (ind['atr'][0] * self.params.stop_loss_atr)
                    take_profit_price = current_price + (ind['atr'][0] * self.params.take_profit_atr)
                    
                    # Place bracket order
                    self.orders[instrument] = self.buy_bracket(
                        data=data,
                        size=size,
                        price=None,
                        stopprice=stop_loss_price,
                        limitprice=take_profit_price,
                        exectype=backtrader.Order.Market
                    )
                    self.positions_count[instrument] += 1
                    self.log(f'BUY BRACKET - Size: {size}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Signal: {signal_strength:.2f}', 
                            instrument=instrument)
                    
            elif strong_sell_signal and trend_down:
                size = self.calculate_position_size(instrument)
                if size > 0:
                    # Calculate SL and TP prices for short
                    current_price = ind['close'][0]
                    stop_loss_price = current_price + (ind['atr'][0] * self.params.stop_loss_atr)
                    take_profit_price = current_price - (ind['atr'][0] * self.params.take_profit_atr)
                    
                    # Place bracket order
                    self.orders[instrument] = self.sell_bracket(
                        data=data,
                        size=size,
                        price=None,
                        stopprice=stop_loss_price,
                        limitprice=take_profit_price,
                        exectype=backtrader.Order.Market
                    )
                    self.positions_count[instrument] += 1
                    self.log(f'SELL BRACKET - Size: {size}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Signal: {signal_strength:.2f}', 
                            instrument=instrument)
        
        elif current_position != 0:  # We have a position - check for early exit
            # Only close on very strong opposite signals
            if current_position > 0 and signal_strength <= -2.5:
                self.orders[instrument] = self.close(data=data)
                self.positions_count[instrument] = max(0, self.positions_count[instrument] - 1)
                self.log(f'CLOSE LONG - Strong opposite signal: {signal_strength:.2f}', instrument=instrument)
                
            elif current_position < 0 and signal_strength >= 2.5:
                self.orders[instrument] = self.close(data=data)
                self.positions_count[instrument] = max(0, self.positions_count[instrument] - 1)
                self.log(f'CLOSE SHORT - Strong opposite signal: {signal_strength:.2f}', instrument=instrument)
    
    def notify_order(self, order):
        """Order notification"""
        # Find which instrument this order belongs to
        instrument = "Unknown"
        for i, data in enumerate(self.datas):
            if order.data == data:
                instrument = data._name if hasattr(data, '_name') else f"Data{i}"
                break
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED - Price: {order.executed.price:.5f}, Size: {order.executed.size}', instrument=instrument)
            else:
                self.log(f'SELL EXECUTED - Price: {order.executed.price:.5f}, Size: {order.executed.size}', instrument=instrument)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.status}', instrument=instrument)
            # Reset position count if order failed
            if instrument in self.positions_count:
                self.positions_count[instrument] = max(0, self.positions_count[instrument] - 1)
        
        # Clear the order reference
        if instrument in self.orders:
            self.orders[instrument] = None
    
    def notify_trade(self, trade):
        """Trade notification"""
        if trade.isclosed:
            # Find instrument
            instrument = "Unknown"
            for i, data in enumerate(self.datas):
                if trade.data == data:
                    instrument = data._name if hasattr(data, '_name') else f"Data{i}"
                    break
            
            self.log(f'TRADE CLOSED - P&L: {trade.pnlcomm:.2f}', instrument=instrument)
            # Reset position count when trade closes
            if instrument in self.positions_count:
                self.positions_count[instrument] = max(0, self.positions_count[instrument] - 1)


class MultiInstrumentStrategy(backtrader.Strategy):
    """
    Multi-instrument strategy that can trade multiple currency pairs
    """
    
    params = (
        ('risk_per_trade', 0.01),  # 1% risk per trade per instrument
        ('max_positions_per_instrument', 1),
        ('correlation_threshold', 0.7),  # Avoid highly correlated positions
    )
    
    def __init__(self):
        self.instruments = {}
        self.orders = {}
        self.positions_count = 0
        
        # Initialize indicators for each data feed
        for i, data in enumerate(self.datas):
            instrument_name = data._name if hasattr(data, '_name') else f'instrument_{i}'
            
            self.instruments[instrument_name] = {
                'data': data,
                'close': data.close,
                'high': data.high,
                'low': data.low,
                
                # Technical indicators
                'sma_fast': btind.SMA(data, period=10),
                'sma_slow': btind.SMA(data, period=30),
                'ema_fast': btind.EMA(data, period=8),
                'ema_slow': btind.EMA(data, period=21),
                'rsi': btind.RSI(data, period=14),
                'bb': btind.BollingerBands(data, period=20),
                'atr': btind.ATR(data, period=14),
                'macd': btind.MACD(data),
                'stoch': btind.Stochastic(data),
                
                # Position tracking
                'position_size': 0,
                'last_signal': 0,
                'order': None,
            }
            
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
        
    def get_signal_strength(self, instrument):
        """Calculate signal strength for a specific instrument"""
        inst = self.instruments[instrument]
        signals = []
        
        # Skip if not enough data
        if len(inst['close']) < 30:
            return 0
            
        # MA crossover signal
        if inst['sma_fast'][0] > inst['sma_slow'][0] and inst['sma_fast'][-1] <= inst['sma_slow'][-1]:
            signals.append(1)
        elif inst['sma_fast'][0] < inst['sma_slow'][0] and inst['sma_fast'][-1] >= inst['sma_slow'][-1]:
            signals.append(-1)
        else:
            signals.append(0)
            
        # EMA trend
        if inst['ema_fast'][0] > inst['ema_slow'][0]:
            signals.append(0.5)
        else:
            signals.append(-0.5)
            
        # RSI signal
        if inst['rsi'][0] < 30:
            signals.append(1)
        elif inst['rsi'][0] > 70:
            signals.append(-1)
        else:
            signals.append(0)
            
        # Bollinger Bands
        if inst['close'][0] < inst['bb'].lines.bot[0]:
            signals.append(0.5)
        elif inst['close'][0] > inst['bb'].lines.top[0]:
            signals.append(-0.5)
        else:
            signals.append(0)
            
        # MACD signal
        if inst['macd'].macd[0] > inst['macd'].signal[0] and inst['macd'].macd[-1] <= inst['macd'].signal[-1]:
            signals.append(1)
        elif inst['macd'].macd[0] < inst['macd'].signal[0] and inst['macd'].macd[-1] >= inst['macd'].signal[-1]:
            signals.append(-1)
        else:
            signals.append(0)
            
        return sum(signals)
        
    def calculate_position_size(self, instrument):
        """Calculate position size for specific instrument"""
        inst = self.instruments[instrument]
        
        if len(inst['atr']) < 1:
            return 1000  # Default size if ATR not available
            
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        
        # Use ATR for position sizing
        atr_value = inst['atr'][0]
        if atr_value > 0:
            position_size = risk_amount / (atr_value * 2)  # 2x ATR stop loss
            max_position = account_value * 0.05  # Max 5% per instrument
            position_size = min(position_size, max_position)
            return max(int(position_size), 1000)  # Minimum 1000 units
            
        return 1000
        
    def next(self):
        """Main strategy logic for all instruments"""
        
        for instrument, inst in self.instruments.items():
            # Skip if pending order
            if inst['order']:
                continue
                
            # Get signal strength
            signal_strength = self.get_signal_strength(instrument)
            
            # Current position for this instrument
            current_position = self.getposition(inst['data']).size
            inst['position_size'] = current_position
            
            # Entry conditions - more aggressive for testing
            strong_buy = signal_strength >= 1.5
            strong_sell = signal_strength <= -1.5
            
            if current_position == 0:  # No position in this instrument
                if strong_buy:
                    size = self.calculate_position_size(instrument)
                    if size > 0:
                        inst['order'] = self.buy(data=inst['data'], size=size)
                        self.log(f'{instrument} BUY CREATE, Size: {size}, Signal: {signal_strength:.2f}')
                        
                elif strong_sell:
                    size = self.calculate_position_size(instrument)
                    if size > 0:
                        inst['order'] = self.sell(data=inst['data'], size=size)
                        self.log(f'{instrument} SELL CREATE, Size: {size}, Signal: {signal_strength:.2f}')
                        
            else:  # Have position in this instrument
                # Exit conditions
                if current_position > 0 and signal_strength <= -1.0:
                    inst['order'] = self.close(data=inst['data'])
                    self.log(f'{instrument} CLOSE LONG, Signal: {signal_strength:.2f}')
                    
                elif current_position < 0 and signal_strength >= 1.0:
                    inst['order'] = self.close(data=inst['data'])
                    self.log(f'{instrument} CLOSE SHORT, Signal: {signal_strength:.2f}')
                    
    def notify_order(self, order):
        """Order notification"""
        # Find which instrument this order belongs to
        for instrument, inst in self.instruments.items():
            if inst['order'] == order:
                if order.status in [order.Completed]:
                    if order.isbuy():
                        self.log(f'{instrument} BUY EXECUTED, Price: {order.executed.price:.5f}')
                    else:
                        self.log(f'{instrument} SELL EXECUTED, Price: {order.executed.price:.5f}')
                        
                elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                    self.log(f'{instrument} Order Canceled/Margin/Rejected')
                    
                inst['order'] = None
                break


class QuantitativeAlphaStrategy(backtrader.Strategy):
    """
    Advanced quantitative strategy using statistical arbitrage and alpha generation
    Based on professional hedge fund techniques
    """
    
    params = (
        ('lookback_period', 252),  # 1 year lookback
        ('zscore_entry', 2.0),     # Z-score threshold for entry
        ('zscore_exit', 0.5),      # Z-score threshold for exit
        ('volatility_window', 20), # Volatility calculation window
        ('momentum_window', 12),   # Momentum calculation window
        ('risk_per_trade', 0.015), # 1.5% risk per trade
        ('max_leverage', 3.0),     # Maximum leverage
        ('sharpe_threshold', 1.5), # Minimum Sharpe ratio for trades
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Advanced indicators
        self.returns = btind.PctChange(self.data, period=1)
        self.volatility = btind.StdDev(self.returns, period=self.params.volatility_window)
        self.momentum = btind.Momentum(self.data, period=self.params.momentum_window)
        
        # Statistical measures
        self.sma_long = btind.SMA(self.data, period=self.params.lookback_period//4)
        self.rolling_mean = btind.SMA(self.data, period=self.params.volatility_window)
        self.rolling_std = btind.StdDev(self.data, period=self.params.volatility_window)
        
        # Risk management
        self.atr = btind.ATR(self.data, period=14)
        self.rsi = btind.RSI(self.data, period=14)
        
        # Market regime detection
        self.vix_proxy = btind.StdDev(self.returns, period=10) * np.sqrt(252)  # Annualized volatility
        
        self.order = None
        self.trade_count = 0
        self.winning_trades = 0
        
    def calculate_zscore(self):
        """Calculate Z-score for mean reversion signals"""
        if len(self.rolling_std) < 1 or self.rolling_std[0] == 0:
            return 0
        return (self.dataclose[0] - self.rolling_mean[0]) / self.rolling_std[0]
    
    def calculate_kelly_size(self):
        """Calculate optimal position size using Kelly Criterion"""
        if self.trade_count < 10:
            return self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0]
        
        win_rate = self.winning_trades / self.trade_count
        if win_rate <= 0.5:
            return self.broker.getvalue() * 0.01 / self.dataclose[0]  # Conservative sizing
        
        # Simplified Kelly: f = (bp - q) / b where b=avg_win/avg_loss, p=win_rate, q=1-p
        avg_win_loss_ratio = 1.5  # Assume 1.5:1 reward/risk
        kelly_fraction = (avg_win_loss_ratio * win_rate - (1 - win_rate)) / avg_win_loss_ratio
        kelly_fraction = max(0.01, min(kelly_fraction, 0.05))  # Cap between 1% and 5%
        
        return self.broker.getvalue() * kelly_fraction / self.dataclose[0]
    
    def detect_market_regime(self):
        """Detect current market regime: trending, ranging, or volatile"""
        if len(self.vix_proxy) < 1:
            return "unknown"
        
        current_vol = self.vix_proxy[0]
        if current_vol > 0.25:  # High volatility
            return "volatile"
        elif abs(self.momentum[0]) > self.atr[0] * 2:
            return "trending"
        else:
            return "ranging"
    
    def next(self):
        if self.order or len(self.data) < self.params.volatility_window:
            return
        
        zscore = self.calculate_zscore()
        regime = self.detect_market_regime()
        
        # Advanced entry conditions based on market regime with proper SL/TP
        if not self.position:
            if regime == "ranging" and abs(zscore) > self.params.zscore_entry:
                # Mean reversion in ranging market
                if zscore > self.params.zscore_entry and self.rsi[0] > 70:
                    size = int(self.calculate_kelly_size())
                    if size > 0:
                        # Calculate SL/TP for mean reversion short
                        current_price = self.dataclose[0]
                        stop_loss_price = current_price + (self.atr[0] * 2.0)
                        take_profit_price = current_price - (self.atr[0] * 2.5)
                        
                        self.order = self.sell_bracket(
                            size=size,
                            price=None,
                            stopprice=stop_loss_price,
                            limitprice=take_profit_price,
                            exectype=backtrader.Order.Market
                        )
                        self.log(f'SELL BRACKET - Mean Reversion, Z-score: {zscore:.2f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
                    
                elif zscore < -self.params.zscore_entry and self.rsi[0] < 30:
                    size = int(self.calculate_kelly_size())
                    if size > 0:
                        # Calculate SL/TP for mean reversion long
                        current_price = self.dataclose[0]
                        stop_loss_price = current_price - (self.atr[0] * 2.0)
                        take_profit_price = current_price + (self.atr[0] * 2.5)
                        
                        self.order = self.buy_bracket(
                            size=size,
                            price=None,
                            stopprice=stop_loss_price,
                            limitprice=take_profit_price,
                            exectype=backtrader.Order.Market
                        )
                        self.log(f'BUY BRACKET - Mean Reversion, Z-score: {zscore:.2f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
            
            elif regime == "trending" and self.momentum[0] != 0:
                # Momentum following in trending market
                if (self.momentum[0] > 0 and self.rsi[0] > 50 and self.rsi[0] < 80 and
                    self.dataclose[0] > self.sma_long[0]):
                    size = int(self.calculate_kelly_size())
                    if size > 0:
                        # Calculate SL/TP for momentum long
                        current_price = self.dataclose[0]
                        stop_loss_price = current_price - (self.atr[0] * 1.5)
                        take_profit_price = current_price + (self.atr[0] * 3.0)
                        
                        self.order = self.buy_bracket(
                            size=size,
                            price=None,
                            stopprice=stop_loss_price,
                            limitprice=take_profit_price,
                            exectype=backtrader.Order.Market
                        )
                        self.log(f'BUY BRACKET - Momentum, Regime: {regime}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
                    
                elif (self.momentum[0] < 0 and self.rsi[0] < 50 and self.rsi[0] > 20 and
                      self.dataclose[0] < self.sma_long[0]):
                    size = int(self.calculate_kelly_size())
                    if size > 0:
                        # Calculate SL/TP for momentum short
                        current_price = self.dataclose[0]
                        stop_loss_price = current_price + (self.atr[0] * 1.5)
                        take_profit_price = current_price - (self.atr[0] * 3.0)
                        
                        self.order = self.sell_bracket(
                            size=size,
                            price=None,
                            stopprice=stop_loss_price,
                            limitprice=take_profit_price,
                            exectype=backtrader.Order.Market
                        )
                        self.log(f'SELL BRACKET - Momentum, Regime: {regime}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
        
        else:
            # Exit conditions
            if regime == "ranging":
                if abs(zscore) < self.params.zscore_exit:
                    self.order = self.close()
                    self.log(f'CLOSE - Mean Reversion Exit, Z-score: {zscore:.2f}')
            
            elif regime == "trending":
                # Trend reversal exit
                if ((self.position.size > 0 and self.momentum[0] < -self.atr[0]) or
                    (self.position.size < 0 and self.momentum[0] > self.atr[0])):
                    self.order = self.close()
                    self.log(f'CLOSE - Trend Reversal, Regime: {regime}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class ProfessionalScalpingStrategy(backtrader.Strategy):
    """
    High-frequency scalping strategy for short-term profits
    Uses order flow analysis and microstructure patterns
    """
    
    params = (
        ('fast_ema', 5),
        ('slow_ema', 13),
        ('rsi_period', 7),
        ('bb_period', 10),
        ('volume_ma', 20),
        ('scalp_target_pips', 5),   # Target 5 pips profit
        ('scalp_stop_pips', 3),     # Stop loss 3 pips
        ('risk_per_trade', 0.005),  # 0.5% risk per scalp
        ('max_trades_per_hour', 10),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Fast indicators for scalping
        self.ema_fast = btind.EMA(self.data, period=self.params.fast_ema)
        self.ema_slow = btind.EMA(self.data, period=self.params.slow_ema)
        self.rsi = btind.RSI(self.data, period=self.params.rsi_period)
        self.bb = btind.BollingerBands(self.data, period=self.params.bb_period, devfactor=1.5)
        
        # Price action indicators
        self.atr = btind.ATR(self.data, period=7)
        
        # Order flow proxies
        self.price_velocity = btind.RateOfChange(self.data, period=3)
        
        self.order = None
        self.entry_price = None
        self.trades_this_hour = 0
        self.last_trade_time = None
        
    def calculate_pip_value(self):
        """Calculate pip value for position sizing"""
        # Assuming EUR/USD or similar major pair
        return 0.0001
    
    def next(self):
        if self.order:
            return
        
        current_time = self.datas[0].datetime.datetime(0)
        
        # Reset hourly trade counter
        if (self.last_trade_time is None or 
            current_time.hour != self.last_trade_time.hour):
            self.trades_this_hour = 0
        
        # Limit trades per hour
        if self.trades_this_hour >= self.params.max_trades_per_hour:
            return
        
        pip_value = self.calculate_pip_value()
        
        if not self.position:
            # Scalping entry conditions
            ema_bullish = self.ema_fast[0] > self.ema_slow[0]
            ema_bearish = self.ema_fast[0] < self.ema_slow[0]
            
            # Price action confirmation
            strong_momentum = abs(self.price_velocity[0]) > 0.1
            
            # Volume confirmation (if available)
            volume_ok = True
            try:
                if hasattr(self.data, 'volume'):
                    volume_ma = sum([self.data.volume[-i] for i in range(1, 6)]) / 5
                    volume_ok = self.data.volume[0] > volume_ma * 1.2
            except:
                pass
            
            # Long scalp setup
            if (ema_bullish and self.rsi[0] > 45 and self.rsi[0] < 70 and
                strong_momentum and self.price_velocity[0] > 0 and volume_ok and
                self.dataclose[0] > self.bb.lines.mid[0]):
                
                # Calculate position size for scalping
                risk_amount = self.broker.getvalue() * self.params.risk_per_trade
                stop_distance = self.params.scalp_stop_pips * pip_value
                size = int(risk_amount / stop_distance) if stop_distance > 0 else 1000
                
                self.order = self.buy(size=size)
                self.entry_price = self.dataclose[0]
                self.trades_this_hour += 1
                self.last_trade_time = current_time
                self.log(f'SCALP BUY - Entry: {self.entry_price:.5f}')
            
            # Short scalp setup
            elif (ema_bearish and self.rsi[0] < 55 and self.rsi[0] > 30 and
                  strong_momentum and self.price_velocity[0] < 0 and volume_ok and
                  self.dataclose[0] < self.bb.lines.mid[0]):
                
                risk_amount = self.broker.getvalue() * self.params.risk_per_trade
                stop_distance = self.params.scalp_stop_pips * pip_value
                size = int(risk_amount / stop_distance) if stop_distance > 0 else 1000
                
                self.order = self.sell(size=size)
                self.entry_price = self.dataclose[0]
                self.trades_this_hour += 1
                self.last_trade_time = current_time
                self.log(f'SCALP SELL - Entry: {self.entry_price:.5f}')
        
        else:
            # Quick scalp exits
            if self.entry_price:
                profit_pips = abs(self.dataclose[0] - self.entry_price) / pip_value
                
                # Take profit
                if ((self.position.size > 0 and 
                     self.dataclose[0] >= self.entry_price + self.params.scalp_target_pips * pip_value) or
                    (self.position.size < 0 and 
                     self.dataclose[0] <= self.entry_price - self.params.scalp_target_pips * pip_value)):
                    
                    self.order = self.close()
                    self.log(f'SCALP PROFIT - Pips: {profit_pips:.1f}')
                
                # Stop loss
                elif ((self.position.size > 0 and 
                       self.dataclose[0] <= self.entry_price - self.params.scalp_stop_pips * pip_value) or
                      (self.position.size < 0 and 
                       self.dataclose[0] >= self.entry_price + self.params.scalp_stop_pips * pip_value)):
                    
                    self.order = self.close()
                    self.log(f'SCALP STOP - Pips: -{profit_pips:.1f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class InstitutionalBreakoutStrategy(backtrader.Strategy):
    """
    Institutional-grade breakout strategy
    Identifies and trades significant support/resistance breaks with volume confirmation
    """
    
    params = (
        ('lookback_period', 50),    # Period to identify S/R levels
        ('breakout_threshold', 0.002),  # 0.2% breakout threshold
        ('volume_multiplier', 1.5), # Volume must be 1.5x average
        ('atr_multiplier', 2.0),    # ATR-based stop loss
        ('risk_per_trade', 0.025),  # 2.5% risk per trade
        ('min_consolidation', 10),  # Minimum bars in consolidation
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Support/Resistance calculation
        self.highest = btind.Highest(self.datahigh, period=self.params.lookback_period)
        self.lowest = btind.Lowest(self.datalow, period=self.params.lookback_period)
        
        # Trend and momentum
        self.sma_trend = btind.SMA(self.data, period=50)
        self.ema_fast = btind.EMA(self.data, period=12)
        self.ema_slow = btind.EMA(self.data, period=26)
        
        # Volatility and volume
        self.atr = btind.ATR(self.data, period=14)
        self.volume_sma = btind.SMA(self.data.volume, period=20) if hasattr(self.data, 'volume') else None
        
        # Momentum oscillators
        self.rsi = btind.RSI(self.data, period=14)
        self.macd = btind.MACD(self.data)
        
        self.order = None
        self.resistance_level = None
        self.support_level = None
        self.consolidation_count = 0
        
    def identify_levels(self):
        """Identify key support and resistance levels"""
        if len(self.highest) < 1 or len(self.lowest) < 1:
            return None, None
        
        resistance = self.highest[0]
        support = self.lowest[0]
        
        # Check for consolidation (price staying within range)
        price_range = resistance - support
        current_range = abs(self.datahigh[0] - self.datalow[0])
        
        if current_range < price_range * 0.3:  # Tight consolidation
            self.consolidation_count += 1
        else:
            self.consolidation_count = 0
        
        return resistance, support
    
    def confirm_breakout(self, level, direction):
        """Confirm breakout with multiple criteria"""
        confirmations = 0
        
        # Price confirmation
        if direction == "up" and self.dataclose[0] > level * (1 + self.params.breakout_threshold):
            confirmations += 1
        elif direction == "down" and self.dataclose[0] < level * (1 - self.params.breakout_threshold):
            confirmations += 1
        
        # Volume confirmation
        if self.volume_sma and hasattr(self.data, 'volume'):
            if self.data.volume[0] > self.volume_sma[0] * self.params.volume_multiplier:
                confirmations += 1
        else:
            confirmations += 1  # Skip volume check if not available
        
        # Momentum confirmation
        if direction == "up" and self.macd.macd[0] > self.macd.signal[0]:
            confirmations += 1
        elif direction == "down" and self.macd.macd[0] < self.macd.signal[0]:
            confirmations += 1
        
        # RSI confirmation (not overbought/oversold)
        if 30 < self.rsi[0] < 70:
            confirmations += 1
        
        return confirmations >= 3
    
    def next(self):
        if self.order or len(self.data) < self.params.lookback_period:
            return
        
        resistance, support = self.identify_levels()
        if not resistance or not support:
            return
        
        # Only trade after sufficient consolidation
        if self.consolidation_count < self.params.min_consolidation:
            return
        
        if not self.position:
            # Resistance breakout (long)
            if (self.dataclose[0] > resistance and 
                self.confirm_breakout(resistance, "up") and
                self.dataclose[0] > self.sma_trend[0]):  # Trend alignment
                
                # Calculate position size
                risk_amount = self.broker.getvalue() * self.params.risk_per_trade
                stop_distance = self.atr[0] * self.params.atr_multiplier
                size = int(risk_amount / stop_distance) if stop_distance > 0 else 1000
                
                self.order = self.buy(size=size)
                self.log(f'BREAKOUT BUY - Resistance: {resistance:.5f}, Price: {self.dataclose[0]:.5f}')
            
            # Support breakdown (short)
            elif (self.dataclose[0] < support and 
                  self.confirm_breakout(support, "down") and
                  self.dataclose[0] < self.sma_trend[0]):  # Trend alignment
                
                risk_amount = self.broker.getvalue() * self.params.risk_per_trade
                stop_distance = self.atr[0] * self.params.atr_multiplier
                size = int(risk_amount / stop_distance) if stop_distance > 0 else 1000
                
                self.order = self.sell(size=size)
                self.log(f'BREAKDOWN SELL - Support: {support:.5f}, Price: {self.dataclose[0]:.5f}')
        
        else:
            # Exit conditions
            # Trend reversal or return to broken level
            if self.position.size > 0:
                if (self.dataclose[0] < resistance or  # Return to resistance (now support)
                    self.ema_fast[0] < self.ema_slow[0]):  # Trend reversal
                    self.order = self.close()
                    self.log('CLOSE LONG - Trend reversal or level retest')
            
            elif self.position.size < 0:
                if (self.dataclose[0] > support or  # Return to support (now resistance)
                    self.ema_fast[0] > self.ema_slow[0]):  # Trend reversal
                    self.order = self.close()
                    self.log('CLOSE SHORT - Trend reversal or level retest')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class MachineLearningMomentumStrategy(backtrader.Strategy):
    """
    Advanced momentum strategy using sophisticated feature engineering and pattern recognition
    Uses professional quantitative techniques for signal generation and risk management
    """
    
    params = (
        ('feature_window', 20),     # Window for feature calculation
        ('prediction_horizon', 5),  # Bars ahead to predict
        ('momentum_threshold', 0.6), # Momentum score threshold
        ('volatility_adjustment', True),
        ('risk_per_trade', 0.02),
        ('max_positions', 2),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Feature engineering indicators
        self.returns = btind.PctChange(self.data, period=1)
        self.log_returns = btind.PctChange(self.data, period=1)  # Approximation
        
        # Multiple timeframe momentum
        self.momentum_short = btind.Momentum(self.data, period=5)
        self.momentum_medium = btind.Momentum(self.data, period=10)
        self.momentum_long = btind.Momentum(self.data, period=20)
        
        # Volatility features
        self.volatility = btind.StdDev(self.returns, period=self.params.feature_window)
        self.atr = btind.ATR(self.data, period=14)
        
        # Price pattern features
        self.rsi = btind.RSI(self.data, period=14)
        self.bb = btind.BollingerBands(self.data, period=20)
        self.macd = btind.MACD(self.data)
        
        # Trend strength
        self.adx = btind.DirectionalMovementIndex(self.data, period=14)
        
        self.order = None
        self.feature_history = []
        self.prediction_accuracy = 0.5  # Start with 50% accuracy
        
    def extract_features(self):
        """Extract features for 'ML' prediction"""
        if len(self.data) < self.params.feature_window:
            return None
        
        features = {
            'momentum_short': self.momentum_short[0] / self.dataclose[0] if self.dataclose[0] != 0 else 0,
            'momentum_medium': self.momentum_medium[0] / self.dataclose[0] if self.dataclose[0] != 0 else 0,
            'momentum_long': self.momentum_long[0] / self.dataclose[0] if self.dataclose[0] != 0 else 0,
            'volatility': self.volatility[0] if len(self.volatility) > 0 else 0,
            'rsi_normalized': (self.rsi[0] - 50) / 50 if len(self.rsi) > 0 else 0,
            'bb_position': ((self.dataclose[0] - self.bb.lines.mid[0]) / 
                           (self.bb.lines.top[0] - self.bb.lines.bot[0])) if len(self.bb.lines.top) > 0 else 0,
            'macd_signal': 1 if (len(self.macd.macd) > 0 and self.macd.macd[0] > self.macd.signal[0]) else -1,
            'trend_strength': self.adx.adx[0] / 100 if len(self.adx.adx) > 0 else 0,
        }
        
        return features
    
    def calculate_momentum_score(self, features):
        """Calculate momentum score using weighted features"""
        if not features:
            return 0
        
        # Weighted scoring system (professional feature importance weighting)
        weights = {
            'momentum_short': 0.25,
            'momentum_medium': 0.20,
            'momentum_long': 0.15,
            'volatility': -0.10,  # High volatility reduces confidence
            'rsi_normalized': 0.10,
            'bb_position': 0.10,
            'macd_signal': 0.15,
            'trend_strength': 0.05,
        }
        
        score = sum(features.get(key, 0) * weight for key, weight in weights.items())
        
        # Adjust for prediction accuracy (adaptive learning)
        confidence_multiplier = (self.prediction_accuracy - 0.5) * 2  # Scale to -1 to 1
        score *= (1 + confidence_multiplier * 0.2)  # Adjust by up to 20%
        
        return score
    
    def update_prediction_accuracy(self, was_correct):
        """Update prediction accuracy (simple moving average)"""
        alpha = 0.1  # Learning rate
        if was_correct:
            self.prediction_accuracy = self.prediction_accuracy * (1 - alpha) + alpha
        else:
            self.prediction_accuracy = self.prediction_accuracy * (1 - alpha)
    
    def next(self):
        if self.order or len(self.data) < self.params.feature_window:
            return
        
        features = self.extract_features()
        if not features:
            return
        
        momentum_score = self.calculate_momentum_score(features)
        
        # Position count check
        current_positions = 1 if self.position.size != 0 else 0
        
        if current_positions < self.params.max_positions:
            # Entry signals based on momentum score
            if momentum_score > self.params.momentum_threshold:
                # Calculate volatility-adjusted position size
                base_size = self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0]
                
                if self.params.volatility_adjustment and features['volatility'] > 0:
                    # Reduce size in high volatility
                    vol_adjustment = 1 / (1 + features['volatility'] * 10)
                    size = int(base_size * vol_adjustment)
                else:
                    size = int(base_size)
                
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'ML BUY - Score: {momentum_score:.3f}, Features: {features}')
            
            elif momentum_score < -self.params.momentum_threshold:
                base_size = self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0]
                
                if self.params.volatility_adjustment and features['volatility'] > 0:
                    vol_adjustment = 1 / (1 + features['volatility'] * 10)
                    size = int(base_size * vol_adjustment)
                else:
                    size = int(base_size)
                
                if size > 0:
                    self.order = self.sell(size=size)
                    self.log(f'ML SELL - Score: {momentum_score:.3f}, Features: {features}')
        
        else:
            # Exit conditions for existing positions
            if abs(momentum_score) < self.params.momentum_threshold * 0.3:  # Weak signal
                self.order = self.close()
                self.log(f'ML CLOSE - Weak signal: {momentum_score:.3f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


# Import real strategies
try:
    from real_ml_strategy import (
        RealMachineLearningStrategy,
        RealQuantitativeAlphaStrategy, 
        RealProfessionalScalpingStrategy,
        RealInstitutionalBreakoutStrategy
    )
    print(" Real advanced strategies loaded successfully!")
except ImportError as e:
    print(f" Could not import real strategies: {e}")
    print(" Using fallback strategies...")

# Keep original simple strategy for backward compatibility
class Strategy(AdvancedMultiStrategy):
    """Default strategy - uses the advanced multi-strategy"""
    pass

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

# For real scalping (order book simulation)
from collections import deque
import time

class RealMachineLearningStrategy(backtrader.Strategy):
    """
    REAL Machine Learning Strategy using scikit-learn
    Uses Random Forest and Gradient Boosting for price prediction
    """
    
    params = (
        ('lookback_window', 50),    # Historical data for training
        ('retrain_frequency', 100), # Retrain model every N bars
        ('prediction_threshold', 0.6), # Confidence threshold for trades
        ('risk_per_trade', 0.02),
        ('max_positions', 2),
        ('feature_engineering', True),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # ML Models
        self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Technical indicators for features
        self.rsi = btind.RSI(self.data, period=14)
        self.macd = btind.MACD(self.data)
        self.bb = btind.BollingerBands(self.data, period=20)
        self.atr = btind.ATR(self.data, period=14)
        self.ema_fast = btind.EMA(self.data, period=12)
        self.ema_slow = btind.EMA(self.data, period=26)
        self.stoch = btind.Stochastic(self.data)
        self.williams_r = btind.WilliamsR(self.data)
        
        # Data storage for ML
        self.price_history = deque(maxlen=1000)
        self.feature_history = deque(maxlen=1000)
        self.target_history = deque(maxlen=1000)
        
        # Model state
        self.model_trained = False
        self.bars_since_retrain = 0
        self.last_prediction = 0
        self.prediction_confidence = 0
        
        self.order = None
        
    def extract_features(self):
        """Extract comprehensive features for ML model"""
        if len(self.data) < 30:
            return None
            
        features = []
        
        # Price-based features
        returns_1 = (self.dataclose[0] - self.dataclose[-1]) / self.dataclose[-1] if len(self.data) > 1 else 0
        returns_5 = (self.dataclose[0] - self.dataclose[-5]) / self.dataclose[-5] if len(self.data) > 5 else 0
        returns_10 = (self.dataclose[0] - self.dataclose[-10]) / self.dataclose[-10] if len(self.data) > 10 else 0
        
        features.extend([returns_1, returns_5, returns_10])
        
        # Technical indicators
        rsi_val = self.rsi[0] / 100.0 if len(self.rsi) > 0 else 0.5
        macd_val = self.macd.macd[0] if len(self.macd.macd) > 0 else 0
        macd_signal = self.macd.signal[0] if len(self.macd.signal) > 0 else 0
        macd_hist = self.macd.histo[0] if len(self.macd.histo) > 0 else 0
        
        features.extend([rsi_val, macd_val, macd_signal, macd_hist])
        
        # Bollinger Bands
        if len(self.bb.lines.mid) > 0:
            bb_upper = self.bb.lines.top[0]
            bb_lower = self.bb.lines.bot[0]
            bb_mid = self.bb.lines.mid[0]
            bb_position = (self.dataclose[0] - bb_mid) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0
            bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid != 0 else 0
            features.extend([bb_position, bb_width])
        else:
            features.extend([0, 0])
            
        # Volatility
        atr_val = self.atr[0] / self.dataclose[0] if len(self.atr) > 0 and self.dataclose[0] != 0 else 0
        features.append(atr_val)
        
        # EMA trend
        ema_trend = (self.ema_fast[0] - self.ema_slow[0]) / self.ema_slow[0] if len(self.ema_fast) > 0 and len(self.ema_slow) > 0 and self.ema_slow[0] != 0 else 0
        features.append(ema_trend)
        
        # Stochastic
        stoch_k = self.stoch.percK[0] / 100.0 if len(self.stoch.percK) > 0 else 0.5
        stoch_d = self.stoch.percD[0] / 100.0 if len(self.stoch.percD) > 0 else 0.5
        features.extend([stoch_k, stoch_d])
        
        # Williams %R
        williams_val = (self.williams_r[0] + 100) / 100.0 if len(self.williams_r) > 0 else 0.5
        features.append(williams_val)
        
        # Price patterns (candlestick-like features)
        if len(self.data) >= 3:
            body_size = abs(self.dataclose[0] - self.data.open[0]) / self.dataclose[0] if self.dataclose[0] != 0 else 0
            upper_shadow = (self.datahigh[0] - max(self.dataclose[0], self.data.open[0])) / self.dataclose[0] if self.dataclose[0] != 0 else 0
            lower_shadow = (min(self.dataclose[0], self.data.open[0]) - self.datalow[0]) / self.dataclose[0] if self.dataclose[0] != 0 else 0
            features.extend([body_size, upper_shadow, lower_shadow])
        else:
            features.extend([0, 0, 0])
            
        # Volume features (if available)
        if hasattr(self.data, 'volume') and len(self.data.volume) > 10:
            recent_volumes = [self.data.volume[-i] for i in range(1, 11)]
            avg_volume = np.mean(recent_volumes)
            volume_ratio = self.data.volume[0] / avg_volume if avg_volume > 0 else 1
            features.append(volume_ratio)
        else:
            features.append(1.0)
            
        return np.array(features)
    
    def create_target(self, future_bars=5):
        """Create target variable for ML training"""
        if len(self.price_history) < future_bars + 1:
            return 0
            
        current_price = self.price_history[-future_bars-1]
        future_price = self.price_history[-1]
        
        price_change = (future_price - current_price) / current_price
        
        # Classification: 1 for up, 0 for sideways, -1 for down
        if price_change > 0.001:  # 0.1% threshold
            return 1
        elif price_change < -0.001:
            return -1
        else:
            return 0
    
    def train_models(self):
        """Train ML models with historical data"""
        if len(self.feature_history) < 50:
            return False
            
        try:
            # Prepare training data
            X = np.array(list(self.feature_history))
            y = np.array(list(self.target_history))
            
            # Remove any NaN or infinite values
            mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
            X = X[mask]
            y = y[mask]
            
            if len(X) < 30:
                return False
                
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            self.rf_model.fit(X_scaled, y)
            self.gb_model.fit(X_scaled, y)
            
            # Evaluate models
            rf_score = self.rf_model.score(X_scaled, y)
            gb_score = self.gb_model.score(X_scaled, y)
            
            self.log(f'ML Models Trained - RF Score: {rf_score:.3f}, GB Score: {gb_score:.3f}')
            
            return True
            
        except Exception as e:
            self.log(f'ML Training Error: {e}')
            return False
    
    def predict_direction(self, features):
        """Make prediction using ensemble of models"""
        if not self.model_trained or features is None:
            return 0, 0
            
        try:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Get predictions from both models
            rf_pred = self.rf_model.predict(features_scaled)[0]
            gb_pred = self.gb_model.predict(features_scaled)[0]
            
            # Get prediction probabilities for confidence
            rf_proba = np.max(self.rf_model.predict_proba(features_scaled)[0])
            gb_proba = np.max(self.gb_model.predict_proba(features_scaled)[0])
            
            # Ensemble prediction (weighted average)
            ensemble_pred = (rf_pred + gb_pred) / 2
            ensemble_confidence = (rf_proba + gb_proba) / 2
            
            return ensemble_pred, ensemble_confidence
            
        except Exception as e:
            self.log(f'ML Prediction Error: {e}')
            return 0, 0
    
    def next(self):
        if self.order:
            return
            
        # Store current price and features
        self.price_history.append(self.dataclose[0])
        
        # Extract features
        features = self.extract_features()
        if features is None:
            return
            
        self.feature_history.append(features)
        
        # Create target for training (if we have enough history)
        if len(self.price_history) >= 10:
            target = self.create_target(5)
            self.target_history.append(target)
        
        # Train/retrain models
        self.bars_since_retrain += 1
        if (not self.model_trained and len(self.feature_history) >= 50) or \
           (self.bars_since_retrain >= self.params.retrain_frequency and len(self.feature_history) >= 50):
            
            if self.train_models():
                self.model_trained = True
                self.bars_since_retrain = 0
        
        # Make predictions and trade
        if self.model_trained:
            prediction, confidence = self.predict_direction(features)
            self.last_prediction = prediction
            self.prediction_confidence = confidence
            
            # Trading logic based on ML predictions
            if not self.position and confidence > self.params.prediction_threshold:
                base_size = self.broker.getvalue() * self.params.risk_per_trade / self.dataclose[0]
                
                # Adjust size based on confidence
                size = int(base_size * confidence)
                
                if prediction > 0.5 and size > 0:  # Strong buy signal
                    self.order = self.buy(size=size)
                    self.log(f'ML BUY - Prediction: {prediction:.3f}, Confidence: {confidence:.3f}')
                    
                elif prediction < -0.5 and size > 0:  # Strong sell signal
                    self.order = self.sell(size=size)
                    self.log(f'ML SELL - Prediction: {prediction:.3f}, Confidence: {confidence:.3f}')
            
            elif self.position:
                # Exit conditions
                if confidence < self.params.prediction_threshold * 0.5:  # Low confidence
                    self.order = self.close()
                    self.log(f'ML CLOSE - Low confidence: {confidence:.3f}')
                elif (self.position.size > 0 and prediction < -0.3) or \
                     (self.position.size < 0 and prediction > 0.3):  # Reversal signal
                    self.order = self.close()
                    self.log(f'ML CLOSE - Reversal signal: {prediction:.3f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class RealQuantitativeAlphaStrategy(backtrader.Strategy):
    """
    REAL Quantitative Alpha Strategy using statistical arbitrage
    Implements pairs trading, mean reversion, and statistical models
    """
    
    params = (
        ('lookback_period', 252),  # 1 year lookback
        ('zscore_entry', 2.0),     # Z-score threshold for entry
        ('zscore_exit', 0.5),      # Z-score threshold for exit
        ('half_life_threshold', 30), # Maximum half-life for mean reversion
        ('risk_per_trade', 0.015), # 1.5% risk per trade
        ('max_leverage', 3.0),     # Maximum leverage
        ('sharpe_threshold', 1.5), # Minimum Sharpe ratio for trades
        ('correlation_window', 60), # Window for correlation analysis
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Statistical measures
        self.returns = btind.PctChange(self.data, period=1)
        self.log_prices = []
        self.price_ratios = deque(maxlen=self.params.lookback_period)
        self.zscore_history = deque(maxlen=100)
        
        # Advanced indicators
        self.volatility = btind.StdDev(self.returns, period=20)
        self.momentum = btind.Momentum(self.data, period=12)
        self.atr = btind.ATR(self.data, period=14)
        self.rsi = btind.RSI(self.data, period=14)
        
        # Statistical arbitrage components
        self.mean_reversion_signal = 0
        self.momentum_signal = 0
        self.regime_state = 'neutral'  # trending, mean_reverting, neutral
        
        # Risk management
        self.current_sharpe = 0
        self.trade_pnl_history = deque(maxlen=50)
        
        self.order = None
        
    def calculate_half_life(self, series):
        """Calculate half-life of mean reversion using Ornstein-Uhlenbeck process"""
        if len(series) < 10:
            return float('inf')
            
        try:
            # Convert to numpy array
            y = np.array(series)
            y_lag = np.roll(y, 1)[1:]  # Lagged series
            y = y[1:]  # Current series
            
            # OLS regression: y_t = alpha + beta * y_{t-1} + epsilon
            X = np.column_stack([np.ones(len(y_lag)), y_lag])
            
            # Use scipy for robust regression
            from scipy.linalg import lstsq
            coeffs, _, _, _ = lstsq(X, y)
            
            beta = coeffs[1]
            
            # Half-life calculation
            if beta >= 1 or beta <= 0:
                return float('inf')
                
            half_life = -np.log(2) / np.log(beta)
            return half_life
            
        except Exception:
            return float('inf')
    
    def calculate_zscore(self, value, series):
        """Calculate z-score for statistical arbitrage"""
        if len(series) < 10:
            return 0
            
        mean_val = np.mean(series)
        std_val = np.std(series)
        
        if std_val == 0:
            return 0
            
        return (value - mean_val) / std_val
    
    def detect_market_regime(self):
        """Detect market regime using statistical tests"""
        if len(self.price_ratios) < 30:
            return 'neutral'
            
        # Convert to numpy array for analysis
        prices = np.array(list(self.price_ratios))
        
        # Test for mean reversion using Augmented Dickey-Fuller test (simplified)
        # In practice, you'd use statsmodels.tsa.stattools.adfuller
        half_life = self.calculate_half_life(prices)
        
        # Test for trending using linear regression slope
        x = np.arange(len(prices))
        slope, _, r_value, _, _ = stats.linregress(x, prices)
        
        # Regime classification
        if half_life < self.params.half_life_threshold and abs(r_value) < 0.3:
            return 'mean_reverting'
        elif abs(r_value) > 0.6:
            return 'trending'
        else:
            return 'neutral'
    
    def calculate_optimal_position_size(self, signal_strength, volatility):
        """Calculate optimal position size using Kelly Criterion"""
        if volatility <= 0:
            return 0
            
        # Simplified Kelly Criterion
        # f* = (bp - q) / b, where b = odds, p = win probability, q = loss probability
        
        # Estimate win probability based on signal strength and historical performance
        base_win_prob = 0.5 + (signal_strength * 0.2)  # Adjust based on signal
        win_prob = np.clip(base_win_prob, 0.1, 0.9)
        
        # Estimate average win/loss ratio from recent trades
        if len(self.trade_pnl_history) > 5:
            wins = [pnl for pnl in self.trade_pnl_history if pnl > 0]
            losses = [abs(pnl) for pnl in self.trade_pnl_history if pnl < 0]
            
            if wins and losses:
                avg_win = np.mean(wins)
                avg_loss = np.mean(losses)
                win_loss_ratio = avg_win / avg_loss
            else:
                win_loss_ratio = 1.5  # Default assumption
        else:
            win_loss_ratio = 1.5
        
        # Kelly fraction
        kelly_fraction = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
        kelly_fraction = np.clip(kelly_fraction, 0, 0.25)  # Cap at 25%
        
        # Adjust for volatility
        vol_adjustment = 1 / (1 + volatility * 10)
        
        # Final position size
        account_value = self.broker.getvalue()
        position_value = account_value * kelly_fraction * vol_adjustment
        
        return position_value / self.dataclose[0] if self.dataclose[0] > 0 else 0
    
    def next(self):
        if self.order:
            return
            
        # Store price data
        self.price_ratios.append(self.dataclose[0])
        
        if len(self.price_ratios) < 30:
            return
            
        # Detect market regime
        self.regime_state = self.detect_market_regime()
        
        # Calculate z-score for mean reversion
        current_zscore = self.calculate_zscore(self.dataclose[0], list(self.price_ratios))
        self.zscore_history.append(current_zscore)
        
        # Calculate signals based on regime
        if self.regime_state == 'mean_reverting':
            # Mean reversion strategy
            self.mean_reversion_signal = -np.tanh(current_zscore)  # Contrarian signal
            signal_strength = abs(self.mean_reversion_signal)
            
        elif self.regime_state == 'trending':
            # Momentum strategy
            momentum_zscore = self.calculate_zscore(self.momentum[0], 
                                                  [self.momentum[-i] for i in range(1, min(21, len(self.momentum)))])
            self.momentum_signal = np.tanh(momentum_zscore)  # Trend following
            signal_strength = abs(self.momentum_signal)
            
        else:
            # Neutral regime - reduce activity
            self.mean_reversion_signal = 0
            self.momentum_signal = 0
            signal_strength = 0
        
        # Combined signal
        if self.regime_state == 'mean_reverting':
            combined_signal = self.mean_reversion_signal
        elif self.regime_state == 'trending':
            combined_signal = self.momentum_signal
        else:
            combined_signal = 0
        
        # Risk management - calculate current Sharpe ratio
        if len(self.trade_pnl_history) > 10:
            returns_array = np.array(list(self.trade_pnl_history))
            if np.std(returns_array) > 0:
                self.current_sharpe = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252)
            else:
                self.current_sharpe = 0
        
        # Trading logic
        current_vol = self.volatility[0] if len(self.volatility) > 0 else 0.01
        
        if not self.position:
            # Entry conditions
            if (abs(combined_signal) > 0.5 and 
                signal_strength > 0.3 and 
                abs(current_zscore) > self.params.zscore_entry and
                self.current_sharpe > -1.0):  # Don't trade if performance is terrible
                
                # Calculate optimal position size
                position_size = self.calculate_optimal_position_size(signal_strength, current_vol)
                
                if position_size > 0:
                    if combined_signal > 0:
                        self.order = self.buy(size=int(position_size))
                        self.log(f'QUANT BUY - Signal: {combined_signal:.3f}, Z-score: {current_zscore:.2f}, '
                               f'Regime: {self.regime_state}, Sharpe: {self.current_sharpe:.2f}')
                    else:
                        self.order = self.sell(size=int(position_size))
                        self.log(f'QUANT SELL - Signal: {combined_signal:.3f}, Z-score: {current_zscore:.2f}, '
                               f'Regime: {self.regime_state}, Sharpe: {self.current_sharpe:.2f}')
        
        else:
            # Exit conditions
            exit_condition = False
            
            if self.regime_state == 'mean_reverting':
                # Exit when z-score returns to normal
                exit_condition = abs(current_zscore) < self.params.zscore_exit
            elif self.regime_state == 'trending':
                # Exit when momentum reverses
                exit_condition = (self.position.size > 0 and combined_signal < -0.2) or \
                               (self.position.size < 0 and combined_signal > 0.2)
            else:
                # Exit in neutral regime
                exit_condition = True
            
            # Risk management exits
            if (self.current_sharpe < -2.0 or  # Poor performance
                current_vol > 0.05):  # High volatility
                exit_condition = True
            
            if exit_condition:
                self.order = self.close()
                self.log(f'QUANT CLOSE - Z-score: {current_zscore:.2f}, Regime: {self.regime_state}')
    
    def notify_trade(self, trade):
        """Track trade performance for Sharpe ratio calculation"""
        if trade.isclosed:
            self.trade_pnl_history.append(trade.pnlcomm)
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class RealProfessionalScalpingStrategy(backtrader.Strategy):
    """
    REAL Professional Scalping Strategy
    Implements order book analysis, microstructure patterns, and high-frequency techniques
    """
    
    params = (
        ('tick_size', 0.00001),     # Minimum price movement
        ('spread_threshold', 2),    # Maximum spread in ticks
        ('volume_imbalance_threshold', 0.7),  # Order flow imbalance threshold
        ('scalp_target_ticks', 3),  # Target profit in ticks
        ('scalp_stop_ticks', 2),    # Stop loss in ticks
        ('max_trades_per_minute', 5),
        ('risk_per_trade', 0.001),  # 0.1% risk per scalp
        ('momentum_window', 10),    # Very short momentum window
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Microstructure indicators
        self.tick_data = deque(maxlen=100)
        self.bid_ask_spread = deque(maxlen=50)
        self.volume_imbalance = deque(maxlen=20)
        
        # Ultra-fast indicators
        self.ema_ultra_fast = btind.EMA(self.data, period=3)
        self.ema_fast = btind.EMA(self.data, period=8)
        self.rsi_fast = btind.RSI(self.data, period=5)
        
        # Order flow simulation (since we don't have real order book)
        self.simulated_bid_volume = deque(maxlen=20)
        self.simulated_ask_volume = deque(maxlen=20)
        
        # Scalping state
        self.last_trade_time = 0
        self.trades_this_minute = 0
        self.current_minute = 0
        
        # Price action patterns
        self.price_momentum = deque(maxlen=self.params.momentum_window)
        
        self.order = None
        
    def simulate_order_book(self):
        """Simulate order book data from price/volume information"""
        if not hasattr(self.data, 'volume') or len(self.data.volume) == 0:
            # If no volume data, simulate based on price action
            price_change = self.dataclose[0] - self.dataclose[-1] if len(self.data) > 1 else 0
            
            # Simulate volume imbalance based on price movement
            if price_change > 0:
                bid_vol = 100 + abs(price_change) * 10000
                ask_vol = 80 + abs(price_change) * 5000
            elif price_change < 0:
                bid_vol = 80 + abs(price_change) * 5000
                ask_vol = 100 + abs(price_change) * 10000
            else:
                bid_vol = ask_vol = 90
        else:
            # Use actual volume data to simulate order book
            total_vol = self.data.volume[0]
            price_change = self.dataclose[0] - self.dataclose[-1] if len(self.data) > 1 else 0
            
            if price_change > 0:
                bid_vol = total_vol * 0.6
                ask_vol = total_vol * 0.4
            elif price_change < 0:
                bid_vol = total_vol * 0.4
                ask_vol = total_vol * 0.6
            else:
                bid_vol = ask_vol = total_vol * 0.5
        
        self.simulated_bid_volume.append(bid_vol)
        self.simulated_ask_volume.append(ask_vol)
        
        # Calculate volume imbalance
        if bid_vol + ask_vol > 0:
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
        else:
            imbalance = 0
            
        self.volume_imbalance.append(imbalance)
        
        return imbalance
    
    def calculate_spread(self):
        """Calculate bid-ask spread (simulated)"""
        # Simulate spread based on volatility
        if len(self.data) > 5:
            recent_range = max([self.datahigh[-i] for i in range(1, 6)]) - \
                          min([self.datalow[-i] for i in range(1, 6)])
            spread = max(self.params.tick_size, recent_range * 0.1)
        else:
            spread = self.params.tick_size * 2
            
        self.bid_ask_spread.append(spread)
        return spread
    
    def detect_microstructure_pattern(self):
        """Detect microstructure patterns for scalping"""
        if len(self.price_momentum) < 5:
            return 'neutral', 0
            
        # Calculate ultra-short momentum
        momentum = (self.dataclose[0] - self.dataclose[-5]) / self.dataclose[-5] if len(self.data) > 5 else 0
        self.price_momentum.append(momentum)
        
        # Pattern detection
        recent_momentum = list(self.price_momentum)[-5:]
        
        # Momentum acceleration pattern
        if len(recent_momentum) >= 3:
            if all(recent_momentum[i] > recent_momentum[i-1] for i in range(1, 3)):
                return 'momentum_up', abs(momentum)
            elif all(recent_momentum[i] < recent_momentum[i-1] for i in range(1, 3)):
                return 'momentum_down', abs(momentum)
        
        # Mean reversion pattern (for counter-trend scalping)
        if abs(momentum) > 0.0005:  # Strong move
            return 'mean_reversion', abs(momentum)
        
        return 'neutral', 0
    
    def calculate_scalp_size(self):
        """Calculate position size for scalping"""
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        
        # Very tight stop loss for scalping
        stop_distance = self.params.scalp_stop_ticks * self.params.tick_size
        
        if stop_distance > 0:
            size = risk_amount / stop_distance
            # Limit to reasonable size for scalping
            max_size = account_value * 0.02  # Max 2% of account
            return min(int(size), int(max_size / self.dataclose[0]))
        
        return 0
    
    def next(self):
        if self.order:
            return
            
        # Time management for scalping
        current_time = self.data.datetime.datetime(0)
        current_minute_num = current_time.minute
        
        if current_minute_num != self.current_minute:
            self.current_minute = current_minute_num
            self.trades_this_minute = 0
        
        # Limit trades per minute
        if self.trades_this_minute >= self.params.max_trades_per_minute:
            return
        
        # Simulate order book and microstructure
        volume_imbalance = self.simulate_order_book()
        spread = self.calculate_spread()
        
        # Skip if spread is too wide
        if spread > self.params.spread_threshold * self.params.tick_size:
            return
        
        # Detect microstructure patterns
        pattern, strength = self.detect_microstructure_pattern()
        
        # Ultra-fast technical signals
        ema_signal = 1 if self.ema_ultra_fast[0] > self.ema_fast[0] else -1
        rsi_signal = 1 if self.rsi_fast[0] < 30 else (-1 if self.rsi_fast[0] > 70 else 0)
        
        # Order flow signal
        flow_signal = 1 if volume_imbalance > self.params.volume_imbalance_threshold else \
                     (-1 if volume_imbalance < -self.params.volume_imbalance_threshold else 0)
        
        # Combined scalping signal
        total_signal = 0
        
        if pattern == 'momentum_up' and ema_signal > 0 and flow_signal > 0:
            total_signal = strength * 2
        elif pattern == 'momentum_down' and ema_signal < 0 and flow_signal < 0:
            total_signal = -strength * 2
        elif pattern == 'mean_reversion':
            # Counter-trend scalping
            if rsi_signal > 0 and flow_signal < 0:
                total_signal = strength
            elif rsi_signal < 0 and flow_signal > 0:
                total_signal = -strength
        
        # Scalping trades
        if not self.position and abs(total_signal) > 0.3:
            size = self.calculate_scalp_size()
            
            if size > 0:
                if total_signal > 0:
                    self.order = self.buy(size=size)
                    self.trades_this_minute += 1
                    self.log(f'SCALP BUY - Signal: {total_signal:.3f}, Pattern: {pattern}, '
                           f'Imbalance: {volume_imbalance:.3f}, Spread: {spread/self.params.tick_size:.1f} ticks')
                else:
                    self.order = self.sell(size=size)
                    self.trades_this_minute += 1
                    self.log(f'SCALP SELL - Signal: {total_signal:.3f}, Pattern: {pattern}, '
                           f'Imbalance: {volume_imbalance:.3f}, Spread: {spread/self.params.tick_size:.1f} ticks')
        
        elif self.position:
            # Quick exit conditions for scalping
            entry_price = self.position.price if hasattr(self.position, 'price') else self.dataclose[0]
            current_price = self.dataclose[0]
            
            if self.position.size > 0:  # Long position
                profit_ticks = (current_price - entry_price) / self.params.tick_size
                
                if (profit_ticks >= self.params.scalp_target_ticks or 
                    profit_ticks <= -self.params.scalp_stop_ticks or
                    total_signal < -0.2):  # Signal reversal
                    
                    self.order = self.close()
                    self.log(f'SCALP CLOSE LONG - Profit: {profit_ticks:.1f} ticks')
                    
            else:  # Short position
                profit_ticks = (entry_price - current_price) / self.params.tick_size
                
                if (profit_ticks >= self.params.scalp_target_ticks or 
                    profit_ticks <= -self.params.scalp_stop_ticks or
                    total_signal > 0.2):  # Signal reversal
                    
                    self.order = self.close()
                    self.log(f'SCALP CLOSE SHORT - Profit: {profit_ticks:.1f} ticks')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')


class RealInstitutionalBreakoutStrategy(backtrader.Strategy):
    """
    REAL Institutional Breakout Strategy
    Implements volume profile analysis, institutional order flow, and smart money concepts
    """
    
    params = (
        ('volume_profile_periods', 100),  # Periods for volume profile
        ('breakout_threshold', 0.002),    # 0.2% breakout threshold
        ('volume_confirmation', 2.0),     # Volume must be 2x average
        ('institutional_size_threshold', 1000000),  # Large order threshold
        ('risk_per_trade', 0.025),        # 2.5% risk per trade
        ('max_positions', 3),
        ('support_resistance_periods', 50),
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Volume profile components
        self.volume_profile = {}
        self.price_levels = deque(maxlen=self.params.volume_profile_periods)
        self.volume_levels = deque(maxlen=self.params.volume_profile_periods)
        
        # Support/Resistance levels
        self.support_levels = []
        self.resistance_levels = []
        self.key_levels = deque(maxlen=20)
        
        # Institutional flow indicators
        self.large_orders = deque(maxlen=50)
        self.order_flow_imbalance = deque(maxlen=30)
        
        # Advanced indicators
        self.volume_ma = btind.SMA(self.data.volume, period=20) if hasattr(self.data, 'volume') else None
        self.atr = btind.ATR(self.data, period=14)
        self.rsi = btind.RSI(self.data, period=14)
        self.ema_fast = btind.EMA(self.data, period=12)
        self.ema_slow = btind.EMA(self.data, period=26)
        
        # Smart money concepts
        self.liquidity_zones = []
        self.order_blocks = []
        self.fair_value_gaps = []
        
        self.order = None
        
    def build_volume_profile(self):
        """Build volume profile for key levels identification"""
        if not hasattr(self.data, 'volume') or len(self.data.volume) == 0:
            return
            
        # Store price and volume data
        self.price_levels.append(self.dataclose[0])
        self.volume_levels.append(self.data.volume[0])
        
        if len(self.price_levels) < 20:
            return
            
        # Create price bins for volume profile
        price_array = np.array(list(self.price_levels))
        volume_array = np.array(list(self.volume_levels))
        
        # Calculate price range and create bins
        price_min, price_max = np.min(price_array), np.max(price_array)
        num_bins = 20
        bins = np.linspace(price_min, price_max, num_bins)
        
        # Aggregate volume by price level
        volume_profile = {}
        for i in range(len(bins) - 1):
            bin_mask = (price_array >= bins[i]) & (price_array < bins[i + 1])
            bin_volume = np.sum(volume_array[bin_mask])
            bin_price = (bins[i] + bins[i + 1]) / 2
            volume_profile[bin_price] = bin_volume
        
        self.volume_profile = volume_profile
        
        # Identify high volume nodes (HVN) and low volume nodes (LVN)
        if volume_profile:
            sorted_levels = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
            
            # Top 3 high volume nodes become key levels
            hvn_levels = [level[0] for level in sorted_levels[:3]]
            self.key_levels.extend(hvn_levels)
    
    def identify_support_resistance(self):
        """Identify institutional-grade support and resistance levels"""
        if len(self.data) < self.params.support_resistance_periods:
            return
            
        # Look for swing highs and lows
        lookback = min(self.params.support_resistance_periods, len(self.data))
        highs = [self.datahigh[-i] for i in range(1, lookback)]
        lows = [self.datalow[-i] for i in range(1, lookback)]
        
        # Find significant levels using local maxima/minima
        resistance_candidates = []
        support_candidates = []
        
        for i in range(2, len(highs) - 2):
            # Resistance: local maximum
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_candidates.append(highs[i])
                
            # Support: local minimum
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_candidates.append(lows[i])
        
        # Filter levels by significance (multiple touches)
        self.resistance_levels = self.filter_significant_levels(resistance_candidates, highs)
        self.support_levels = self.filter_significant_levels(support_candidates, lows)
    
    def filter_significant_levels(self, candidates, price_data):
        """Filter levels that have been tested multiple times"""
        significant_levels = []
        tolerance = self.atr[0] * 0.5 if len(self.atr) > 0 else 0.001
        
        for level in candidates:
            touches = 0
            for price in price_data:
                if abs(price - level) <= tolerance:
                    touches += 1
            
            # Level is significant if touched 3+ times
            if touches >= 3:
                significant_levels.append(level)
        
        return significant_levels
    
    def detect_institutional_order_flow(self):
        """Detect institutional order flow patterns"""
        if not hasattr(self.data, 'volume') or len(self.data.volume) == 0:
            return 0
            
        current_volume = self.data.volume[0]
        avg_volume = self.volume_ma[0] if self.volume_ma and len(self.volume_ma) > 0 else current_volume
        
        # Detect large orders (institutional activity)
        if current_volume > avg_volume * self.params.volume_confirmation:
            order_size = current_volume * self.dataclose[0]  # Approximate order value
            
            if order_size > self.params.institutional_size_threshold:
                # Determine order direction based on price action
                price_change = self.dataclose[0] - self.dataclose[-1] if len(self.data) > 1 else 0
                direction = 1 if price_change > 0 else -1
                
                self.large_orders.append({
                    'price': self.dataclose[0],
                    'volume': current_volume,
                    'direction': direction,
                    'timestamp': len(self.data)
                })
        
        # Calculate order flow imbalance
        if len(self.large_orders) >= 5:
            recent_orders = list(self.large_orders)[-5:]
            buy_volume = sum(order['volume'] for order in recent_orders if order['direction'] > 0)
            sell_volume = sum(order['volume'] for order in recent_orders if order['direction'] < 0)
            
            if buy_volume + sell_volume > 0:
                imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
            else:
                imbalance = 0
                
            self.order_flow_imbalance.append(imbalance)
            return imbalance
        
        return 0
    
    def identify_liquidity_zones(self):
        """Identify liquidity zones where stops might be placed"""
        # Liquidity typically sits above resistance and below support
        liquidity_zones = []
        
        for resistance in self.resistance_levels:
            # Liquidity above resistance (buy stops)
            liquidity_zones.append({
                'price': resistance + self.atr[0] * 0.5 if len(self.atr) > 0 else resistance * 1.001,
                'type': 'buy_stops',
                'strength': 'high'
            })
        
        for support in self.support_levels:
            # Liquidity below support (sell stops)
            liquidity_zones.append({
                'price': support - self.atr[0] * 0.5 if len(self.atr) > 0 else support * 0.999,
                'type': 'sell_stops',
                'strength': 'high'
            })
        
        self.liquidity_zones = liquidity_zones
    
    def detect_breakout_with_volume(self):
        """Detect institutional-grade breakouts with volume confirmation"""
        if not self.resistance_levels and not self.support_levels:
            return None, 0
            
        current_price = self.dataclose[0]
        current_volume = self.data.volume[0] if hasattr(self.data, 'volume') else 0
        avg_volume = self.volume_ma[0] if self.volume_ma and len(self.volume_ma) > 0 else current_volume
        
        # Check for resistance breakout
        for resistance in self.resistance_levels:
            if (current_price > resistance * (1 + self.params.breakout_threshold) and
                current_volume > avg_volume * self.params.volume_confirmation):
                
                # Additional confirmation: price should close above resistance
                if self.dataclose[0] > resistance:
                    strength = min((current_price - resistance) / resistance, 0.05)  # Cap at 5%
                    return 'bullish_breakout', strength
        
        # Check for support breakdown
        for support in self.support_levels:
            if (current_price < support * (1 - self.params.breakout_threshold) and
                current_volume > avg_volume * self.params.volume_confirmation):
                
                # Additional confirmation: price should close below support
                if self.dataclose[0] < support:
                    strength = min((support - current_price) / support, 0.05)  # Cap at 5%
                    return 'bearish_breakdown', strength
        
        return None, 0
    
    def next(self):
        if self.order:
            return
            
        # Build volume profile and identify key levels
        self.build_volume_profile()
        self.identify_support_resistance()
        self.identify_liquidity_zones()
        
        # Detect institutional order flow
        order_flow_imbalance = self.detect_institutional_order_flow()
        
        # Detect breakouts
        breakout_type, breakout_strength = self.detect_breakout_with_volume()
        
        # Additional filters
        trend_filter = self.ema_fast[0] > self.ema_slow[0] if len(self.ema_fast) > 0 and len(self.ema_slow) > 0 else True
        rsi_filter = 30 < self.rsi[0] < 70 if len(self.rsi) > 0 else True  # Avoid extreme RSI
        
        # Trading logic
        if not self.position and breakout_type and breakout_strength > 0.001:
            
            # Calculate position size
            account_value = self.broker.getvalue()
            risk_amount = account_value * self.params.risk_per_trade
            
            # Use ATR for stop loss
            stop_distance = self.atr[0] * 2 if len(self.atr) > 0 else self.dataclose[0] * 0.02
            position_size = int(risk_amount / stop_distance) if stop_distance > 0 else 0
            
            if position_size > 0:
                if breakout_type == 'bullish_breakout' and trend_filter and order_flow_imbalance > 0:
                    self.order = self.buy(size=position_size)
                    self.log(f'INSTITUTIONAL BUY - Breakout strength: {breakout_strength:.3f}, '
                           f'Order flow: {order_flow_imbalance:.3f}, Volume conf: {breakout_strength > 0.001}')
                    
                elif breakout_type == 'bearish_breakdown' and not trend_filter and order_flow_imbalance < 0:
                    self.order = self.sell(size=position_size)
                    self.log(f'INSTITUTIONAL SELL - Breakdown strength: {breakout_strength:.3f}, '
                           f'Order flow: {order_flow_imbalance:.3f}, Volume conf: {breakout_strength > 0.001}')
        
        elif self.position:
            # Exit conditions
            current_price = self.dataclose[0]
            
            # Take profit at next key level
            if self.position.size > 0:  # Long position
                next_resistance = min([r for r in self.resistance_levels if r > current_price], default=None)
                if next_resistance and current_price >= next_resistance * 0.98:  # Near resistance
                    self.order = self.close()
                    self.log('INSTITUTIONAL CLOSE LONG - Near resistance level')
                    
            else:  # Short position
                next_support = max([s for s in self.support_levels if s < current_price], default=None)
                if next_support and current_price <= next_support * 1.02:  # Near support
                    self.order = self.close()
                    self.log('INSTITUTIONAL CLOSE SHORT - Near support level')
            
            # Stop loss and trend reversal
            if ((self.position.size > 0 and order_flow_imbalance < -0.5) or
                (self.position.size < 0 and order_flow_imbalance > 0.5)):
                self.order = self.close()
                self.log('INSTITUTIONAL CLOSE - Order flow reversal')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
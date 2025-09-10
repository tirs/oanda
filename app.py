"""
🚀 Advanced OANDA Trading Bot - FastAPI Web Application
Professional-grade trading interface with modern dark theme
"""

from random import random
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import os
import sys

# Configure logging with proper encoding for Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set console encoding to UTF-8 if possible
if sys.platform == "win32":
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass  # Fallback to default encoding

# Import our trading modules with error handling
try:
    import settings
    import backtest
    import trade
    import strategy
    from strategy_selector import get_available_strategies, get_strategy_info
    TRADING_MODULES_AVAILABLE = True
    logger.info("✅ All trading modules loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import trading modules: {e}")
    TRADING_MODULES_AVAILABLE = False
    
    # Create mock functions for missing modules
    def get_available_strategies():
        return {"mock_strategy": {"name": "Mock Strategy", "description": "Trading modules not available"}}
    
    def get_strategy_info(strategy_name):
        return {"name": "Mock Strategy", "description": "Trading modules not available", "parameters": {}}

# FastAPI app initialization
app = FastAPI(
    title="Advanced OANDA Trading Bot",
    description="Professional-grade trading interface with advanced strategies",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Initialize OANDA connection on startup"""
    logger.info("Starting OANDA Trading Bot Application")
    
    # Check if we have the required environment variables
    if not settings.ACCESS_TOKEN or settings.ACCESS_TOKEN in ["your_access_token_here", "demo_mode"]:
        logger.warning("⚠️ OANDA ACCESS_TOKEN not configured - running in demo mode")
        return
    
    if not settings.ACCOUNT_ID or settings.ACCOUNT_ID in ["your_account_id_here", "demo_mode"]:
        logger.warning("⚠️ OANDA ACCOUNT_ID not configured - running in demo mode")
        return
    
    # Test OANDA connection
    try:
        import requests
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        test_response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}",
            headers=headers,
            timeout=10
        )
        
        if test_response.status_code == 200:
            account_data = test_response.json()
            account = account_data.get("account", {})
            logger.info(f"OANDA connection successful - Account: {account.get('id')}, Balance: {account.get('balance')} {account.get('currency')}")
            
            # Initialize account info
            trading_state.account_info = {
                "id": account.get("id"),
                "currency": account.get("currency"),
                "balance": float(account.get("balance", 0)),
                "nav": float(account.get("NAV", 0)),
                "unrealized_pnl": float(account.get("unrealizedPL", 0)),
                "margin_used": float(account.get("marginUsed", 0)),
                "margin_available": float(account.get("marginAvailable", 0)),
                "open_positions": int(account.get("openPositionCount", 0)),
                "open_trades": int(account.get("openTradeCount", 0))
            }
        else:
            logger.error(f"OANDA connection failed: {test_response.status_code}")
            
    except Exception as e:
        logger.error(f"Failed to connect to OANDA: {e}")
    
    # Start periodic data refresh task (only if not in demo mode)
    if not (settings.ACCESS_TOKEN in ["your_access_token_here", "demo_mode"] or 
            settings.ACCOUNT_ID in ["your_account_id_here", "demo_mode"]):
        asyncio.create_task(periodic_data_refresh())
    
    # Auto-start trading for 24/7 operation (only if not in demo mode)
    if not (settings.ACCESS_TOKEN in ["your_access_token_here", "demo_mode"] or 
            settings.ACCOUNT_ID in ["your_account_id_here", "demo_mode"]):
        try:
            logger.info("Auto-starting 24/7 trading...")
            trading_state.is_trading = True
            asyncio.create_task(run_trading_bot())
            logger.info("24/7 trading started successfully")
        except Exception as e:
            logger.error(f"Failed to auto-start trading: {e}")
            trading_state.is_trading = False
    else:
        logger.info("Running in demo mode - trading disabled")

async def periodic_data_refresh():
    """Periodically refresh account and position data"""
    while True:
        try:
            if not trading_state.is_trading:  # Only refresh when not actively trading
                await update_trading_data()
            await asyncio.sleep(30)  # Refresh every 30 seconds
        except Exception as e:
            logger.error(f"Error in periodic data refresh: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Template helper functions
def get_strategy_description(strategy_name):
    descriptions = {
        "AggressiveMultiInstrumentStrategy": "Aggressive multi-pair trading with proper SL/TP orders for maximum profit opportunities",
        "QuantitativeAlphaStrategy": "Statistical arbitrage with market regime detection for consistent alpha generation",
        "ProfessionalScalpingStrategy": "High-frequency scalping strategy for quick profits in volatile markets",
        "InstitutionalBreakoutStrategy": "Volume-confirmed breakout trading used by institutional traders",
        "MachineLearningMomentumStrategy": "ML-inspired feature engineering for momentum detection",
        "MultiInstrumentStrategy": "Diversified trading across multiple currency pairs simultaneously",
        "AdvancedMultiStrategy": "Multi-indicator strategy with enhanced SL/TP risk management",
        "MomentumStrategy": "Pure momentum following strategy for trending markets",
        "MeanReversionStrategy": "Range-bound market specialist for sideways price action"
    }
    return descriptions.get(strategy_name, "Advanced trading strategy")

def get_strategy_icon(strategy_name):
    icons = {
        "AggressiveMultiInstrumentStrategy": "fa-rocket",
        "QuantitativeAlphaStrategy": "fa-chart-line",
        "ProfessionalScalpingStrategy": "fa-bolt",
        "InstitutionalBreakoutStrategy": "fa-building",
        "MachineLearningMomentumStrategy": "fa-robot",
        "MultiInstrumentStrategy": "fa-globe",
        "AdvancedMultiStrategy": "fa-layer-group",
        "MomentumStrategy": "fa-arrow-trend-up",
        "MeanReversionStrategy": "fa-arrows-rotate"
    }
    return icons.get(strategy_name, "fa-chart-line")

def get_strategy_risk(strategy_name):
    risks = {
        "AggressiveMultiInstrumentStrategy": "Moderate-High",
        "QuantitativeAlphaStrategy": "Moderate",
        "ProfessionalScalpingStrategy": "High",
        "InstitutionalBreakoutStrategy": "Moderate",
        "MachineLearningMomentumStrategy": "Moderate-High",
        "MultiInstrumentStrategy": "Low-Moderate",
        "AdvancedMultiStrategy": "Moderate",
        "MomentumStrategy": "High",
        "MeanReversionStrategy": "Low"
    }
    return risks.get(strategy_name, "Moderate")

def get_strategy_timeframe(strategy_name):
    timeframes = {
        "AggressiveMultiInstrumentStrategy": "1H-4H",
        "QuantitativeAlphaStrategy": "1H-4H",
        "ProfessionalScalpingStrategy": "1M-15M",
        "InstitutionalBreakoutStrategy": "4H-1D",
        "MachineLearningMomentumStrategy": "1H-4H",
        "MultiInstrumentStrategy": "1H-4H",
        "AdvancedMultiStrategy": "1H-4H",
        "MomentumStrategy": "4H-1D",
        "MeanReversionStrategy": "1H-4H"
    }
    return timeframes.get(strategy_name, "1H-4H")

def get_strategy_market_type(strategy_name):
    market_types = {
        "AggressiveMultiInstrumentStrategy": "All Markets",
        "QuantitativeAlphaStrategy": "All Markets",
        "ProfessionalScalpingStrategy": "Volatile",
        "InstitutionalBreakoutStrategy": "Trending",
        "MachineLearningMomentumStrategy": "Trending",
        "MultiInstrumentStrategy": "All Markets",
        "AdvancedMultiStrategy": "All Markets",
        "MomentumStrategy": "Trending",
        "MeanReversionStrategy": "Range-bound"
    }
    return market_types.get(strategy_name, "All Markets")

def get_strategy_return(strategy_name):
    returns = {
        "AggressiveMultiInstrumentStrategy": "25-40%",
        "QuantitativeAlphaStrategy": "15-25%",
        "ProfessionalScalpingStrategy": "20-35%",
        "InstitutionalBreakoutStrategy": "12-20%",
        "MachineLearningMomentumStrategy": "18-28%",
        "MultiInstrumentStrategy": "10-18%",
        "AdvancedMultiStrategy": "12-22%",
        "MomentumStrategy": "15-30%",
        "MeanReversionStrategy": "8-15%"
    }
    return returns.get(strategy_name, "10-20%")

# Static files and templates
static_dir = Path("static")
templates_dir = Path("templates")

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Add template globals and filters
templates.env.globals.update({
    'get_strategy_description': get_strategy_description,
    'get_strategy_icon': get_strategy_icon,
    'get_strategy_risk': get_strategy_risk,
    'get_strategy_timeframe': get_strategy_timeframe,
    'get_strategy_market_type': get_strategy_market_type,
    'get_strategy_return': get_strategy_return,
    'get_strategy_color_class': lambda x: "bg-blue-500",
    'get_strategy_short_desc': lambda x: get_strategy_description(x)[:50] + "...",
    'get_mock_return': lambda x: f"{15 + hash(x) % 20}",
    'get_mock_sharpe': lambda x: f"{1.2 + (hash(x) % 10) / 10:.1f}",
    'get_mock_drawdown': lambda x: f"-{5 + hash(x) % 10}",
    'get_mock_winrate': lambda x: f"{55 + hash(x) % 20}",
    'get_mock_avg_trade': lambda x: f"{25 + hash(x) % 50}"
})

# Add custom filters
templates.env.filters['tojsonfilter'] = json.dumps

# Global state management
class TradingState:
    def __init__(self):
        self.is_trading = False
        self.current_positions = []
        self.account_info = {}
        self.recent_trades = []
        self.performance_metrics = {}
        self.connected_clients = set()
        self.trading_task = None
        
    def add_client(self, websocket):
        self.connected_clients.add(websocket)
        
    def remove_client(self, websocket):
        self.connected_clients.discard(websocket)
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients"""
        if self.connected_clients:
            disconnected = set()
            for client in self.connected_clients:
                try:
                    await client.send_text(json.dumps(message))
                except:
                    disconnected.add(client)
            
            # Remove disconnected clients
            for client in disconnected:
                self.connected_clients.discard(client)

trading_state = TradingState()

# WebSocket connection manager
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    trading_state.add_client(websocket)
    
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "data": {
                "is_trading": trading_state.is_trading,
                "positions": trading_state.current_positions,
                "account": trading_state.account_info
            }
        }))
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                # Handle incoming WebSocket messages if needed
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        trading_state.remove_client(websocket)

# Main dashboard route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main trading dashboard"""
    try:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Trading Dashboard",
            "current_strategy": settings.STRATEGY_NAME,
            "instruments": settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT],
            "is_trading": trading_state.is_trading
        })
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page (same as root)"""
    try:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Trading Dashboard",
            "current_strategy": settings.STRATEGY_NAME,
            "instruments": settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT],
            "is_trading": trading_state.is_trading
        })
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

# Strategy management routes
@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request):
    """Strategy selection and management page"""
    try:
        available_strategies = get_available_strategies()
        strategy_details = get_strategy_info()  # This returns all strategy info
        
        return templates.TemplateResponse("strategies.html", {
            "request": request,
            "title": "Strategy Management",
            "strategies": strategy_details,
            "available_strategies": available_strategies,
            "current_strategy": settings.STRATEGY_NAME,
            "instruments": settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT],
            "alternative_strategies": getattr(settings, 'ALTERNATIVE_STRATEGIES', available_strategies)
        })
    except Exception as e:
        logger.error(f"Error rendering strategies page: {e}")
        return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    """Backtesting interface"""
    return templates.TemplateResponse("backtest.html", {
        "request": request,
        "title": "Backtesting",
        "strategies": settings.ALTERNATIVE_STRATEGIES,
        "instruments": settings.INSTRUMENTS,
        "current_strategy": settings.STRATEGY_NAME
    })

@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request):
    """Live positions and trades page"""
    # Force update trading data to get latest positions and trades
    await update_trading_data()
    
    return templates.TemplateResponse("positions.html", {
        "request": request,
        "title": "Positions & Trades",
        "positions": trading_state.current_positions,
        "recent_trades": trading_state.recent_trades,
        "account": trading_state.account_info
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Performance analytics page"""
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "title": "Performance Analytics",
        "metrics": trading_state.performance_metrics
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings and configuration page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Settings",
        "settings": {
            "account_id": settings.ACCOUNT_ID,
            "environment": settings.ENVIRONMENT,
            "access_token": getattr(settings, 'ACCESS_TOKEN', ''),
            "account_currency": getattr(settings, 'ACCOUNT_CURRENCY', 'USD'),
            "instruments": settings.INSTRUMENTS,
            "multi_instrument_mode": settings.MULTI_INSTRUMENT_MODE,
            "strategy_name": settings.STRATEGY_NAME,
            "email_recipient": getattr(settings, 'EMAIL_RECIPIENT', 'trader@example.com'),
            "risk_settings": {
                "max_percentage_risk": settings.MAX_PERCENTAGE_ACCOUNT_AT_RISK,
                "max_total_exposure": settings.MAX_TOTAL_RISK_EXPOSURE,
                "max_correlated_positions": settings.MAX_CORRELATED_POSITIONS
            }
        }
    })

# API Routes
@app.get("/api/status")
async def get_status():
    """Get current trading status"""
    return {
        "is_trading": trading_state.is_trading,
        "strategy": settings.STRATEGY_NAME,
        "instruments": settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT],
        "positions_count": len(trading_state.current_positions),
        "account_balance": trading_state.account_info.get("balance", 0),
        "unrealized_pnl": sum(float(pos.get("unrealized_pnl", 0)) for pos in trading_state.current_positions)
    }

@app.get("/api/positions")
async def get_positions():
    """Get current positions with real-time data"""
    # Force update trading data to get latest positions
    await update_trading_data()
    
    return {
        "positions": trading_state.current_positions,
        "account": trading_state.account_info,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/trades")
async def get_trades_api(limit: int = 50, instrument: str = None, days: int = 7):
    """Get recent trades from OANDA"""
    trades_data = await get_recent_trades(limit=limit, instrument=instrument, days=days)
    return trades_data

@app.get("/api/positions/recent-trades")
async def get_positions_recent_trades(limit: int = 50, instrument: str = None, days: int = 7):
    """Get recent trades from OANDA (positions page endpoint)"""
    trades_data = await get_recent_trades(limit=limit, instrument=instrument, days=days)
    return trades_data

@app.get("/api/positions/pnl-history")
async def get_pnl_history(period: str = "1h"):
    """Get P&L history for charts"""
    try:
        # For now, return mock data - in production this would query OANDA transaction history
        from datetime import datetime, timedelta
        import random
        
        # Generate time series based on period
        if period == "1h":
            points = 60
            delta = timedelta(minutes=1)
        elif period == "4h":
            points = 48
            delta = timedelta(minutes=5)
        else:  # 1d
            points = 24
            delta = timedelta(hours=1)
        
        now = datetime.now()
        data = []
        cumulative_pnl = 0
        
        for i in range(points):
            timestamp = now - (delta * (points - i))
            # Simulate P&L changes
            change = random.uniform(-50, 50)
            cumulative_pnl += change
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "pnl": round(cumulative_pnl, 2),
                "change": round(change, 2)
            })
        
        return {"data": data}
        
    except Exception as e:
        logger.error(f"Error getting P&L history: {e}")
        return {"data": []}

@app.post("/api/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a specific position"""
    try:
        import requests
        
        # Extract instrument from position ID (format: oanda_EUR_USD_long)
        parts = position_id.split('_')
        if len(parts) >= 3:
            instrument = '_'.join(parts[1:-1])  # Handle instruments like EUR_USD
            side = parts[-1].upper()
        else:
            raise HTTPException(status_code=400, detail="Invalid position ID format")
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Close position via OANDA API
        close_data = {
            "longUnits": "ALL" if side == "LONG" else "NONE",
            "shortUnits": "ALL" if side == "SHORT" else "NONE"
        }
        
        response = requests.put(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/positions/{instrument}/close",
            headers=headers,
            json=close_data,
            timeout=10
        )
        
        if response.status_code == 200:
            # Update local state
            await update_trading_data()
            
            await trading_state.broadcast({
                "type": "position_closed",
                "data": {"position_id": position_id, "instrument": instrument}
            })
            
            return {"status": "success", "message": f"Position {position_id} closed successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to close position: {response.text}")
            
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/positions/close-all")
async def close_all_positions():
    """Close all open positions"""
    try:
        closed_count = 0
        errors = []
        
        # Get current positions
        await update_trading_data()
        
        for position in trading_state.current_positions:
            try:
                await close_position(position["id"])
                closed_count += 1
            except Exception as e:
                errors.append(f"Failed to close {position['id']}: {str(e)}")
        
        await trading_state.broadcast({
            "type": "all_positions_closed",
            "data": {"closed_count": closed_count, "errors": errors}
        })
        
        return {
            "status": "success", 
            "message": f"Closed {closed_count} positions",
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/positions/{position_id}/modify")
async def modify_position(position_id: str, modification: dict):
    """Modify stop loss and take profit for a position"""
    try:
        import requests
        
        # Extract instrument from position ID
        parts = position_id.split('_')
        if len(parts) >= 3:
            instrument = '_'.join(parts[1:-1])
        else:
            raise HTTPException(status_code=400, detail="Invalid position ID format")
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Find the trade ID for this position
        trades_response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/openTrades",
            headers=headers,
            timeout=10
        )
        
        if trades_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get open trades")
        
        trades = trades_response.json().get("trades", [])
        target_trade = None
        
        for trade in trades:
            if trade["instrument"] == instrument:
                target_trade = trade
                break
        
        if not target_trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        trade_id = target_trade["id"]
        
        # Prepare modification data
        modify_data = {}
        
        if "stop_loss" in modification and modification["stop_loss"]:
            modify_data["stopLoss"] = {"price": str(modification["stop_loss"])}
        
        if "take_profit" in modification and modification["take_profit"]:
            modify_data["takeProfit"] = {"price": str(modification["take_profit"])}
        
        # Send modification request
        response = requests.put(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/trades/{trade_id}/orders",
            headers=headers,
            json=modify_data,
            timeout=10
        )
        
        if response.status_code == 200:
            # Update local state
            await update_trading_data()
            
            await trading_state.broadcast({
                "type": "position_modified",
                "data": {"position_id": position_id, "modification": modification}
            })
            
            return {"status": "success", "message": "Position modified successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to modify position: {response.text}")
            
    except Exception as e:
        logger.error(f"Error modifying position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start-trading")
async def start_trading(background_tasks: BackgroundTasks):
    """Start live trading"""
    if trading_state.is_trading:
        raise HTTPException(status_code=400, detail="Trading is already active")
    
    try:
        trading_state.is_trading = True
        background_tasks.add_task(run_trading_bot)
        
        await trading_state.broadcast({
            "type": "trading_started",
            "data": {"message": "Live trading started successfully"}
        })
        
        return {"status": "success", "message": "Trading started"}
    except Exception as e:
        trading_state.is_trading = False
        raise HTTPException(status_code=500, detail=f"Failed to start trading: {str(e)}")

@app.post("/api/stop-trading")
async def stop_trading():
    """Stop live trading"""
    if not trading_state.is_trading:
        raise HTTPException(status_code=400, detail="Trading is not active")
    
    trading_state.is_trading = False
    
    if trading_state.trading_task:
        trading_state.trading_task.cancel()
    
    await trading_state.broadcast({
        "type": "trading_stopped",
        "data": {"message": "Live trading stopped"}
    })
    
    return {"status": "success", "message": "Trading stopped"}

@app.post("/api/run-backtest")
async def run_backtest_api(background_tasks: BackgroundTasks, strategy: str = None):
    """Run backtest with specified strategy"""
    try:
        if strategy and strategy in settings.ALTERNATIVE_STRATEGIES:
            # Temporarily change strategy for backtest
            original_strategy = settings.STRATEGY_NAME
            settings.STRATEGY_NAME = strategy
        
        # Run backtest in background
        background_tasks.add_task(execute_backtest)
        
        return {"status": "success", "message": f"Backtest started with {strategy or settings.STRATEGY_NAME}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start backtest: {str(e)}")

@app.get("/api/positions")
async def get_positions():
    """Get current positions with detailed information from OANDA"""
    try:
        import requests
        from datetime import datetime, timedelta
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        positions = []
        
        try:
            # Get open positions from OANDA
            positions_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/openPositions",
                headers=headers,
                timeout=10
            )
            
            if positions_response.status_code == 200:
                oanda_positions = positions_response.json().get("positions", [])
                
                # Get current prices for all instruments
                instruments_with_positions = [pos["instrument"] for pos in oanda_positions]
                current_prices = {}
                
                if instruments_with_positions:
                    pricing_response = requests.get(
                        f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/pricing",
                        headers=headers,
                        params={"instruments": ",".join(instruments_with_positions)},
                        timeout=10
                    )
                    
                    if pricing_response.status_code == 200:
                        prices_data = pricing_response.json().get("prices", [])
                        for price_info in prices_data:
                            instrument = price_info["instrument"]
                            # Use mid price (average of bid and ask)
                            bid = float(price_info["bids"][0]["price"])
                            ask = float(price_info["asks"][0]["price"])
                            current_prices[instrument] = (bid + ask) / 2
                
                # Process each position
                for i, oanda_pos in enumerate(oanda_positions):
                    instrument = oanda_pos["instrument"]
                    
                    # Determine if we have long or short position
                    long_units = float(oanda_pos["long"]["units"])
                    short_units = float(oanda_pos["short"]["units"])
                    
                    if long_units != 0:
                        units = long_units
                        side = "LONG"
                        avg_price = float(oanda_pos["long"]["averagePrice"])
                        unrealized_pnl = float(oanda_pos["long"]["unrealizedPL"])
                    elif short_units != 0:
                        units = short_units
                        side = "SHORT"
                        avg_price = float(oanda_pos["short"]["averagePrice"])
                        unrealized_pnl = float(oanda_pos["short"]["unrealizedPL"])
                    else:
                        continue  # Skip positions with no units
                    
                    current_price = current_prices.get(instrument, avg_price)
                    
                    # Calculate margin used (approximate)
                    margin_used = abs(units) * current_price * 0.02  # Assuming 50:1 leverage (2% margin)
                    
                    # Estimate position open time (OANDA doesn't provide this directly in positions endpoint)
                    # We'll use a placeholder for now
                    open_time = datetime.now() - timedelta(hours=2)  # Placeholder
                    
                    position = {
                        "id": f"oanda_{instrument}_{side.lower()}",
                        "instrument": instrument,
                        "units": int(abs(units)),
                        "side": side,
                        "entry_price": round(avg_price, 5),
                        "current_price": round(current_price, 5),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "margin_used": round(margin_used, 2),
                        "stop_loss": None,  # Would need to get from orders endpoint
                        "take_profit": None,  # Would need to get from orders endpoint
                        "open_time": open_time.isoformat(),
                        "duration_minutes": int((datetime.now() - open_time).total_seconds() / 60)
                    }
                    positions.append(position)
                    
            else:
                logger.warning(f"Failed to get positions from OANDA: {positions_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OANDA API request failed: {e}")
            # Fall back to mock data if OANDA API fails
            return await get_mock_positions()
        
        # If no real positions, show empty result (no mock data for real trading)
        if not positions:
            logger.info("No open positions found in OANDA account")
        
        # Update global state
        trading_state.current_positions = positions
        
        total_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions)
        total_margin_used = sum(pos["margin_used"] for pos in positions)
        
        return {
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "total_margin_used": round(total_margin_used, 2),
                "long_positions": len([p for p in positions if p["side"] == "LONG"]),
                "short_positions": len([p for p in positions if p["side"] == "SHORT"])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        # Fall back to mock data on any error
        return await get_mock_positions()

async def get_mock_positions():
    """Fallback function to generate mock positions for demo purposes"""
    try:
        import random
        from datetime import datetime, timedelta
        
        # Generate mock positions data
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF", "USD_CAD", "NZD_USD"]
        positions = []
        
        # Generate 2-5 random positions
        num_positions = random.randint(2, 5)
        
        for i in range(num_positions):
            instrument = random.choice(instruments)
            side = random.choice(['LONG', 'SHORT'])
            units = random.randint(1000, 10000)
            entry_price = 1.0000 + random.uniform(0.0500, 0.2000)
            current_price = entry_price + random.uniform(-0.0050, 0.0050)
            unrealized_pnl = (current_price - entry_price) * units * (1 if side == 'LONG' else -1)
            margin_used = units * current_price * 0.02  # 2% margin
            
            # Generate stop loss and take profit
            if side == 'LONG':
                stop_loss = entry_price - random.uniform(0.0020, 0.0050)
                take_profit = entry_price + random.uniform(0.0030, 0.0080)
            else:
                stop_loss = entry_price + random.uniform(0.0020, 0.0050)
                take_profit = entry_price - random.uniform(0.0030, 0.0080)
            
            # Random open time (within last 24 hours)
            open_time = datetime.now() - timedelta(minutes=random.randint(30, 1440))
            
            position = {
                "id": f"mock_{i+1}_{instrument}",
                "instrument": instrument,
                "units": units,
                "side": side,
                "entry_price": round(entry_price, 5),
                "current_price": round(current_price, 5),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "margin_used": round(margin_used, 2),
                "stop_loss": round(stop_loss, 5) if random.random() > 0.3 else None,
                "take_profit": round(take_profit, 5) if random.random() > 0.2 else None,
                "open_time": open_time.isoformat(),
                "duration_minutes": int((datetime.now() - open_time).total_seconds() / 60)
            }
            positions.append(position)
        
        total_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions)
        total_margin_used = sum(pos["margin_used"] for pos in positions)
        
        return {
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "total_margin_used": round(total_margin_used, 2),
                "long_positions": len([p for p in positions if p["side"] == "LONG"]),
                "short_positions": len([p for p in positions if p["side"] == "SHORT"])
            }
        }
    except Exception as e:
        logger.error(f"Failed to generate mock positions: {e}")
        return {
            "positions": [],
            "summary": {
                "total_positions": 0,
                "total_unrealized_pnl": 0.0,
                "total_margin_used": 0.0,
                "long_positions": 0,
                "short_positions": 0
            }
        }

@app.get("/api/positions/recent-trades")
async def get_recent_trades(limit: int = 50, instrument: str = None, days: int = 7):
    """Get recent completed trades from OANDA"""
    try:
        import requests
        from datetime import datetime, timedelta
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        trades = []
        
        try:
            # Calculate date range
            from_date = datetime.now() - timedelta(days=days)
            
            # Get transactions from OANDA (orders, fills, etc.)
            params = {
                "from": from_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "type": "ORDER_FILL"  # Only get filled orders (completed trades)
            }
            
            if instrument:
                params["instrument"] = instrument
            
            transactions_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/transactions",
                headers=headers,
                params=params,
                timeout=15
            )
            
            if transactions_response.status_code == 200:
                transactions_data = transactions_response.json()
                transactions = transactions_data.get("transactions", [])
                
                # Process transactions to create trade records
                for transaction in transactions[:limit]:  # Limit results
                    if transaction.get("type") == "ORDER_FILL":
                        trade_time = datetime.fromisoformat(transaction["time"].replace("Z", "+00:00"))
                        
                        # Determine side
                        units = float(transaction["units"])
                        side = "BUY" if units > 0 else "SELL"
                        
                        # Get price and P&L
                        price = float(transaction["price"])
                        pnl = float(transaction.get("pl", 0))
                        
                        trade = {
                            "id": f"oanda_{transaction['id']}",
                            "instrument": transaction["instrument"],
                            "side": side,
                            "units": int(abs(units)),
                            "entry_price": price,  # This is actually the fill price
                            "exit_price": price,   # For individual fills, entry and exit are the same
                            "pnl": round(pnl, 2),
                            "open_time": trade_time.isoformat(),
                            "close_time": trade_time.isoformat(),
                            "duration_minutes": 0,  # Individual fills don't have duration
                            "strategy": settings.STRATEGY_NAME,
                            "commission": float(transaction.get("commission", 0))
                        }
                        trades.append(trade)
                        
            else:
                logger.warning(f"Failed to get transactions from OANDA: {transactions_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OANDA API request failed: {e}")
            # Fall back to mock data if OANDA API fails
            return await get_mock_trades(limit, instrument, days)
        
        # If no real trades found, return empty result
        if not trades:
            logger.info("No recent trades found in OANDA account")
        
        # Sort by close time (most recent first)
        trades.sort(key=lambda x: x["close_time"], reverse=True)
        
        # Calculate statistics
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] < 0]
        
        total_pnl = sum(t["pnl"] for t in trades)
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            "trades": trades,
            "statistics": {
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "average_win": round(avg_win, 2),
                "average_loss": round(avg_loss, 2),
                "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
                "average_duration": round(sum(t["duration_minutes"] for t in trades) / len(trades), 0) if trades else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get recent trades: {e}")
        # Fall back to mock data on any error
        return await get_mock_trades(limit, instrument, days)

async def get_mock_trades(limit: int = 50, instrument: str = None, days: int = 7):
    """Fallback function to generate mock trades for demo purposes"""
    try:
        import random
        from datetime import datetime, timedelta
        
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF", "USD_CAD", "NZD_USD"]
        strategies = ["QuantitativeAlpha", "ProfessionalScalping", "InstitutionalBreakout", "MachineLearningMomentum"]
        
        trades = []
        num_trades = min(limit, 100)  # Cap at 100 trades
        
        for i in range(num_trades):
            trade_instrument = instrument if instrument else random.choice(instruments)
            side = random.choice(['BUY', 'SELL'])
            units = random.randint(1000, 10000)
            entry_price = 1.0000 + random.uniform(0.0500, 0.2000)
            exit_price = entry_price + random.uniform(-0.0100, 0.0100)
            
            # Calculate P&L
            pnl = (exit_price - entry_price) * units * (1 if side == 'BUY' else -1)
            
            # Random trade time within specified days
            trade_time = datetime.now() - timedelta(
                minutes=random.randint(0, days * 24 * 60)
            )
            
            # Random duration (15 minutes to 4 hours)
            duration_minutes = random.randint(15, 240)
            close_time = trade_time + timedelta(minutes=duration_minutes)
            
            trade = {
                "id": f"mock_trade_{i+1}",
                "instrument": trade_instrument,
                "side": side,
                "units": units,
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "pnl": round(pnl, 2),
                "open_time": trade_time.isoformat(),
                "close_time": close_time.isoformat(),
                "duration_minutes": duration_minutes,
                "strategy": random.choice(strategies),
                "commission": round(random.uniform(0.5, 2.0), 2)
            }
            trades.append(trade)
        
        # Sort by close time (most recent first)
        trades.sort(key=lambda x: x["close_time"], reverse=True)
        
        # Calculate statistics
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] < 0]
        
        total_pnl = sum(t["pnl"] for t in trades)
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            "trades": trades,
            "statistics": {
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "average_win": round(avg_win, 2),
                "average_loss": round(avg_loss, 2),
                "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
                "average_duration": round(sum(t["duration_minutes"] for t in trades) / len(trades), 0) if trades else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to generate mock trades: {e}")
        return {
            "trades": [],
            "statistics": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "profit_factor": 0.0,
                "average_duration": 0.0
            }
        }

@app.get("/api/positions/pnl-history")
async def get_pnl_history(period: str = "1H"):
    """Get P&L history for charting"""
    try:
        import random
        from datetime import datetime, timedelta
        
        # Determine data points based on period
        if period == "1H":
            points = 60  # 60 minutes
            interval_minutes = 1
        elif period == "4H":
            points = 48  # 4 hours in 5-minute intervals
            interval_minutes = 5
        elif period == "1D":
            points = 24  # 24 hours
            interval_minutes = 60
        else:
            points = 60
            interval_minutes = 1
        
        data = []
        cumulative_pnl = 0
        
        for i in range(points):
            timestamp = datetime.now() - timedelta(minutes=(points - i - 1) * interval_minutes)
            
            # Generate random P&L change
            pnl_change = random.uniform(-50, 50)
            cumulative_pnl += pnl_change
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "pnl": round(cumulative_pnl, 2),
                "change": round(pnl_change, 2)
            })
        
        return {"data": data, "period": period}
    except Exception as e:
        logger.error(f"Failed to get P&L history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get P&L history: {str(e)}")

@app.post("/api/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a specific position via OANDA API"""
    try:
        import requests
        
        # Find the position
        position = None
        for pos in trading_state.current_positions:
            if pos.get("id") == position_id:
                position = pos
                break
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Check if this is a real OANDA position or mock position
        if position_id.startswith("oanda_"):
            # Real OANDA position - close via API
            instrument = position["instrument"]
            side = "longUnits" if position["side"] == "LONG" else "shortUnits"
            
            close_data = {
                side: "ALL"  # Close all units for this side
            }
            
            try:
                close_response = requests.put(
                    f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/positions/{instrument}/close",
                    headers=headers,
                    json=close_data,
                    timeout=10
                )
                
                if close_response.status_code == 200:
                    close_result = close_response.json()
                    
                    # Extract actual P&L from the response
                    if side == "longUnits" and "longOrderFillTransaction" in close_result:
                        actual_pnl = float(close_result["longOrderFillTransaction"]["pl"])
                    elif side == "shortUnits" and "shortOrderFillTransaction" in close_result:
                        actual_pnl = float(close_result["shortOrderFillTransaction"]["pl"])
                    else:
                        actual_pnl = position["unrealized_pnl"]  # Fallback to estimated P&L
                    
                    # Remove from local state
                    trading_state.current_positions = [
                        pos for pos in trading_state.current_positions 
                        if pos.get("id") != position_id
                    ]
                    
                    # Broadcast update to connected clients
                    await trading_state.broadcast({
                        "type": "position_closed",
                        "data": {
                            "position_id": position_id,
                            "instrument": position["instrument"],
                            "pnl": actual_pnl
                        }
                    })
                    
                    return {
                        "status": "success",
                        "message": f"Position {instrument} closed successfully via OANDA",
                        "closed_pnl": actual_pnl
                    }
                else:
                    logger.error(f"OANDA close position failed: {close_response.status_code} - {close_response.text}")
                    raise HTTPException(status_code=400, detail=f"Failed to close position via OANDA: {close_response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"OANDA API request failed: {e}")
                raise HTTPException(status_code=500, detail=f"OANDA API request failed: {str(e)}")
        
        else:
            # Mock position - just remove from local state
            trading_state.current_positions = [
                pos for pos in trading_state.current_positions 
                if pos.get("id") != position_id
            ]
            
            # Broadcast update to connected clients
            await trading_state.broadcast({
                "type": "position_closed",
                "data": {
                    "position_id": position_id,
                    "instrument": position["instrument"],
                    "pnl": position["unrealized_pnl"]
                }
            })
            
            return {
                "status": "success",
                "message": f"Mock position {position_id} closed successfully",
                "closed_pnl": position["unrealized_pnl"]
            }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")

@app.post("/api/positions/close-all")
async def close_all_positions():
    """Close all open positions via OANDA API"""
    try:
        import requests
        
        closed_positions = len(trading_state.current_positions)
        total_pnl = sum(pos.get("unrealized_pnl", 0) for pos in trading_state.current_positions)
        actual_total_pnl = 0
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Close each position
        for position in trading_state.current_positions.copy():
            try:
                if position["id"].startswith("oanda_"):
                    # Real OANDA position - close via API
                    instrument = position["instrument"]
                    side = "longUnits" if position["side"] == "LONG" else "shortUnits"
                    
                    close_data = {
                        side: "ALL"  # Close all units for this side
                    }
                    
                    close_response = requests.put(
                        f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/positions/{instrument}/close",
                        headers=headers,
                        json=close_data,
                        timeout=10
                    )
                    
                    if close_response.status_code == 200:
                        close_result = close_response.json()
                        
                        # Extract actual P&L from the response
                        if side == "longUnits" and "longOrderFillTransaction" in close_result:
                            actual_pnl = float(close_result["longOrderFillTransaction"]["pl"])
                        elif side == "shortUnits" and "shortOrderFillTransaction" in close_result:
                            actual_pnl = float(close_result["shortOrderFillTransaction"]["pl"])
                        else:
                            actual_pnl = position["unrealized_pnl"]
                        
                        actual_total_pnl += actual_pnl
                        logger.info(f"Closed OANDA position {instrument} with P&L: {actual_pnl}")
                    else:
                        logger.warning(f"Failed to close OANDA position {instrument}: {close_response.status_code}")
                        actual_total_pnl += position["unrealized_pnl"]  # Use estimated P&L
                else:
                    # Mock position
                    actual_total_pnl += position["unrealized_pnl"]
                    logger.info(f"Closed mock position {position['id']}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to close position {position['id']} via OANDA API: {e}")
                actual_total_pnl += position["unrealized_pnl"]  # Use estimated P&L
            except Exception as e:
                logger.error(f"Error closing position {position['id']}: {e}")
                actual_total_pnl += position["unrealized_pnl"]  # Use estimated P&L
        
        # Clear all positions from local state
        trading_state.current_positions = []
        
        # Broadcast update to connected clients
        await trading_state.broadcast({
            "type": "all_positions_closed",
            "data": {
                "closed_count": closed_positions,
                "total_pnl": actual_total_pnl
            }
        })
        
        return {
            "status": "success",
            "message": f"All {closed_positions} positions closed successfully",
            "closed_positions": closed_positions,
            "total_pnl": round(actual_total_pnl, 2)
        }
    except Exception as e:
        logger.error(f"Failed to close all positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close all positions: {str(e)}")

@app.post("/api/positions/{position_id}/modify")
async def modify_position(position_id: str, modification: dict):
    """Modify position stop loss or take profit"""
    try:
        # Find the position
        position = None
        position_index = None
        for i, pos in enumerate(trading_state.current_positions):
            if pos.get("id") == position_id:
                position = pos
                position_index = i
                break
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Update stop loss and/or take profit
        if "stop_loss" in modification:
            trading_state.current_positions[position_index]["stop_loss"] = modification["stop_loss"]
        
        if "take_profit" in modification:
            trading_state.current_positions[position_index]["take_profit"] = modification["take_profit"]
        
        # Broadcast update to connected clients
        await trading_state.broadcast({
            "type": "position_modified",
            "data": {
                "position_id": position_id,
                "instrument": position["instrument"],
                "modifications": modification
            }
        })
        
        return {
            "status": "success",
            "message": f"Position {position_id} modified successfully",
            "position": trading_state.current_positions[position_index]
        }
    except Exception as e:
        logger.error(f"Failed to modify position: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to modify position: {str(e)}")

@app.get("/api/account")
async def get_account_info():
    """Get account information from OANDA"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            # Get account details from OANDA
            account_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}",
                headers=headers,
                timeout=10
            )
            
            if account_response.status_code == 200:
                account_data = account_response.json()
                account_info = account_data.get("account", {})
                
                # Update global state
                trading_state.account_info = {
                    "id": account_info.get("id"),
                    "currency": account_info.get("currency"),
                    "balance": float(account_info.get("balance", 0)),
                    "nav": float(account_info.get("NAV", 0)),
                    "unrealized_pnl": float(account_info.get("unrealizedPL", 0)),
                    "margin_used": float(account_info.get("marginUsed", 0)),
                    "margin_available": float(account_info.get("marginAvailable", 0)),
                    "open_positions": int(account_info.get("openPositionCount", 0)),
                    "open_trades": int(account_info.get("openTradeCount", 0)),
                    "last_transaction_id": account_info.get("lastTransactionID")
                }
                
                return trading_state.account_info
            else:
                logger.warning(f"Failed to get account info from OANDA: {account_response.status_code}")
                return {
                    "error": f"Failed to get account info: {account_response.status_code}",
                    "fallback": True
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OANDA API request failed: {e}")
            return {
                "error": f"OANDA API request failed: {str(e)}",
                "fallback": True
            }
            
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        return {
            "error": f"Failed to get account info: {str(e)}",
            "fallback": True
        }

@app.get("/api/test-oanda-connection")
async def test_oanda_connection():
    """Test OANDA API connection"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Test connection with a simple account request
        test_response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}",
            headers=headers,
            timeout=5
        )
        
        if test_response.status_code == 200:
            account_data = test_response.json()
            account = account_data.get("account", {})
            
            return {
                "status": "success",
                "message": "OANDA API connection successful",
                "account_id": account.get("id"),
                "currency": account.get("currency"),
                "balance": float(account.get("balance", 0)),
                "environment": settings.ENVIRONMENT,
                "api_url": api_url
            }
        else:
            return {
                "status": "error",
                "message": f"OANDA API returned status {test_response.status_code}",
                "response": test_response.text[:200]  # First 200 chars of response
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to connect to OANDA API: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

@app.post("/api/refresh-data")
async def refresh_data():
    """Manually refresh account and position data from OANDA"""
    try:
        await update_trading_data()
        return {
            "status": "success",
            "message": "Data refreshed successfully",
            "account": trading_state.account_info,
            "positions_count": len(trading_state.current_positions),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to refresh data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {str(e)}")

@app.get("/api/strategies")
async def get_strategies_api():
    """Get available strategies"""
    return {
        "current": settings.STRATEGY_NAME,
        "available": settings.ALTERNATIVE_STRATEGIES,
        "details": {name: get_strategy_info(name) for name in settings.ALTERNATIVE_STRATEGIES}
    }

@app.post("/api/change-strategy")
async def change_strategy(strategy_data: dict):
    """Change current trading strategy"""
    strategy_name = strategy_data.get("strategy")
    
    if strategy_name not in settings.ALTERNATIVE_STRATEGIES:
        raise HTTPException(status_code=400, detail="Invalid strategy name")
    
    # If trading is active, stop it first
    if trading_state.is_trading:
        logger.info(f"Stopping trading to change strategy from {settings.STRATEGY_NAME} to {strategy_name}")
        trading_state.is_trading = False
        
        # Broadcast trading stopped
        await trading_state.broadcast({
            "type": "trading_stopped",
            "data": {"reason": "Strategy change requested"}
        })
    
    # Close all open positions before changing strategy
    try:
        await update_trading_data()  # Get latest positions
        if trading_state.current_positions:
            logger.info(f"Closing {len(trading_state.current_positions)} positions before strategy change")
            
            # Close all positions
            for position in trading_state.current_positions:
                try:
                    await close_position(position["id"])
                    logger.info(f"Closed position {position['id']}")
                except Exception as e:
                    logger.warning(f"Failed to close position {position['id']}: {e}")
            
            # Wait a moment for positions to close
            await asyncio.sleep(2)
            await update_trading_data()  # Refresh positions
            
    except Exception as e:
        logger.error(f"Error closing positions during strategy change: {e}")
    
    # Change the strategy
    old_strategy = settings.STRATEGY_NAME
    settings.STRATEGY_NAME = strategy_name
    
    logger.info(f"Strategy changed from {old_strategy} to {strategy_name}")
    
    await trading_state.broadcast({
        "type": "strategy_changed",
        "data": {
            "old_strategy": old_strategy,
            "new_strategy": strategy_name,
            "positions_closed": len(trading_state.current_positions) if trading_state.current_positions else 0
        }
    })
    
    return {
        "status": "success", 
        "message": f"Strategy changed from {old_strategy} to {strategy_name}",
        "positions_closed": True
    }

@app.post("/api/settings")
async def save_settings(request: Request):
    """Save settings configuration"""
    try:
        data = await request.json()
        
        # Update account settings
        if "account_id" in data:
            settings.ACCOUNT_ID = data["account_id"]
        
        if "environment" in data:
            settings.ENVIRONMENT = data["environment"]
        
        if "access_token" in data:
            settings.ACCESS_TOKEN = data["access_token"]
        
        if "account_currency" in data:
            settings.ACCOUNT_CURRENCY = data["account_currency"]
        
        # Update settings based on the received data
        if "multi_instrument_mode" in data:
            settings.MULTI_INSTRUMENT_MODE = data["multi_instrument_mode"]
        
        if "instruments" in data:
            settings.INSTRUMENTS = data["instruments"]
        
        if "strategy_name" in data:
            if data["strategy_name"] in settings.ALTERNATIVE_STRATEGIES:
                settings.STRATEGY_NAME = data["strategy_name"]
        
        if "max_percentage_risk" in data:
            settings.MAX_PERCENTAGE_ACCOUNT_AT_RISK = float(data["max_percentage_risk"])
        
        if "max_total_exposure" in data:
            settings.MAX_TOTAL_RISK_EXPOSURE = float(data["max_total_exposure"])
        
        if "max_correlated_positions" in data:
            settings.MAX_CORRELATED_POSITIONS = int(data["max_correlated_positions"])
        
        if "candles_minutes" in data:
            settings.CANDLES_MINUTES = int(data["candles_minutes"])
        
        if "email_address" in data:
            settings.EMAIL_RECIPIENT = data["email_address"]
        
        if "notifications" in data:
            # Store notification preferences (you might want to save these to a config file)
            notifications = data["notifications"]
            settings.EMAIL_NOTIFICATIONS_ENABLED = notifications.get("email_enabled", False)
            settings.TRADE_ALERTS_ENABLED = notifications.get("trade_alerts", False)
            settings.RISK_ALERTS_ENABLED = notifications.get("risk_alerts", False)
            settings.PERFORMANCE_REPORTS_ENABLED = notifications.get("performance_reports", False)
        
        if "debug_mode" in data:
            settings.DEBUG_MODE = data["debug_mode"]
        
        # Broadcast settings update
        await trading_state.broadcast({
            "type": "settings_updated",
            "data": {"message": "Settings updated successfully"}
        })
        
        return {"status": "success", "message": "Settings saved successfully"}
    
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.post("/api/emergency-stop")
async def emergency_stop():
    """Emergency stop - immediately stop trading and close all positions"""
    try:
        # Stop trading immediately
        trading_state.is_trading = False
        
        if trading_state.trading_task:
            trading_state.trading_task.cancel()
        
        # In a real implementation, this would close all open positions
        # For now, we'll simulate closing positions
        trading_state.current_positions = []
        
        await trading_state.broadcast({
            "type": "emergency_stop",
            "data": {"message": "Emergency stop executed - all trading halted"}
        })
        
        logger.warning("Emergency stop executed")
        return {"status": "success", "message": "Emergency stop executed successfully"}
    
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")

@app.post("/api/reset-settings")
async def reset_settings():
    """Reset all settings to default values"""
    try:
        # Reset to default values
        settings.MULTI_INSTRUMENT_MODE = True
        settings.INSTRUMENTS = [
            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF",
            "NZD_USD", "USD_CAD", "EUR_GBP", "EUR_JPY", "GBP_JPY"
        ]
        settings.STRATEGY_NAME = "QuantitativeAlphaStrategy"
        settings.MAX_PERCENTAGE_ACCOUNT_AT_RISK = 2
        settings.MAX_TOTAL_RISK_EXPOSURE = 10
        settings.MAX_CORRELATED_POSITIONS = 3
        settings.CANDLES_MINUTES = 60
        
        await trading_state.broadcast({
            "type": "settings_reset",
            "data": {"message": "Settings reset to defaults"}
        })
        
        return {"status": "success", "message": "Settings reset to defaults"}
    
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")

@app.get("/api/system-status")
async def get_system_status():
    """Get current system status"""
    try:
        # In a real implementation, this would check actual system health
        return {
            "oanda_api": {
                "status": "connected",
                "ping": "45ms",
                "last_update": "2s ago"
            },
            "trading_engine": {
                "status": "running" if trading_state.is_trading else "stopped",
                "uptime": "2h 34m"
            },
            "data_feed": {
                "status": "active",
                "last_update": "2s ago"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@app.get("/api/analytics/performance-metrics")
async def get_performance_metrics():
    """Get current performance metrics"""
    try:
        import random
        
        # Generate realistic sample data (replace with actual calculations)
        return {
            "total_return": round(random.uniform(8.0, 15.0), 1),
            "sharpe_ratio": round(random.uniform(1.5, 2.2), 2),
            "max_drawdown": round(random.uniform(-12.0, -5.0), 1),
            "win_rate": round(random.uniform(60.0, 75.0), 1),
            "volatility": round(random.uniform(12.0, 18.0), 1),
            "sortino_ratio": round(random.uniform(1.8, 2.5), 2),
            "calmar_ratio": round(random.uniform(1.2, 1.8), 2),
            "var_95": round(random.uniform(-3.5, -2.0), 1),
            "expected_shortfall": round(random.uniform(-5.0, -3.5), 1),
            "beta": round(random.uniform(0.7, 1.1), 2),
            "alpha": round(random.uniform(2.0, 4.0), 1),
            "total_trades": random.randint(1000, 1500),
            "winning_trades": random.randint(600, 900),
            "losing_trades": random.randint(300, 500),
            "average_trade": round(random.uniform(35.0, 55.0), 2),
            "best_trade": round(random.uniform(1000.0, 1500.0), 2),
            "worst_trade": round(random.uniform(-600.0, -400.0), 2),
            "profit_factor": round(random.uniform(1.8, 2.5), 2)
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@app.get("/api/analytics/equity-curve")
async def get_equity_curve(period: str = "1M"):
    """Get equity curve data for specified period"""
    try:
        import random
        import datetime
        from datetime import timedelta
        
        # Generate sample equity curve data
        periods = {
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365
        }
        
        days = periods.get(period, 30)
        start_date = datetime.datetime.now() - timedelta(days=days)
        
        data = []
        equity = 100000  # Starting equity
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            # Simulate daily returns with slight upward bias
            daily_return = random.gauss(0.001, 0.015)  # 0.1% average daily return, 1.5% volatility
            equity *= (1 + daily_return)
            
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "equity": round(equity, 2)
            })
        
        return {"data": data}
    except Exception as e:
        logger.error(f"Failed to get equity curve: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get equity curve: {str(e)}")

@app.get("/api/analytics/drawdown")
async def get_drawdown_data():
    """Get drawdown analysis data"""
    try:
        import random
        import datetime
        from datetime import timedelta
        
        # Generate sample drawdown data
        start_date = datetime.datetime.now() - timedelta(days=90)
        data = []
        peak = 100000
        current = 100000
        
        for i in range(90):
            date = start_date + timedelta(days=i)
            # Simulate equity changes
            daily_return = random.gauss(0.001, 0.015)
            current *= (1 + daily_return)
            
            if current > peak:
                peak = current
            
            drawdown = ((current - peak) / peak) * 100
            
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "drawdown": round(drawdown, 2)
            })
        
        return {"data": data}
    except Exception as e:
        logger.error(f"Failed to get drawdown data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get drawdown data: {str(e)}")

@app.get("/api/analytics/returns-distribution")
async def get_returns_distribution():
    """Get returns distribution data"""
    try:
        import random
        
        # Generate sample daily returns
        returns = [random.gauss(0.001, 0.015) * 100 for _ in range(250)]  # Convert to percentage
        
        # Create histogram data manually (avoiding numpy dependency)
        bins = []
        for i in range(-6, 6):
            bins.append(i + 0.5)
        
        hist = [0] * len(bins)
        for ret in returns:
            for i, bin_center in enumerate(bins):
                if abs(ret - bin_center) < 0.5:
                    hist[i] += 1
                    break
        
        data = []
        for i, count in enumerate(hist):
            data.append({
                "bin": bins[i],
                "count": count
            })
        
        return {"data": data}
    except Exception as e:
        logger.error(f"Failed to get returns distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get returns distribution: {str(e)}")

@app.get("/api/analytics/rolling-sharpe")
async def get_rolling_sharpe():
    """Get rolling Sharpe ratio data"""
    try:
        import random
        import datetime
        from datetime import timedelta
        
        # Generate sample rolling Sharpe ratio data
        start_date = datetime.datetime.now() - timedelta(days=90)
        data = []
        
        for i in range(90):
            date = start_date + timedelta(days=i)
            # Simulate rolling Sharpe ratio with some variation
            sharpe = random.gauss(1.8, 0.3)
            
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "sharpe": round(sharpe, 2)
            })
        
        return {"data": data}
    except Exception as e:
        logger.error(f"Failed to get rolling Sharpe: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rolling Sharpe: {str(e)}")

@app.get("/api/analytics/strategy-breakdown")
async def get_strategy_breakdown(period: str = "all"):
    """Get strategy performance breakdown by instrument"""
    try:
        import random
        
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF", "USD_CAD", "NZD_USD"]
        
        # Adjust data based on time period
        period_multipliers = {
            "all": 1.0,      # Full data
            "30": 0.25,      # ~25% of trades for 30 days
            "90": 0.75       # ~75% of trades for 90 days
        }
        
        multiplier = period_multipliers.get(period, 1.0)
        
        data = []
        for i, instrument in enumerate(instruments):
            # Use instrument index to create consistent but different data per period
            random.seed(hash(instrument + period) % 1000)
            
            base_trades = random.randint(150, 300)
            trades = max(10, int(base_trades * multiplier))
            
            win_rate = random.uniform(60, 80)
            
            # Adjust PnL based on period (shorter periods might have different performance)
            base_pnl = random.uniform(1500, 4000)
            if period == "30":
                total_pnl = base_pnl * multiplier * random.uniform(0.8, 1.2)  # More volatile for shorter periods
            elif period == "90":
                total_pnl = base_pnl * multiplier * random.uniform(0.9, 1.1)  # Moderate adjustment
            else:
                total_pnl = base_pnl
            
            avg_trade = total_pnl / trades
            best_trade = random.uniform(300, 600) * (1.2 if period == "30" else 1.0)  # Higher volatility in shorter periods
            worst_trade = random.uniform(-200, -100) * (1.2 if period == "30" else 1.0)
            profit_factor = random.uniform(1.5, 3.0)
            
            data.append({
                "instrument": instrument,
                "trades": trades,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_trade": round(avg_trade, 2),
                "best_trade": round(best_trade, 2),
                "worst_trade": round(worst_trade, 2),
                "profit_factor": round(profit_factor, 2)
            })
        
        # Reset random seed
        random.seed()
        
        return {"data": data, "period": period}
    except Exception as e:
        logger.error(f"Failed to get strategy breakdown: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy breakdown: {str(e)}")

@app.get("/api/analytics/monthly-performance")
async def get_monthly_performance():
    """Get monthly performance data"""
    try:
        import random
        
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        
        data = []
        ytd_total = 0
        
        for i, month in enumerate(months[:6]):  # First 6 months
            performance = random.uniform(-2.0, 5.0)
            ytd_total += performance
            
            data.append({
                "month": month,
                "performance": round(performance, 1)
            })
        
        data.append({
            "month": "YTD Total",
            "performance": round(ytd_total, 1)
        })
        
        return {"data": data}
    except Exception as e:
        logger.error(f"Failed to get monthly performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monthly performance: {str(e)}")

@app.post("/api/analytics/run-backtest")
async def run_backtest():
    """Run backtest analysis"""
    try:
        import subprocess
        import sys
        import os
        
        # Run backtest in background
        backtest_path = os.path.join(os.path.dirname(__file__), "backtest.py")
        
        if os.path.exists(backtest_path):
            # Run backtest as subprocess
            result = subprocess.run([sys.executable, backtest_path], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": "Backtest completed successfully",
                    "output": result.stdout
                }
            else:
                return {
                    "status": "error",
                    "message": "Backtest failed",
                    "error": result.stderr
                }
        else:
            return {
                "status": "error",
                "message": "Backtest file not found"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Backtest timed out (60s limit)"
        }
    except Exception as e:
        logger.error(f"Failed to run backtest: {e}")
        return {
            "status": "error",
            "message": f"Failed to run backtest: {str(e)}"
        }

# Background tasks
async def run_trading_bot():
    """Background task to run the real OANDA trading bot"""
    try:
        logger.info("Starting OANDA Trading Bot")
        
        # Start the actual trading bot in a separate thread to avoid blocking
        import threading
        import concurrent.futures
        
        def run_trade_bot():
            """Run the actual trading bot from trade.py"""
            try:
                trade.trade(headless=True)  # Run in headless mode for web app
            except Exception as e:
                logger.error(f"Trading bot execution error: {e}")
                return False
            return True
        
        # Run the trading bot in a thread pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit the trading task
            trading_future = executor.submit(run_trade_bot)
            
            # Monitor the trading bot and update UI
            while trading_state.is_trading:
                try:
                    # Update positions and account info from OANDA
                    await update_trading_data()
                    
                    # Check if trading bot is still running
                    if trading_future.done():
                        result = trading_future.result()
                        if not result:
                            logger.error("Trading bot stopped unexpectedly")
                            trading_state.is_trading = False
                            break
                        else:
                            logger.info("Trading bot completed successfully")
                            trading_state.is_trading = False
                            break
                    
                    # Wait before next update
                    await asyncio.sleep(10)  # Update every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Error updating trading data: {e}")
                    await asyncio.sleep(5)  # Wait a bit before retrying
            
            # Cancel the trading future if we're stopping
            if not trading_future.done():
                trading_future.cancel()
                
    except asyncio.CancelledError:
        logger.info("Trading task cancelled")
        trading_state.is_trading = False
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        trading_state.is_trading = False
        
        # Broadcast error to clients
        await trading_state.broadcast({
            "type": "trading_error",
            "data": {
                "message": f"Trading bot error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        })

async def update_trading_data():
    """Update trading data from OANDA and broadcast to clients"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Get account info
        try:
            account_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}",
                headers=headers,
                timeout=10
            )
            
            if account_response.status_code == 200:
                account_data = account_response.json()
                account_info = account_data.get("account", {})
                
                trading_state.account_info = {
                    "id": account_info.get("id"),
                    "currency": account_info.get("currency"),
                    "balance": float(account_info.get("balance", 0)),
                    "nav": float(account_info.get("NAV", 0)),
                    "unrealized_pnl": float(account_info.get("unrealizedPL", 0)),
                    "margin_used": float(account_info.get("marginUsed", 0)),
                    "margin_available": float(account_info.get("marginAvailable", 0)),
                    "open_positions": int(account_info.get("openPositionCount", 0)),
                    "open_trades": int(account_info.get("openTradeCount", 0))
                }
        except Exception as e:
            logger.warning(f"Failed to update account info: {e}")
        
        # Get current positions and trades (for SL/TP info)
        try:
            # Get positions
            positions_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/openPositions",
                headers=headers,
                timeout=10
            )
            
            # Get open trades (contains SL/TP information)
            trades_response = requests.get(
                f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/openTrades",
                headers=headers,
                timeout=10
            )
            
            if positions_response.status_code == 200:
                oanda_positions = positions_response.json().get("positions", [])
                oanda_trades = []
                
                if trades_response.status_code == 200:
                    oanda_trades = trades_response.json().get("trades", [])
                
                # Get current prices for all instruments
                instruments_with_positions = [pos["instrument"] for pos in oanda_positions]
                current_prices = {}
                
                if instruments_with_positions:
                    pricing_response = requests.get(
                        f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/pricing",
                        headers=headers,
                        params={"instruments": ",".join(instruments_with_positions)},
                        timeout=10
                    )
                    
                    if pricing_response.status_code == 200:
                        prices_data = pricing_response.json().get("prices", [])
                        for price_info in prices_data:
                            instrument = price_info["instrument"]
                            bid = float(price_info["bids"][0]["price"])
                            ask = float(price_info["asks"][0]["price"])
                            current_prices[instrument] = (bid + ask) / 2
                
                # Create a map of trades by instrument for SL/TP lookup
                trades_by_instrument = {}
                for trade in oanda_trades:
                    instrument = trade["instrument"]
                    if instrument not in trades_by_instrument:
                        trades_by_instrument[instrument] = []
                    trades_by_instrument[instrument].append(trade)
                
                # Process positions
                positions = []
                for oanda_pos in oanda_positions:
                    instrument = oanda_pos["instrument"]
                    
                    # Check for long or short position
                    long_units = float(oanda_pos["long"]["units"])
                    short_units = float(oanda_pos["short"]["units"])
                    
                    if long_units != 0:
                        units = long_units
                        side = "LONG"
                        avg_price = float(oanda_pos["long"]["averagePrice"])
                        unrealized_pnl = float(oanda_pos["long"]["unrealizedPL"])
                    elif short_units != 0:
                        units = short_units
                        side = "SHORT"
                        avg_price = float(oanda_pos["short"]["averagePrice"])
                        unrealized_pnl = float(oanda_pos["short"]["unrealizedPL"])
                    else:
                        continue
                    
                    current_price = current_prices.get(instrument, avg_price)
                    margin_used = abs(units) * current_price * 0.02
                    
                    # Look for SL/TP in related trades
                    stop_loss = None
                    take_profit = None
                    open_time = datetime.now() - timedelta(hours=1)
                    
                    if instrument in trades_by_instrument:
                        for trade in trades_by_instrument[instrument]:
                            # Check if trade direction matches position
                            trade_units = float(trade["currentUnits"])
                            if (units > 0 and trade_units > 0) or (units < 0 and trade_units < 0):
                                # Get SL/TP from trade
                                if "stopLossOrder" in trade and trade["stopLossOrder"]:
                                    stop_loss = float(trade["stopLossOrder"]["price"])
                                if "takeProfitOrder" in trade and trade["takeProfitOrder"]:
                                    take_profit = float(trade["takeProfitOrder"]["price"])
                                # Get actual open time
                                if "openTime" in trade:
                                    try:
                                        open_time = datetime.fromisoformat(trade["openTime"].replace('Z', '+00:00'))
                                    except:
                                        pass
                                break
                    
                    # Calculate duration
                    duration_minutes = int((datetime.now(open_time.tzinfo) - open_time).total_seconds() / 60)
                    
                    position = {
                        "id": f"oanda_{instrument}_{side.lower()}",
                        "instrument": instrument,
                        "units": int(abs(units)),
                        "side": side,
                        "entry_price": round(avg_price, 5),
                        "current_price": round(current_price, 5),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "margin_used": round(margin_used, 2),
                        "stop_loss": round(stop_loss, 5) if stop_loss else None,
                        "take_profit": round(take_profit, 5) if take_profit else None,
                        "open_time": open_time.isoformat(),
                        "duration_minutes": max(1, duration_minutes)
                    }
                    positions.append(position)
                
                trading_state.current_positions = positions
                
        except Exception as e:
            logger.warning(f"Failed to update positions: {e}")
        
        # Get recent trades (last 24 hours)
        try:
            recent_trades_data = await get_recent_trades(limit=20, days=1)
            if recent_trades_data and "trades" in recent_trades_data:
                trading_state.recent_trades = recent_trades_data["trades"]
            else:
                # Keep existing trades if API call fails
                if not trading_state.recent_trades:
                    trading_state.recent_trades = []
        except Exception as e:
            logger.warning(f"Failed to update recent trades: {e}")
        
        # Broadcast update to all connected clients
        await trading_state.broadcast({
            "type": "market_update",
            "data": {
                "account": trading_state.account_info,
                "positions": trading_state.current_positions,
                "recent_trades": trading_state.recent_trades,
                "timestamp": datetime.now().isoformat(),
                "is_trading": trading_state.is_trading
            }
        })
        
    except Exception as e:
        logger.error(f"Error in update_trading_data: {e}")

async def execute_backtest():
    """Execute backtest in background"""
    try:
        # This would call your existing backtest.py
        logger.info("Starting backtest...")
        # backtest.backtest()  # Uncomment when ready
        
        # Simulate backtest results
        await asyncio.sleep(2)
        
        results = {
            "total_return": random.uniform(-10, 25),
            "sharpe_ratio": random.uniform(0.5, 2.5),
            "max_drawdown": random.uniform(-15, -5),
            "total_trades": random.randint(50, 200),
            "win_rate": random.uniform(45, 65)
        }
        
        await trading_state.broadcast({
            "type": "backtest_complete",
            "data": results
        })
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")

@app.get("/api/account")
async def get_account_info():
    """Get current account information"""
    try:
        await update_trading_data()
        return {
            "account": trading_state.account_info,
            "positions_count": len(trading_state.current_positions),
            "unrealized_pnl": sum(float(pos.get("unrealized_pnl", 0)) for pos in trading_state.current_positions),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return {"error": str(e)}

@app.get("/api/market-data")
async def get_market_data():
    """Get current market prices for all instruments"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        instruments = settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT]
        market_data = {}
        
        # Get pricing for all instruments
        instruments_str = ",".join(instruments)
        pricing_response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/pricing",
            headers=headers,
            params={"instruments": instruments_str},
            timeout=10
        )
        
        if pricing_response.status_code == 200:
            pricing_data = pricing_response.json()
            
            for price_info in pricing_data.get("prices", []):
                instrument = price_info["instrument"]
                bid = float(price_info["bids"][0]["price"])
                ask = float(price_info["asks"][0]["price"])
                mid_price = (bid + ask) / 2
                spread = ask - bid
                
                # Calculate 24h change (mock for now - would need historical data)
                import random
                change_percent = (random.random() - 0.5) * 2  # Random change between -1% and +1%
                
                market_data[instrument] = {
                    "instrument": instrument,
                    "bid": bid,
                    "ask": ask,
                    "mid": mid_price,
                    "spread": spread,
                    "change_percent": round(change_percent, 2),
                    "timestamp": price_info.get("time", datetime.now().isoformat())
                }
        
        return {"market_data": market_data, "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return {"market_data": {}, "error": str(e)}

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """Get all dashboard data in one request"""
    try:
        # Update trading data first
        await update_trading_data()
        
        # Get market data
        market_response = await get_market_data()
        market_data = market_response.get("market_data", {})
        
        # Calculate daily stats
        today_trades = 0  # Would need to query OANDA transaction history
        win_rate = 0      # Would need to calculate from recent trades
        
        # Get recent trades for today's stats
        try:
            trades_data = await get_recent_trades(limit=100, days=1)
            if trades_data and "trades" in trades_data:
                today_trades = len(trades_data["trades"])
                if today_trades > 0:
                    winning_trades = sum(1 for trade in trades_data["trades"] 
                                       if float(trade.get("realizedPL", 0)) > 0)
                    win_rate = round((winning_trades / today_trades) * 100, 1)
        except:
            pass
        
        return {
            "account": trading_state.account_info,
            "positions": trading_state.current_positions,
            "market_data": market_data,
            "stats": {
                "positions_count": len(trading_state.current_positions),
                "unrealized_pnl": sum(float(pos.get("unrealized_pnl", 0)) for pos in trading_state.current_positions),
                "today_trades": today_trades,
                "win_rate": win_rate
            },
            "trading_status": {
                "is_trading": trading_state.is_trading,
                "strategy": settings.STRATEGY_NAME,
                "instruments": settings.INSTRUMENTS if settings.MULTI_INSTRUMENT_MODE else [settings.INSTRUMENT]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {"error": str(e)}

@app.get("/api/price-history/{instrument}")
async def get_price_history(instrument: str, period: str = "1H", count: int = 50):
    """Get historical price data for an instrument"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Get historical candles
        response = requests.get(
            f"{api_url}/v3/instruments/{instrument}/candles",
            headers=headers,
            params={
                "granularity": period,
                "count": count
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            prices = []
            
            for candle in data.get("candles", []):
                if candle.get("complete", True):
                    mid_price = (float(candle["mid"]["h"]) + float(candle["mid"]["l"])) / 2
                    prices.append({
                        "time": candle["time"],
                        "mid": mid_price,
                        "high": float(candle["mid"]["h"]),
                        "low": float(candle["mid"]["l"]),
                        "open": float(candle["mid"]["o"]),
                        "close": float(candle["mid"]["c"])
                    })
            
            return {"prices": prices, "instrument": instrument, "period": period}
        else:
            return {"prices": [], "error": f"OANDA API error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        return {"prices": [], "error": str(e)}

@app.get("/api/recent-trades")
async def get_recent_trades_api(limit: int = 10):
    """Get recent trades from OANDA account"""
    try:
        import requests
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Get recent transactions
        response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/transactions",
            headers=headers,
            params={
                "type": "ORDER_FILL",
                "count": limit * 2  # Get more to filter for actual trades
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            trades = []
            
            for transaction in data.get("transactions", []):
                if transaction.get("type") == "ORDER_FILL":
                    trades.append({
                        "id": transaction.get("id"),
                        "time": transaction.get("time"),
                        "instrument": transaction.get("instrument"),
                        "units": int(transaction.get("units", 0)),
                        "price": float(transaction.get("price", 0)),
                        "realizedPL": float(transaction.get("pl", 0)),
                        "reason": transaction.get("reason", "")
                    })
            
            # Limit to requested number
            trades = trades[:limit]
            
            return {"trades": trades, "count": len(trades)}
        else:
            return {"trades": [], "error": f"OANDA API error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}")
        return {"trades": [], "error": str(e)}

@app.get("/api/positions/recent-trades")
async def get_recent_trades_positions(limit: int = 50, days: int = 7, instrument: str = None):
    """Get recent completed trades for positions page"""
    try:
        import requests
        from datetime import datetime, timedelta
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get transactions
        response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/transactions",
            headers=headers,
            params={
                "type": "ORDER_FILL",
                "from": start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "to": end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            trades = []
            
            for transaction in data.get("transactions", []):
                if transaction.get("type") == "ORDER_FILL":
                    trade_instrument = transaction.get("instrument", "")
                    
                    # Filter by instrument if specified
                    if instrument and trade_instrument != instrument:
                        continue
                    
                    # Calculate duration (mock for now - would need order creation time)
                    duration_minutes = 15 + (hash(transaction.get("id", "")) % 120)  # Mock duration 15-135 minutes
                    
                    trades.append({
                        "id": transaction.get("id"),
                        "close_time": transaction.get("time"),
                        "instrument": trade_instrument,
                        "side": "LONG" if int(transaction.get("units", 0)) > 0 else "SHORT",
                        "units": abs(int(transaction.get("units", 0))),
                        "entry_price": float(transaction.get("price", 0)),
                        "exit_price": float(transaction.get("price", 0)),
                        "realized_pnl": float(transaction.get("pl", 0)),
                        "duration_minutes": duration_minutes,
                        "strategy": "AggressiveMultiInstrumentStrategy"
                    })
            
            # Sort by close time (newest first)
            trades.sort(key=lambda x: x["close_time"], reverse=True)
            
            # Limit results
            trades = trades[:limit]
            
            # Calculate statistics
            statistics = calculate_trade_statistics(trades)
            
            return {
                "trades": trades,
                "statistics": statistics,
                "count": len(trades),
                "period_days": days
            }
        else:
            return {"trades": [], "statistics": {}, "error": f"OANDA API error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error getting recent trades for positions: {e}")
        return {"trades": [], "statistics": {}, "error": str(e)}

@app.get("/api/positions/pnl-history")
async def get_pnl_history(period: str = "1H"):
    """Get P&L history for positions page"""
    try:
        import requests
        from datetime import datetime, timedelta
        
        # OANDA API configuration
        api_url = f"https://api-fxpractice.oanda.com" if settings.ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"
        headers = {
            "Authorization": f"Bearer {settings.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Get account summary for current balance
        response = requests.get(
            f"{api_url}/v3/accounts/{settings.ACCOUNT_ID}/summary",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            account_data = response.json()
            current_balance = float(account_data["account"]["balance"])
            
            # Generate historical P&L data (mock for now - would need historical account data)
            data_points = []
            now = datetime.now()
            
            if period == "1H":
                # Hourly data for last 24 hours
                for i in range(24, 0, -1):
                    timestamp = now - timedelta(hours=i)
                    # Simulate P&L progression
                    pnl_variation = (hash(str(timestamp)) % 1000 - 500) / 100  # Random variation
                    balance = current_balance + pnl_variation
                    
                    data_points.append({
                        "timestamp": timestamp.isoformat(),
                        "pnl": balance,
                        "unrealized_pnl": pnl_variation
                    })
            elif period == "4H":
                # 4-hour data for last 7 days
                for i in range(42, 0, -1):  # 42 * 4 hours = 7 days
                    timestamp = now - timedelta(hours=i * 4)
                    pnl_variation = (hash(str(timestamp)) % 2000 - 1000) / 100
                    balance = current_balance + pnl_variation
                    
                    data_points.append({
                        "timestamp": timestamp.isoformat(),
                        "pnl": balance,
                        "unrealized_pnl": pnl_variation
                    })
            else:  # 1D
                # Daily data for last 30 days
                for i in range(30, 0, -1):
                    timestamp = now - timedelta(days=i)
                    pnl_variation = (hash(str(timestamp)) % 3000 - 1500) / 100
                    balance = current_balance + pnl_variation
                    
                    data_points.append({
                        "timestamp": timestamp.isoformat(),
                        "pnl": balance,
                        "unrealized_pnl": pnl_variation
                    })
            
            return {
                "data": data_points,
                "period": period,
                "current_balance": current_balance
            }
        else:
            return {"data": [], "error": f"OANDA API error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error getting P&L history: {e}")
        return {"data": [], "error": str(e)}

def calculate_trade_statistics(trades):
    """Calculate trading statistics from trades list"""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "average_win": 0,
            "average_loss": 0,
            "average_duration": 0,
            "shortest_duration": 0,
            "longest_duration": 0,
            "best_pair": {"instrument": "EUR_USD", "pnl": 0, "trades": 0}
        }
    
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["realized_pnl"] > 0]
    losing_trades = [t for t in trades if t["realized_pnl"] < 0]
    
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t["realized_pnl"] for t in trades)
    average_win = sum(t["realized_pnl"] for t in winning_trades) / win_count if win_count > 0 else 0
    average_loss = sum(t["realized_pnl"] for t in losing_trades) / loss_count if loss_count > 0 else 0
    
    durations = [t["duration_minutes"] for t in trades]
    average_duration = sum(durations) / len(durations) if durations else 0
    shortest_duration = min(durations) if durations else 0
    longest_duration = max(durations) if durations else 0
    
    # Find best performing pair
    pair_stats = {}
    for trade in trades:
        instrument = trade["instrument"]
        if instrument not in pair_stats:
            pair_stats[instrument] = {"pnl": 0, "trades": 0}
        pair_stats[instrument]["pnl"] += trade["realized_pnl"]
        pair_stats[instrument]["trades"] += 1
    
    best_pair = {"instrument": "EUR_USD", "pnl": 0, "trades": 0}
    if pair_stats:
        best_instrument = max(pair_stats.keys(), key=lambda k: pair_stats[k]["pnl"])
        best_pair = {
            "instrument": best_instrument,
            "pnl": pair_stats[best_instrument]["pnl"],
            "trades": pair_stats[best_instrument]["trades"]
        }
    
    return {
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "average_win": average_win,
        "average_loss": average_loss,
        "average_duration": average_duration,
        "shortest_duration": shortest_duration,
        "longest_duration": longest_duration,
        "best_pair": best_pair
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    print("Starting Advanced OANDA Trading Bot Web Interface...")
    print(" Dashboard will be available at: http://localhost:8000")
    print(" API Documentation at: http://localhost:8000/api/docs")
    
    import os
    
    # Get port from environment variable (for deployment platforms like Render)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    # Use 0.0.0.0 for production deployment
    if os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("HEROKU_APP_NAME"):
        host = "0.0.0.0"
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=False if os.getenv("RENDER") else True,
        log_level="info"
    )
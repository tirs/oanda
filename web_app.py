"""
🚀 OANDA Trading Bot - Web Interface Only
Simplified version for initial deployment without trading dependencies
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import logging
from datetime import datetime
from typing import Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="OANDA Trading Bot - Web Interface",
    description="Trading interface (trading modules loading...)",
    version="2.0.0"
)

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "OANDA Trading Bot",
        "status": "Web interface active - Trading modules loading..."
    })

@app.get("/api/status")
async def get_status():
    """API status endpoint"""
    return {
        "status": "web_only",
        "message": "Web interface is running. Trading modules are being loaded.",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "practice")
    }

@app.get("/api/strategies")
async def get_strategies():
    """Get available strategies"""
    return {
        "strategies": {
            "loading": {
                "name": "Loading...",
                "description": "Trading strategies are being loaded",
                "status": "initializing"
            }
        }
    }

@app.get("/positions")
async def positions(request: Request):
    """Positions page"""
    return templates.TemplateResponse("positions.html", {
        "request": request,
        "title": "Positions",
        "positions": []
    })

@app.get("/strategies")
async def strategies_page(request: Request):
    """Strategies page"""
    return templates.TemplateResponse("strategies.html", {
        "request": request,
        "title": "Trading Strategies",
        "strategies": {}
    })

@app.get("/settings")
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Settings"
    })

@app.get("/analytics")
async def analytics_page(request: Request):
    """Analytics page"""
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "title": "Analytics"
    })

@app.get("/backtest")
async def backtest_page(request: Request):
    """Backtest page"""
    return templates.TemplateResponse("backtest.html", {
        "request": request,
        "title": "Backtesting"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
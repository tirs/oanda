#!/usr/bin/env python3
"""
🚀 OANDA Trading Bot - Web Application Launcher
Professional FastAPI web interface for advanced trading strategies
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import jinja2
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\n📦 Installing required packages...")
        
        # Install requirements
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements_web.txt"
            ])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            return False

def create_directories():
    """Create necessary directories"""
    directories = ["static", "templates", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")

def main():
    """Main launcher function"""
    print("🚀 OANDA Trading Bot - Web Application Launcher")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("settings.py").exists():
        print("❌ Error: settings.py not found. Please run this script from the bot directory.")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        print("❌ Failed to install requirements. Please install manually:")
        print("   pip install -r requirements_web.txt")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Check if templates exist
    if not Path("templates/base.html").exists():
        print("❌ Error: Template files not found. Please ensure all template files are present.")
        sys.exit(1)
    
    print("\n🌟 Starting OANDA Trading Bot Web Interface...")
    print("📊 Dashboard will be available at: http://localhost:8002")
    print("📚 API Documentation at: http://localhost:8002/api/docs")
    print("🔧 Admin Interface at: http://localhost:8002/settings")
    print("\n⚡ Features Available:")
    print("   • Real-time trading dashboard")
    print("   • Strategy management & backtesting")
    print("   • Live position monitoring")
    print("   • Performance analytics")
    print("   • Risk management controls")
    print("   • WebSocket real-time updates")
    
    # Ask user if they want to open browser
    try:
        open_browser = input("\n🌐 Open browser automatically? (y/n): ").lower().strip()
        if open_browser in ['y', 'yes', '']:
            print("🌐 Browser will open automatically...")
            # Delay browser opening to allow server to start
            import threading
            import time
            
            def open_browser_delayed():
                time.sleep(3)
                webbrowser.open("http://localhost:8002")
            
            threading.Thread(target=open_browser_delayed, daemon=True).start()
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
        sys.exit(0)
    
    print("\n🚀 Launching web server...")
    print("📝 Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        # Import and run the FastAPI app
        import uvicorn
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8002,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Web server stopped by user")
        print("💡 Thank you for using OANDA Trading Bot!")
    except Exception as e:
        print(f"\n❌ Error starting web server: {e}")
        print("💡 Please check the error message above and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()
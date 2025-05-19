import os
import logging
import asyncio
import threading
import atexit
from flask import Flask, render_template, jsonify, request, current_app
from auth.auth_service_client import AuthServiceClient
from flask_socketio import SocketIO
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from dotenv import load_dotenv
from database.db import init_db, db, get_sync_db
from api.routes import api_blueprint
from strategies.breakout_reset import BreakoutResetStrategy
from utils.backtest import Backtester
from utils.realtime_data_handler import RealtimeDataHandler
from utils.exchange_interface import MockExchangeInterface, BinanceExchangeInterface # Assuming CcxtExchangeInterface was a typo for BinanceExchangeInterface or a more generic one
from auth.auth_service import token_required
from datetime import datetime, timedelta
from utils.logging_utils import safe_log_info, safe_log_warning, safe_log_error, signal_logging_shutdown # Ensure signal_logging_shutdown is imported
import pandas as pd
import numpy as np
from flask_cors import CORS

def create_app(test_config=None):
    """Application factory function"""
    # Load environment variables
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, # Set the root logger level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(), # Log to console
            # Add FileHandler if needed: logging.FileHandler('cryptobot.log')
        ]
    )
    logger = logging.getLogger(__name__)

    # Initialize Flask app
    app = Flask(__name__)
    CORS(app,
        supports_credentials=True,
        expose_headers=['Authorization'],
        allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
        origins=['http://localhost:5000', 'http://127.0.0.1:5000', 'http://localhost:3000', 'http://127.0.0.1:3000']
    )

    # Configure JWT cookies for cross-origin requests
    app.config['JWT_COOKIE_SECURE'] = False  # Allow http in development
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disable CSRF for development
    app.config['JWT_SESSION_COOKIE'] = False  # Don't use session cookies

    # Configure app
    if test_config is None:
        # JWT Configuration
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key')
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
        app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
        app.config['JWT_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
        app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disabled for development
        app.config['JWT_CSRF_CHECK_FORM'] = False
        app.config['AUTH_SERVICE_URL'] = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8000')
        
        # Database configuration
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///database/cryptobot.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        os.environ['FLASK_ENV'] = 'development'
    else:
        # Load test config
        app.config.update(test_config)
        # Ensure test database is in-memory if not specified
        if 'SQLALCHEMY_DATABASE_URI' not in test_config:
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Initialize JWT with additional configuration
    jwt = JWTManager(app)
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token_cookie'
    app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
    app.config['JWT_COOKIE_DOMAIN'] = None
    app.config['JWT_SESSION_COOKIE'] = False
    
    # Initialize auth service client
    app.auth_service = AuthServiceClient(app.config['AUTH_SERVICE_URL'])
    
    # Enable TESTING mode if running tests
    app.config['TESTING'] = os.getenv('PYTEST_CURRENT_TEST') is not None
    
    # Add JWT callbacks for debugging
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        if app.config.get('TESTING'):
            safe_log_warning(logger, f"TESTING MODE: Bypassing JWT validation")
            return jsonify({"error": "Invalid token"}), 401
        safe_log_error(logger, f"Invalid token: {error}")
        return jsonify({"error": "Invalid token"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        if app.config.get('TESTING'):
            safe_log_warning(logger, f"TESTING MODE: Bypassing token check")
            return jsonify({"error": "Authorization required"}), 401
        safe_log_error(logger, f"Missing token: {error}")
        return jsonify({"error": "Authorization required"}), 401

    # Initialize SocketIO for real-time updates
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading') # Ensure async_mode is set

    # --- Initialize Exchange Interface --- 
    # Load environment variables for exchange configuration
    load_dotenv()
    use_real_exchange = os.getenv('USE_REAL_EXCHANGE', 'false').lower() == 'true'
    exchange_id = os.getenv('EXCHANGE_ID', 'binance')
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'false').lower() == 'true'

    if use_real_exchange:
        if not api_key or not api_secret:
            safe_log_warning(logger, "API_KEY or API_SECRET not found in environment variables. Falling back to MockExchangeInterface.")
            exchange_interface = MockExchangeInterface(testnet=use_testnet)
        else:
            safe_log_info(logger, f"Using real exchange: {exchange_id} ({'Testnet' if use_testnet else 'Live'})")
            # Assuming CcxtExchangeInterface was a placeholder or specific implementation not fully shown
            # For now, let's assume BinanceExchangeInterface if exchange_id is binance, else Mock
            if exchange_id.lower() == 'binance':
                exchange_interface = BinanceExchangeInterface(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=use_testnet
                )
            else:
                safe_log_warning(logger, f"Exchange ID '{exchange_id}' not explicitly supported for real mode, falling back to Mock.")
                exchange_interface = MockExchangeInterface(testnet=use_testnet)
    else:
        safe_log_info(logger, "Using MockExchangeInterface.")
        exchange_interface = MockExchangeInterface(testnet=use_testnet)

    # Initialize Realtime Data Handler
    realtime_handler = RealtimeDataHandler(socketio)

    # Initialize databases (skip in test environment)
    if not app.config.get('TESTING'):
        try:
            init_db(app)
        except Exception as e:
            safe_log_error(logger, f"Failed to initialize database: {e}", exc_info=True)
            if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
                safe_log_warning(logger, "SQLite database may be locked or path invalid")
            raise
    
    # Add cleanup handler for sync database
    @app.teardown_appcontext
    def shutdown_sync_session(exception=None):
        """Cleanup sync database session at app teardown"""
        if exception:
            db.session.rollback()
        db.session.remove()
    
    # Add cleanup handler for async database
    @app.teardown_appcontext
    def shutdown_async_session(exception=None):
        """Cleanup async database connections at app teardown"""
        # Async cleanup will be handled by get_db() context manager
        pass

    # --- Instantiate and Register Strategies --- 
    # Example: Instantiate BreakoutResetStrategy with default parameters
    # Pass the exchange interface to the strategies
    # Define default strategy parameters (consider moving to config)
    default_strategy_params = {
        'lookback_period': 20,
        'volatility_multiplier': 2.0,
        'reset_threshold': 0.5,
        'position_size_pct': 0.1, # Example: 10% of capital per trade
        'take_profit': 0.05, # Example: 5% take profit
        'stop_loss': 0.02 # Example: 2% stop loss
    }
    try:
        breakout_strategy_btc = BreakoutResetStrategy(
            symbol='BTCUSDT',
            exchange_interface=exchange_interface,
            **default_strategy_params
        )
        breakout_strategy_eth = BreakoutResetStrategy(
            symbol='ETHUSDT',
            exchange_interface=exchange_interface,
            **default_strategy_params
        )
    except ValueError as e:
        safe_log_error(logger, f"Failed to initialize BreakoutResetStrategy: {e}", exc_info=True)
        # Handle error appropriately - maybe exit or use a dummy strategy
        raise SystemExit(f"Strategy initialization failed: {e}")

    # Register strategies with the handler
    realtime_handler.register_strategy(breakout_strategy_btc, 'BTCUSDT')
    realtime_handler.register_strategy(breakout_strategy_eth, 'ETHUSDT')
    # --- End Strategy Instantiation/Registration ---

    # Register API blueprint with debug logging
    if not hasattr(app, 'blueprints') or 'api' not in app.blueprints:
        safe_log_info(logger, "Registering API blueprint...")
        app.register_blueprint(api_blueprint, url_prefix='/api')
        safe_log_info(logger, "Successfully registered API routes")
    else:
        safe_log_info(logger, "API blueprint already registered")
    
    # Skip route verification in test environment
    if not app.config.get('TESTING'):
        safe_log_info(logger, "Verifying protected routes...")
        
        # Check if any routes start with these prefixes
        protected_routes = [rule.rule for rule in app.url_map.iter_rules()
                          if rule.rule.startswith('/api/protected')]
        refresh_routes = [rule.rule for rule in app.url_map.iter_rules()
                        if rule.rule.startswith('/api/auth/refresh')]
        
        if not protected_routes:
            safe_log_error(logger, "Failed to register protected route")
        if not refresh_routes:
            safe_log_error(logger, "Failed to register refresh route")

    # Verify protected routes exist (only in non-test environment)
    if not app.config.get('TESTING'):
        all_routes = [rule.rule for rule in app.url_map.iter_rules()]
        required_routes = [
            '/api/protected',
            '/api/protected/route',
            '/api/auth/refresh'
        ]
        
        missing_routes = [route for route in required_routes
                         if route not in all_routes]
        
        if missing_routes:
            safe_log_error(logger, f"Missing required routes: {', '.join(missing_routes)}")

    # Function to run asyncio event loop in a separate thread
    def run_asyncio_loop(loop, handler, subscriptions):
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handler.start(subscriptions))
        except Exception as e_loop:
            safe_log_error(logger, f"Exception in run_asyncio_loop for RealtimeDataHandler: {e_loop}", exc_info=True)
        finally:
            safe_log_info(logger, "Closing asyncio event loop for RealtimeDataHandler.")
            loop.close()

    # Start the RealtimeDataHandler in a background thread
    if not app.config.get('TESTING'): # Don't start handler during tests
        safe_log_info(logger, "Starting RealtimeDataHandler...")
        # Define default subscriptions (can be made dynamic later)
        default_subscriptions = [
            {'exchange': 'binance', 'symbol': 'BTCUSDT'},
            {'exchange': 'binance', 'symbol': 'ETHUSDT'}
        ]
        
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=run_asyncio_loop, args=(loop, realtime_handler, default_subscriptions), daemon=True)
        thread.start()
        
        # Ensure handler stops on exit
        def stop_handler():
            safe_log_info(logger, "atexit: stop_handler initiated...")
            
            if loop.is_running():
                async def stop_async_realtime_handler():
                    await realtime_handler.stop()
                
                future = asyncio.run_coroutine_threadsafe(stop_async_realtime_handler(), loop)
                try:
                    future.result(timeout=10)
                    safe_log_info(logger, "atexit: RealtimeDataHandler.stop() completed successfully.")
                except asyncio.TimeoutError:
                    safe_log_error(logger, "atexit: Timeout waiting for RealtimeDataHandler.stop() to complete.")
                except Exception as e_stop:
                    safe_log_error(logger, f"atexit: Error during RealtimeDataHandler.stop(): {e_stop}", exc_info=True)
            else:
                safe_log_warning(logger, "atexit: Event loop for RealtimeDataHandler was not running. Cannot call stop_async().")

            safe_log_info(logger, "atexit: Signaling application-level logging shutdown...")
            signal_logging_shutdown() # Signal that our app considers logging to be shutting down
            
            safe_log_info(logger, "atexit: Explicitly shutting down Python logging system...")
            logging.shutdown()
            # After this, safe_log will use print() because is_logging_active() will be false.
            print(f"INFO (atexit fallback): Python logging system explicitly shut down at {datetime.now()}.")
            safe_log_info(logger, "atexit: stop_handler finished.") # This will use print()

        atexit.register(stop_handler)
        safe_log_info(logger, "RealtimeDataHandler startup sequence in app.py complete; stop_handler registered.")

    return app

# Create app instance
if os.getenv('PYTEST_CURRENT_TEST'):
    # In test environment, ensure we don't create multiple app instances
    if 'app' not in globals():
        app = create_app()
else:
    app = create_app()


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@jwt_required()
def dashboard():
    current_user = get_jwt_identity()
    safe_log_info(current_app.logger, f"Dashboard accessed by user: {current_user}")
    return render_template('dashboard.html')

@app.route('/backtest')
@jwt_required()
def backtest():
    return render_template('backtest.html')

@app.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"error": "Missing username or password"}), 400

        # Proxy to auth service
        result, status = current_app.auth_service.login(data)
        if status != 200:
            return jsonify(result), status
            
        # Set cookie with token from auth service
        response = jsonify(result)
        response.set_cookie(
            'access_token_cookie',
            value=result['access_token'],
            httponly=True,
            secure=os.getenv('FLASK_ENV') == 'production',
            samesite='Lax'
        )
        return response, 200

    except Exception as e:
        safe_log_error(current_app.logger, f"Login error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500



@app.route('/api/get-news')
@jwt_required()
def get_news():
    # For demo purposes, return static news data
    news = [
        {
            "title": "Bitcoin Breaks $50,000 Barrier Again",
            "source": "CryptoNews",
            "date": "2023-10-15",
            "url": "#",
            "summary": "Bitcoin has surged past $50,000 again, reaching its highest level since May."
        },
        {
            "title": "Ethereum Upgrade Scheduled for Next Month",
            "source": "BlockchainToday",
            "date": "2023-10-14",
            "url": "#",
            "summary": "Ethereum developers have announced the next major upgrade, promising improved scalability."
        },
        {
            "title": "Regulatory Changes Impact Crypto Markets",
            "source": "CoinDesk",
            "date": "2023-10-13",
            "url": "#",
            "summary": "New regulatory guidelines have been proposed, causing market fluctuations."
        }
    ]
    return jsonify(news)

# Main entry point for running the app directly
if __name__ == '__main__':
    app = create_app()
    # Use SocketIO's run method which integrates with Flask's development server
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # socketio.run(app, debug=True, host='0.0.0.0', port=port)
    # Use threading for async tasks with Flask dev server
    socketio.run(app, debug=True, host='0.0.0.0', port=port, use_reloader=False) # use_reloader=False important for background threads
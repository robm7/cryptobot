import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable # Added Callable
from decimal import Decimal

import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker # Added sessionmaker
from sqlalchemy.sql import select, and_

import os

from database.db import engine as db_engine
from trade.models.trade import Trade as InternalTrade
from utils.exchange_interface import ExchangeInterface, get_exchange_api
from services.notification.service import NotificationService, NotificationChannel, NotificationTemplate, UserPreferences
from services.notification.providers import NotificationProviderFactory

logger = logging.getLogger(__name__)

RECONCILIATION_PERIOD_HOURS = 24
MISMATCH_ALERT_THRESHOLD_PERCENT = 0.1

class TradeReconciliationJob:
    def __init__(self, db_session_factory: Callable[[], Any], notification_service: Optional[NotificationService] = None):
        self.db_session_factory = db_session_factory
        
        if notification_service:
            self.notification_service = notification_service
        else:
            email_provider_config = {}
            if os.getenv("SYSTEM_SMTP_SERVER") and \
               os.getenv("SYSTEM_SMTP_USER") and \
               os.getenv("SYSTEM_SMTP_PASSWORD") and \
               os.getenv("SYSTEM_SENDER_EMAIL"):
                email_provider_config = {
                    "smtp_server": os.getenv("SYSTEM_SMTP_SERVER"),
                    "smtp_port": int(os.getenv("SYSTEM_SMTP_PORT", 587)),
                    "smtp_user": os.getenv("SYSTEM_SMTP_USER"),
                    "smtp_password": os.getenv("SYSTEM_SMTP_PASSWORD"),
                    "sender_email": os.getenv("SYSTEM_SENDER_EMAIL")
                }
            
            provider_configs = {}
            if email_provider_config:
                provider_configs[NotificationChannel.EMAIL] = email_provider_config
            
            self.notification_service = NotificationService(provider_configs=provider_configs)
            logger.info("TradeReconciliationJob: NotificationService initialized with default email config from ENV if available.")

            if "system_alert" not in self.notification_service.templates:
                alert_template = NotificationTemplate(
                    name="system_alert",
                    subject="CryptoBot System Alert: {alert_title}",
                    body="Alert Details:\n\n{alert_message}\n\nExchange: {exchange_name}\nTimestamp: {timestamp}",
                    channels=[NotificationChannel.EMAIL]
                )
                self.notification_service.add_template(alert_template)
                logger.info("Added default 'system_alert' template to NotificationService.")

            self.system_alert_recipient_id = os.getenv("SYSTEM_ALERT_RECIPIENT_USER_ID", "cryptobot_admin")
            self.system_alert_email = os.getenv("SYSTEM_ALERT_RECIPIENT_EMAIL")

            if self.system_alert_email and self.system_alert_recipient_id not in self.notification_service.user_prefs:
                try:
                    prefs = UserPreferences(
                        user_id=self.system_alert_recipient_id,
                        email=self.system_alert_email, # type: ignore
                        preferred_channels=[NotificationChannel.EMAIL]
                    )
                    self.notification_service.update_user_preferences(prefs)
                    logger.info(f"Set up system alert recipient '{self.system_alert_recipient_id}' with email '{self.system_alert_email}'.")
                except Exception as e:
                    logger.error(f"Failed to set up system alert recipient due to invalid email '{self.system_alert_email}': {e}")
                    self.system_alert_recipient_id = None


    async def _fetch_internal_trades(self, start_time: datetime, end_time: datetime, exchange_name: str) -> List[Dict]:
        logger.info(f"Fetching internal trades for {exchange_name} from {start_time} to {end_time}")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = SessionLocal()
        trades_data = []
        try:
            query = select(InternalTrade).where(
                InternalTrade.exchange == exchange_name,
                InternalTrade.timestamp >= start_time,
                InternalTrade.timestamp < end_time
            ).order_by(InternalTrade.timestamp.desc())
            results = session.execute(query).scalars().all()
            for trade in results:
                trades_data.append({
                    "internal_trade_id": trade.id,
                    "exchange_order_id": trade.order_id,
                    "symbol": trade.symbol,
                    "side": trade.side.lower() if hasattr(trade.side, 'lower') else str(trade.side),
                    "amount": trade.amount,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat(),
                    "fee": trade.fee,
                    "fee_currency": trade.fee_currency
                })
            logger.info(f"Fetched {len(trades_data)} internal trades for {exchange_name}.")
        except Exception as e:
            logger.exception(f"Error fetching internal trades for {exchange_name}: {e}")
        finally:
            session.close()
        return trades_data

    async def _fetch_exchange_trades(self, exchange_api: ExchangeInterface, symbols_to_check: List[str], start_time: datetime, end_time: datetime) -> List[Dict]:
        logger.info(f"Fetching exchange trades for {exchange_api.exchange_name} from {start_time} to {end_time} for symbols: {symbols_to_check if symbols_to_check else 'all relevant (if supported)'}")
        all_exchange_trades_normalized: List[Dict] = []
        start_timestamp_ms = int(start_time.timestamp() * 1000)
        end_timestamp_ms = int(end_time.timestamp() * 1000)
        fetch_method_name = "get_my_trades_history"

        if not symbols_to_check:
            if hasattr(exchange_api, fetch_method_name) and not getattr(exchange_api, 'requires_symbol_for_trade_history', True):
                try:
                    logger.info(f"Attempting to fetch all account trades for {exchange_api.exchange_name}...")
                    trades_page = await getattr(exchange_api, fetch_method_name)(
                        start_time=start_timestamp_ms,
                        end_time=end_timestamp_ms,
                        limit=200 
                    )
                    for trade_data in trades_page:
                        all_exchange_trades_normalized.append(self._normalize_exchange_trade(trade_data, exchange_api.exchange_name))
                    logger.info(f"Fetched {len(all_exchange_trades_normalized)} trades for all symbols from {exchange_api.exchange_name}.")
                except Exception as e:
                    logger.exception(f"Error fetching all account trades from {exchange_api.exchange_name}: {e}")
            else:
                logger.warning(f"Exchange {exchange_api.exchange_name} requires symbols for fetching trade history or method not available, and no symbols were provided. Skipping exchange fetch.")
                return []
        else:
            for symbol in symbols_to_check:
                try:
                    logger.debug(f"Fetching trades for symbol {symbol} on {exchange_api.exchange_name}")
                    last_trade_id = None
                    limit_per_call = 100
                    while True:
                        if not hasattr(exchange_api, fetch_method_name):
                            logger.error(f"Exchange interface for {exchange_api.exchange_name} missing method '{fetch_method_name}'")
                            break
                        current_page_trades = await getattr(exchange_api, fetch_method_name)(
                            symbol=symbol,
                            start_time=start_timestamp_ms,
                            end_time=end_timestamp_ms,
                            limit=limit_per_call,
                            from_id=last_trade_id
                        )
                        if not current_page_trades:
                            break
                        for trade_data in current_page_trades:
                            all_exchange_trades_normalized.append(self._normalize_exchange_trade(trade_data, exchange_api.exchange_name))
                        last_trade_id = current_page_trades[-1].get('id')
                        if len(current_page_trades) < limit_per_call:
                            break
                        await asyncio.sleep(0.2)
                except Exception as e:
                    logger.exception(f"Error fetching trades for symbol {symbol} from {exchange_api.exchange_name}: {e}")
        
        logger.info(f"Fetched and normalized a total of {len(all_exchange_trades_normalized)} trades from {exchange_api.exchange_name}.")
        return all_exchange_trades_normalized

    def _normalize_exchange_trade(self, ex_trade: Dict, exchange_name: str) -> Dict:
        # Basic normalization, ensure all keys are present even if None
        normalized = {
            "exchange_order_id": str(ex_trade.get("id") or ex_trade.get("orderId") or ex_trade.get("trade_id")),
            "symbol": ex_trade.get("symbol"),
            "side": None,
            "amount": Decimal(0),
            "price": Decimal(0),
            "timestamp": None,
            "fee": Decimal(0),
            "fee_currency": None
        }

        raw_side = ex_trade.get("side")
        if raw_side:
            normalized["side"] = str(raw_side).lower()
        elif ex_trade.get("isBuyer") is True:
             normalized["side"] = "buy"
        elif ex_trade.get("isBuyer") is False: # Check explicitly for False, as it could be None
             normalized["side"] = "sell"
        
        raw_amount = ex_trade.get("qty") or ex_trade.get("executedQty") or ex_trade.get("size") or ex_trade.get("filled_size")
        if raw_amount is not None:
            normalized["amount"] = Decimal(str(raw_amount))

        raw_price = ex_trade.get("price")
        if raw_price is not None:
            normalized["price"] = Decimal(str(raw_price))
        
        raw_time = ex_trade.get("time") or ex_trade.get("timestamp") or ex_trade.get("created_at")
        if raw_time is not None:
            try:
                # Handle various timestamp formats (ms, s, ISO string)
                if isinstance(raw_time, (int, float)) and raw_time > 1e11 : # Likely ms
                    normalized["timestamp"] = datetime.fromtimestamp(raw_time / 1000).isoformat()
                elif isinstance(raw_time, (int, float)): # Likely s
                    normalized["timestamp"] = datetime.fromtimestamp(raw_time).isoformat()
                elif isinstance(raw_time, str):
                     normalized["timestamp"] = datetime.fromisoformat(raw_time.replace("Z", "+00:00")).isoformat()
            except ValueError:
                logger.warning(f"Could not parse timestamp: {raw_time}")

        raw_fee = ex_trade.get("commission") or ex_trade.get("fee")
        if raw_fee is not None:
            normalized["fee"] = Decimal(str(raw_fee))
        
        normalized["fee_currency"] = ex_trade.get("commissionAsset") or ex_trade.get("fee_currency")

        return normalized

    async def reconcile_trades(self, exchange_name: str, api_key: str, api_secret: str, passphrase: Optional[str] = None):
        logger.info(f"Starting trade reconciliation for exchange: {exchange_name}")
        exchange_api = get_exchange_api(exchange_name, api_key, api_secret, passphrase)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=RECONCILIATION_PERIOD_HOURS)

        try:
            internal_trades_list = await self._fetch_internal_trades(start_time, end_time, exchange_name)
            symbols_in_internal_trades = sorted(list(set(t['symbol'] for t in internal_trades_list if t.get('symbol'))))
            
            if not symbols_in_internal_trades:
                logger.info(f"No internal trades found for {exchange_name} in the period. Will attempt to fetch all exchange trades if supported by API.")
            
            exchange_trades_list = await self._fetch_exchange_trades(exchange_api, symbols_in_internal_trades, start_time, end_time)
            
            internal_trades_map = {t['exchange_order_id']: t for t in internal_trades_list if t.get('exchange_order_id')}
            exchange_trades_map = {t['exchange_order_id']: t for t in exchange_trades_list if t.get('exchange_order_id')}

            mismatches: List[Dict[str, Any]] = []
            
            for internal_ex_id, internal_trade in internal_trades_map.items():
                ex_trade = exchange_trades_map.get(internal_ex_id)
                if not ex_trade:
                    mismatches.append({"type": "missing_on_exchange", "details": internal_trade, "reason": "Not found by exchange_order_id"})
                else:
                    internal_amount = Decimal(str(internal_trade.get('amount', 0)))
                    ex_amount = Decimal(str(ex_trade.get('amount', 0)))
                    internal_price = Decimal(str(internal_trade.get('price', 0)))
                    ex_price = Decimal(str(ex_trade.get('price', 0)))

                    if not (internal_trade.get('symbol') == ex_trade.get('symbol') and
                            internal_trade.get('side') == ex_trade.get('side') and
                            abs(internal_amount - ex_amount) < Decimal('0.00000001') and
                            abs(internal_price - ex_price) < Decimal('0.00000001')):
                        mismatches.append({
                            "type": "detail_mismatch", 
                            "internal_trade": internal_trade, 
                            "exchange_trade": ex_trade
                        })
            
            for ex_id, ex_trade in exchange_trades_map.items():
                if ex_id not in internal_trades_map:
                    mismatches.append({"type": "missing_in_db", "details": ex_trade, "reason": "Not found by exchange_order_id"})
            
            total_internal_trades = len(internal_trades_list)
            total_unique_exchange_trades = len(exchange_trades_map)
            
            logger.info(f"Reconciliation for {exchange_name}: Internal Trades Fetched={total_internal_trades}, Unique Exchange Trades Fetched={total_unique_exchange_trades}, Mismatches Found={len(mismatches)}")

            if mismatches:
                mismatch_summary = f"Found {len(mismatches)} discrepancies for {exchange_name}:\n"
                for i, mismatch in enumerate(mismatches[:10]):
                    mismatch_summary += f"  - Mismatch {i+1}: Type: {mismatch['type']}, Reason: {mismatch.get('reason', 'N/A')}, Details: {mismatch.get('details') or mismatch}\n"
                logger.warning(mismatch_summary)
                
                if self.notification_service and self.system_alert_recipient_id:
                    relevant_trade_count = max(total_internal_trades, total_unique_exchange_trades)
                    if relevant_trade_count > 0:
                        mismatch_percent = (len(mismatches) / relevant_trade_count) * 100
                        if mismatch_percent > MISMATCH_ALERT_THRESHOLD_PERCENT:
                            alert_title = "High Trade Mismatch Rate"
                            alert_message_content = f"High trade mismatch rate for {exchange_name}: {mismatch_percent:.2f}% ({len(mismatches)} mismatches out of approx {relevant_trade_count} relevant trades).\n\nSummary of first 10 mismatches:\n{mismatch_summary}"
                            logger.error(f"ALERT: {alert_title} - {alert_message_content}")
                            await self.notification_service.send_notification(
                                user_id=self.system_alert_recipient_id,
                                template_name="system_alert",
                                context={
                                    "alert_title": alert_title,
                                    "alert_message": alert_message_content,
                                    "exchange_name": exchange_name,
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                force_channel=NotificationChannel.EMAIL
                            )
            else:
                logger.info(f"No trade discrepancies found for {exchange_name}.")

        except Exception as e:
            error_message = f"Critical error during trade reconciliation for {exchange_name}: {str(e)}"
            logger.exception(error_message)
            if self.notification_service and self.system_alert_recipient_id:
                await self.notification_service.send_notification(
                    user_id=self.system_alert_recipient_id,
                    template_name="system_alert",
                    context={
                        "alert_title": "Trade Reconciliation CRITICAL Error",
                        "alert_message": error_message,
                        "exchange_name": exchange_name,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    force_channel=NotificationChannel.EMAIL
                )
        finally:
            if hasattr(exchange_api, 'close_session') and callable(getattr(exchange_api, 'close_session')):
                 await exchange_api.close_session()
            elif hasattr(exchange_api, 'close') and callable(getattr(exchange_api, 'close')):
                 await exchange_api.close()

async def run_daily_reconciliation():
    db_session_factory = lambda: Session(db_engine) # Example factory
    
    # Initialize NotificationService instance (or get it from a central place)
    # This setup is simplified; provider_configs should come from secure config.
    email_provider_config = {}
    if os.getenv("SYSTEM_SMTP_SERVER") and \
       os.getenv("SYSTEM_SMTP_USER") and \
       os.getenv("SYSTEM_SMTP_PASSWORD") and \
       os.getenv("SYSTEM_SENDER_EMAIL"):
        email_provider_config = {
            "smtp_server": os.getenv("SYSTEM_SMTP_SERVER"),
            "smtp_port": int(os.getenv("SYSTEM_SMTP_PORT", 587)),
            "smtp_user": os.getenv("SYSTEM_SMTP_USER"),
            "smtp_password": os.getenv("SYSTEM_SMTP_PASSWORD"),
            "sender_email": os.getenv("SYSTEM_SENDER_EMAIL")
        }
    provider_configs = {}
    if email_provider_config:
        provider_configs[NotificationChannel.EMAIL] = email_provider_config
    
    notification_service_instance = NotificationService(provider_configs=provider_configs)
    if "system_alert" not in notification_service_instance.templates:
        alert_template = NotificationTemplate(
            name="system_alert",
            subject="CryptoBot System Alert: {alert_title}",
            body="Alert Details:\n\n{alert_message}\n\nExchange: {exchange_name}\nTimestamp: {timestamp}",
            channels=[NotificationChannel.EMAIL]
        )
        notification_service_instance.add_template(alert_template)

    system_alert_recipient_id = os.getenv("SYSTEM_ALERT_RECIPIENT_USER_ID", "cryptobot_admin")
    system_alert_email = os.getenv("SYSTEM_ALERT_RECIPIENT_EMAIL")
    if system_alert_email and system_alert_recipient_id not in notification_service_instance.user_prefs:
        try:
            prefs = UserPreferences(
                user_id=system_alert_recipient_id,
                email=system_alert_email, # type: ignore
                preferred_channels=[NotificationChannel.EMAIL]
            )
            notification_service_instance.update_user_preferences(prefs)
        except Exception as e:
            logger.error(f"Failed to set up system alert recipient for job: {e}")


    job = TradeReconciliationJob(db_session_factory, notification_service_instance)
    
    binance_api_key = os.getenv("BINANCE_API_KEY")
    binance_api_secret = os.getenv("BINANCE_API_SECRET")

    if binance_api_key and binance_api_secret:
        await job.reconcile_trades("binance", binance_api_key, binance_api_secret)
    else:
        logger.warning("Binance API keys not configured. Skipping Binance reconciliation.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(run_daily_reconciliation())
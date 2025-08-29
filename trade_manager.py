import MetaTrader5 as mt5
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from config import TRADING_SETTINGS, RISK_SETTINGS

class TradeManager:
    """Executes and manages trades with proper risk management."""
    
    def __init__(self, mt5_connector):
        self.mt5_connector = mt5_connector
        self.logger = logging.getLogger(__name__)
        
    def calculate_lot_size(self, symbol: str, stop_loss_pips: int, risk_amount: float = None) -> float:
        """
        Calculate position size based on risk management rules.
        
        Args:
            symbol (str): Trading symbol
            stop_loss_pips (int): Stop loss in pips
            risk_amount (float, optional): Risk amount in account currency
            
        Returns:
            float: Calculated lot size
        """
        try:
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return TRADING_SETTINGS['lot_size']
            
            # Get symbol info
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return TRADING_SETTINGS['lot_size']
            
            # Calculate risk amount if not provided
            if risk_amount is None:
                risk_amount = account_info['balance'] * RISK_SETTINGS['risk_per_trade']
            
            # Calculate pip value
            pip_value = symbol_info['contract_size'] * symbol_info['point']
            if symbol.endswith('JPY'):
                pip_value *= 100  # Adjust for JPY pairs
            
            # Calculate lot size
            lot_size = risk_amount / (stop_loss_pips * pip_value)
            
            # Round to lot step
            lot_step = symbol_info['lot_step']
            lot_size = round(lot_size / lot_step) * lot_step
            
            # Apply min/max limits
            lot_size = max(symbol_info['minimum_lot'], lot_size)
            lot_size = min(symbol_info['maximum_lot'], lot_size)
            
            return lot_size
            
        except Exception as e:
            self.logger.error(f"Error calculating lot size: {e}")
            return TRADING_SETTINGS['lot_size']
    
    def place_market_order(self, symbol: str, order_type: str, volume: float, 
                          stop_loss: float = None, take_profit: float = None,
                          comment: str = "") -> Optional[Dict[str, Any]]:
        """
        Place a market order.
        
        Args:
            symbol (str): Trading symbol
            order_type (str): 'BUY' or 'SELL'
            volume (float): Lot size
            stop_loss (float, optional): Stop loss price
            take_profit (float, optional): Take profit price
            comment (str): Order comment
            
        Returns:
            Optional[Dict]: Order result or None if failed
        """
        if not self.mt5_connector.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Get current price
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                self.logger.error(f"Failed to get current price for {symbol}")
                return None
            
            # Determine order type and price
            if order_type.upper() == 'BUY':
                mt5_order_type = mt5.ORDER_TYPE_BUY
                price = price_info['ask']
            elif order_type.upper() == 'SELL':
                mt5_order_type = mt5.ORDER_TYPE_SELL
                price = price_info['bid']
            else:
                self.logger.error(f"Invalid order type: {order_type}")
                return None
            
            # Create request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": TRADING_SETTINGS['slippage'],
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Order send failed - no result")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"Order successful: {order_type} {volume} {symbol} at {result.price}")
            
            return {
                'ticket': result.order,
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'price': result.price,
                'sl': stop_loss,
                'tp': take_profit,
                'time': datetime.now(),
                'comment': comment,
                'retcode': result.retcode,
            }
            
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    def place_pending_order(self, symbol: str, order_type: str, volume: float,
                           price: float, stop_loss: float = None, take_profit: float = None,
                           comment: str = "") -> Optional[Dict[str, Any]]:
        """
        Place a pending order.
        
        Args:
            symbol (str): Trading symbol
            order_type (str): 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'
            volume (float): Lot size
            price (float): Order price
            stop_loss (float, optional): Stop loss price
            take_profit (float, optional): Take profit price
            comment (str): Order comment
            
        Returns:
            Optional[Dict]: Order result or None if failed
        """
        if not self.mt5_connector.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Map order type
            order_type_map = {
                'BUY_LIMIT': mt5.ORDER_TYPE_BUY_LIMIT,
                'SELL_LIMIT': mt5.ORDER_TYPE_SELL_LIMIT,
                'BUY_STOP': mt5.ORDER_TYPE_BUY_STOP,
                'SELL_STOP': mt5.ORDER_TYPE_SELL_STOP,
            }
            
            if order_type.upper() not in order_type_map:
                self.logger.error(f"Invalid pending order type: {order_type}")
                return None
            
            mt5_order_type = order_type_map[order_type.upper()]
            
            # Create request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": TRADING_SETTINGS['slippage'],
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Pending order send failed - no result")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Pending order failed: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"Pending order successful: {order_type} {volume} {symbol} at {price}")
            
            return {
                'ticket': result.order,
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'price': price,
                'sl': stop_loss,
                'tp': take_profit,
                'time': datetime.now(),
                'comment': comment,
                'retcode': result.retcode,
            }
            
        except Exception as e:
            self.logger.error(f"Error placing pending order: {e}")
            return None
    
    def close_position(self, ticket: int, volume: float = None) -> Optional[Dict[str, Any]]:
        """
        Close a position.
        
        Args:
            ticket (int): Position ticket
            volume (float, optional): Volume to close (None for full close)
            
        Returns:
            Optional[Dict]: Close result or None if failed
        """
        if not self.mt5_connector.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.logger.error(f"Position {ticket} not found")
                return None
            
            position = positions[0]
            
            # Determine close parameters
            if volume is None:
                volume = position.volume
            
            # Determine order type for closing
            if position.type == mt5.ORDER_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": TRADING_SETTINGS['slippage'],
                "magic": 234000,
                "comment": f"Close position {ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Position close failed - no result")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Position close failed: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"Position {ticket} closed successfully")
            
            return {
                'ticket': ticket,
                'close_price': result.price,
                'volume_closed': volume,
                'time': datetime.now(),
                'retcode': result.retcode,
            }
            
        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {e}")
            return None
    
    def cancel_order(self, ticket: int) -> Optional[Dict[str, Any]]:
        """
        Cancel a pending order.
        
        Args:
            ticket (int): Order ticket
            
        Returns:
            Optional[Dict]: Cancel result or None if failed
        """
        if not self.mt5_connector.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Create cancel request
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
            }
            
            # Send cancel request
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Order cancel failed - no result")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order cancel failed: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"Order {ticket} cancelled successfully")
            
            return {
                'ticket': ticket,
                'time': datetime.now(),
                'retcode': result.retcode,
            }
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {ticket}: {e}")
            return None
    
    def modify_position(self, ticket: int, stop_loss: float = None, 
                       take_profit: float = None) -> Optional[Dict[str, Any]]:
        """
        Modify stop loss and/or take profit of a position.
        
        Args:
            ticket (int): Position ticket
            stop_loss (float, optional): New stop loss price
            take_profit (float, optional): New take profit price
            
        Returns:
            Optional[Dict]: Modify result or None if failed
        """
        if not self.mt5_connector.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                self.logger.error(f"Position {ticket} not found")
                return None
            
            position = positions[0]
            
            # Create modify request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": stop_loss if stop_loss is not None else position.sl,
                "tp": take_profit if take_profit is not None else position.tp,
            }
            
            # Send modify request
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Position modify failed - no result")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Position modify failed: {result.retcode} - {result.comment}")
                return None
            
            self.logger.info(f"Position {ticket} modified successfully")
            
            return {
                'ticket': ticket,
                'sl': stop_loss,
                'tp': take_profit,
                'time': datetime.now(),
                'retcode': result.retcode,
            }
            
        except Exception as e:
            self.logger.error(f"Error modifying position {ticket}: {e}")
            return None
    
    def calculate_sl_tp_prices(self, symbol: str, order_type: str, entry_price: float,
                              sl_pips: int, tp_pips: int) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit prices.
        
        Args:
            symbol (str): Trading symbol
            order_type (str): 'BUY' or 'SELL'
            entry_price (float): Entry price
            sl_pips (int): Stop loss in pips
            tp_pips (int): Take profit in pips
            
        Returns:
            Tuple[float, float]: (stop_loss_price, take_profit_price)
        """
        try:
            # Get symbol info for pip calculation
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return None, None
            
            pip_size = symbol_info['point']
            if symbol.endswith('JPY'):
                pip_size *= 100  # Adjust for JPY pairs
            
            if order_type.upper() == 'BUY':
                sl_price = entry_price - (sl_pips * pip_size)
                tp_price = entry_price + (tp_pips * pip_size)
            else:  # SELL
                sl_price = entry_price + (sl_pips * pip_size)
                tp_price = entry_price - (tp_pips * pip_size)
            
            # Round to symbol digits
            digits = symbol_info['digits']
            sl_price = round(sl_price, digits)
            tp_price = round(tp_price, digits)
            
            return sl_price, tp_price
            
        except Exception as e:
            self.logger.error(f"Error calculating SL/TP prices: {e}")
            return None, None

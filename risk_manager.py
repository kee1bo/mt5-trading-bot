import logging
from typing import Dict, Any, Optional
from config import RISK_SETTINGS

class RiskManager:
    """Implements risk management rules and position sizing."""
    
    def __init__(self, mt5_connector, trade_manager):
        self.mt5_connector = mt5_connector
        self.trade_manager = trade_manager
        self.logger = logging.getLogger(__name__)
        self.daily_loss = 0.0
        self.max_drawdown_reached = False
        
    def check_trading_allowed(self) -> bool:
        """
        Check if trading is allowed based on risk parameters.
        
        Returns:
            bool: True if trading is allowed, False otherwise
        """
        try:
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            # Check maximum positions
            positions = self.mt5_connector.get_positions()
            if positions and len(positions) >= RISK_SETTINGS.get('max_positions', 5):
                self.logger.warning("Maximum positions reached")
                return False
            
            # Check daily loss limit
            if self._check_daily_loss_limit(account_info):
                self.logger.warning("Daily loss limit reached")
                return False
            
            # Check maximum drawdown
            if self._check_max_drawdown(account_info):
                self.logger.warning("Maximum drawdown reached")
                return False
            
            # Check if trading is allowed on the account
            if not account_info.get('trade_allowed', True):
                self.logger.warning("Trading not allowed on this account")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trading allowance: {e}")
            return False
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss_price: float, risk_amount: float = None) -> float:
        """
        Calculate position size based on risk management rules.
        
        Args:
            symbol (str): Trading symbol
            entry_price (float): Entry price
            stop_loss_price (float): Stop loss price
            risk_amount (float, optional): Risk amount in account currency
            
        Returns:
            float: Calculated lot size
        """
        try:
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return 0.0
            
            # Calculate risk amount if not provided
            if risk_amount is None:
                risk_amount = account_info['balance'] * RISK_SETTINGS['risk_per_trade']
            
            # Get symbol info
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return 0.0
            
            # Calculate stop loss distance in pips
            pip_size = symbol_info['point']
            if symbol.endswith('JPY'):
                pip_size *= 100
            
            stop_loss_pips = abs(entry_price - stop_loss_price) / pip_size
            
            # Calculate pip value
            pip_value = symbol_info['contract_size'] * pip_size
            
            # Calculate position size
            position_size = risk_amount / (stop_loss_pips * pip_value)
            
            # Apply lot step rounding
            lot_step = symbol_info['lot_step']
            position_size = round(position_size / lot_step) * lot_step
            
            # Apply min/max limits
            min_lot = symbol_info['minimum_lot']
            max_lot = symbol_info['maximum_lot']
            position_size = max(min_lot, min(max_lot, position_size))
            
            # Additional risk checks
            position_size = self._apply_additional_risk_limits(position_size, account_info, symbol_info)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def validate_trade(self, symbol: str, order_type: str, volume: float,
                      entry_price: float = None, stop_loss: float = None,
                      take_profit: float = None) -> Dict[str, Any]:
        """
        Validate a trade before execution.
        
        Args:
            symbol (str): Trading symbol
            order_type (str): Order type
            volume (float): Lot size
            entry_price (float, optional): Entry price
            stop_loss (float, optional): Stop loss price
            take_profit (float, optional): Take profit price
            
        Returns:
            Dict[str, Any]: Validation result
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'adjusted_volume': volume,
        }
        
        try:
            # Check if trading is allowed
            if not self.check_trading_allowed():
                result['valid'] = False
                result['errors'].append("Trading not allowed due to risk limits")
                return result
            
            # Get symbol info
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                result['valid'] = False
                result['errors'].append(f"Invalid symbol: {symbol}")
                return result
            
            # Check if symbol trading is allowed
            if not symbol_info.get('trade_allowed', True):
                result['valid'] = False
                result['errors'].append(f"Trading not allowed for symbol: {symbol}")
                return result
            
            # Validate volume
            min_lot = symbol_info['minimum_lot']
            max_lot = symbol_info['maximum_lot']
            lot_step = symbol_info['lot_step']
            
            if volume < min_lot:
                result['adjusted_volume'] = min_lot
                result['warnings'].append(f"Volume adjusted to minimum: {min_lot}")
            elif volume > max_lot:
                result['adjusted_volume'] = max_lot
                result['warnings'].append(f"Volume adjusted to maximum: {max_lot}")
            
            # Ensure volume is properly stepped
            stepped_volume = round(volume / lot_step) * lot_step
            if stepped_volume != volume:
                result['adjusted_volume'] = stepped_volume
                result['warnings'].append(f"Volume adjusted to lot step: {stepped_volume}")
            
            # Validate stop loss and take profit distances
            if stop_loss and entry_price:
                if not self._validate_sl_tp_distance(symbol, entry_price, stop_loss, "SL"):
                    result['warnings'].append("Stop loss too close to entry price")
            
            if take_profit and entry_price:
                if not self._validate_sl_tp_distance(symbol, entry_price, take_profit, "TP"):
                    result['warnings'].append("Take profit too close to entry price")
            
            # Check margin requirements
            margin_info = self._check_margin_requirements(symbol, result['adjusted_volume'])
            if not margin_info['sufficient']:
                result['valid'] = False
                result['errors'].append("Insufficient margin for trade")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating trade: {e}")
            result['valid'] = False
            result['errors'].append(f"Validation error: {e}")
            return result
    
    def update_trailing_stops(self) -> None:
        """Update trailing stops for open positions."""
        if not RISK_SETTINGS.get('trailing_stop', False):
            return
        
        try:
            positions = self.mt5_connector.get_positions()
            if not positions:
                return
            
            trailing_distance_pips = RISK_SETTINGS.get('trailing_stop_distance', 5)
            
            for position in positions:
                self._update_position_trailing_stop(position, trailing_distance_pips)
                
        except Exception as e:
            self.logger.error(f"Error updating trailing stops: {e}")
    
    def _check_daily_loss_limit(self, account_info: Dict[str, Any]) -> bool:
        """Check if daily loss limit is reached."""
        try:
            max_daily_loss = account_info['balance'] * RISK_SETTINGS['max_daily_loss']
            current_loss = abs(min(0, account_info['profit']))
            
            if current_loss >= max_daily_loss:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking daily loss limit: {e}")
            return True
    
    def _check_max_drawdown(self, account_info: Dict[str, Any]) -> bool:
        """Check if maximum drawdown is reached."""
        try:
            max_drawdown = account_info['balance'] * RISK_SETTINGS['max_drawdown']
            current_drawdown = account_info['balance'] - account_info['equity']
            
            if current_drawdown >= max_drawdown:
                self.max_drawdown_reached = True
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking max drawdown: {e}")
            return True
    
    def _apply_additional_risk_limits(self, position_size: float, 
                                     account_info: Dict[str, Any],
                                     symbol_info: Dict[str, Any]) -> float:
        """Apply additional risk limits to position size."""
        try:
            # Limit position size based on free margin
            free_margin = account_info.get('free_margin', 0)
            required_margin = position_size * symbol_info['contract_size'] / account_info.get('leverage', 1)
            
            if required_margin > free_margin * 0.5:  # Use max 50% of free margin
                max_position_size = (free_margin * 0.5 * account_info.get('leverage', 1)) / symbol_info['contract_size']
                position_size = min(position_size, max_position_size)
            
            # Ensure position size doesn't exceed maximum risk per trade
            max_risk_amount = account_info['balance'] * RISK_SETTINGS['risk_per_trade']
            max_position_value = max_risk_amount * 10  # Conservative multiplier
            max_lots_by_value = max_position_value / symbol_info['contract_size']
            position_size = min(position_size, max_lots_by_value)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error applying additional risk limits: {e}")
            return position_size
    
    def _validate_sl_tp_distance(self, symbol: str, entry_price: float, 
                                sl_tp_price: float, type_str: str) -> bool:
        """Validate stop loss or take profit distance."""
        try:
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return False
            
            min_distance = symbol_info.get('stops_level', 10) * symbol_info['point']
            actual_distance = abs(entry_price - sl_tp_price)
            
            return actual_distance >= min_distance
            
        except Exception as e:
            self.logger.error(f"Error validating {type_str} distance: {e}")
            return False
    
    def _check_margin_requirements(self, symbol: str, volume: float) -> Dict[str, Any]:
        """Check if sufficient margin is available for the trade."""
        try:
            account_info = self.mt5_connector.get_account_info()
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            
            if not account_info or not symbol_info:
                return {'sufficient': False, 'required': 0, 'available': 0}
            
            # Estimate required margin
            required_margin = (volume * symbol_info['contract_size']) / account_info.get('leverage', 1)
            available_margin = account_info.get('free_margin', 0)
            
            return {
                'sufficient': available_margin >= required_margin,
                'required': required_margin,
                'available': available_margin,
            }
            
        except Exception as e:
            self.logger.error(f"Error checking margin requirements: {e}")
            return {'sufficient': False, 'required': 0, 'available': 0}
    
    def _update_position_trailing_stop(self, position: Dict[str, Any], 
                                      trailing_distance_pips: int) -> None:
        """Update trailing stop for a single position."""
        try:
            symbol = position['symbol']
            ticket = position['ticket']
            position_type = position['type']
            current_price = position['price_current']
            current_sl = position.get('sl', 0)
            
            # Get symbol info for pip calculation
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return
            
            pip_size = symbol_info['point']
            if symbol.endswith('JPY'):
                pip_size *= 100
            
            # Calculate new trailing stop
            if position_type == 'BUY':
                new_sl = current_price - (trailing_distance_pips * pip_size)
                # Only move SL up for BUY positions
                if current_sl == 0 or new_sl > current_sl:
                    self.trade_manager.modify_position(ticket, stop_loss=new_sl)
            else:  # SELL
                new_sl = current_price + (trailing_distance_pips * pip_size)
                # Only move SL down for SELL positions
                if current_sl == 0 or new_sl < current_sl:
                    self.trade_manager.modify_position(ticket, stop_loss=new_sl)
                    
        except Exception as e:
            self.logger.error(f"Error updating trailing stop for position {position.get('ticket', 'unknown')}: {e}")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        try:
            account_info = self.mt5_connector.get_account_info()
            positions = self.mt5_connector.get_positions()
            
            if not account_info:
                return {}
            
            total_profit = sum(pos.get('profit', 0) for pos in positions or [])
            total_volume = sum(pos.get('volume', 0) for pos in positions or [])
            
            return {
                'balance': account_info['balance'],
                'equity': account_info['equity'],
                'margin': account_info['margin'],
                'free_margin': account_info['free_margin'],
                'margin_level': account_info.get('margin_level', 0),
                'total_profit': total_profit,
                'total_positions': len(positions or []),
                'total_volume': total_volume,
                'daily_loss_limit': account_info['balance'] * RISK_SETTINGS['max_daily_loss'],
                'max_drawdown_limit': account_info['balance'] * RISK_SETTINGS['max_drawdown'],
                'risk_per_trade': RISK_SETTINGS['risk_per_trade'],
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk metrics: {e}")
            return {}

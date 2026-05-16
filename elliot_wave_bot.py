import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import logging
import json
import os
import threading
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from datetime import datetime

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("elliot_wave_bot.log")
    ]
)
logger = logging.getLogger("ElliotWaveBot")

# Configuration - Replace with your own API credentials
CONFIG = {
    'exchange_id': 'binance', 
    'api_key': os.getenv('EXCHANGE_API_KEY', 'YOUR_API_KEY'), 
    'api_secret': os.getenv('EXCHANGE_API_SECRET', 'YOUR_API_SECRET'),
    'passphrase': os.getenv('EXCHANGE_PASSPHRASE', 'YOUR_PASSPHRASE'),
    'testnet': True,
    'symbol': 'BTC/USDT', # CCXT standard symbol
    'tf_macro': '15m',
    'tf_entry': '1m',
    'risk_per_trade': 0.10, 
    'impulse_threshold': 0.004, 
    'leverage': 5
}

class ElliotWaveBot:
    def __init__(self, config: Dict):
        self.config = config
        self.console = Console()
        self.stats = {
            'initial_balance': 0.0,
            'current_balance': 0.0,
            'total_pnl': 0.0,
            'wins': 0,
            'losses': 0,
            'trades': [],
            'current_setup': {
                'wave_count': 0,
                'macro_bias': 'NEUTRAL',
                'direction': None,
                'status': 'Scanning...'
            }
        }
        exchange_id = config.get('exchange_id', 'binance')
        exchange_class = getattr(ccxt, exchange_id)
        
        exchange_params = {
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'future' # General futures/swap setting
            }
        }
        
        if config.get('api_key') and config['api_key'] != 'YOUR_API_KEY':
            exchange_params['apiKey'] = config['api_key']
        if config.get('api_secret') and config['api_secret'] != 'YOUR_API_SECRET':
            exchange_params['secret'] = config['api_secret']
        if config.get('passphrase') and config['passphrase'] != 'YOUR_PASSPHRASE':
            exchange_params['password'] = config['passphrase']

        self.exchange = exchange_class(exchange_params)
        if config.get('testnet'):
            self.exchange.set_sandbox_mode(True)
            logger.info(f"{exchange_id.upper()} TESTNET MODE ENABLED")
            
        self.symbol = config['symbol']
        self.active_position = None
        
        self.stats['initial_balance'] = self.get_balance()
        self.stats['current_balance'] = self.stats['initial_balance']
        logger.info(f"Initialized ElliotWaveBot on {exchange_id} for {self.symbol}")
        self.save_dashboard_data()

    def save_dashboard_data(self):
        """Save current bot state to JSON for the web dashboard"""
        try:
            data = {
                'symbol': self.symbol,
                'exchange': self.config['exchange_id'],
                'testnet': self.config.get('testnet', False),
                'stats': self.stats,
                'active_position': self.active_position,
                'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open('dashboard_data.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving dashboard data: {e}")

    def fetch_data(self, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Fetch OHLCV data using CCXT"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Exchange Fetch Error: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return df
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        for period in [8, 13, 21, 55, 200]:
            df.ta.ema(length=period, append=True)
        return df

    def get_macro_bias(self, df_macro: pd.DataFrame) -> str:
        if len(df_macro) < 200: return "NEUTRAL"
        last = df_macro.iloc[-1]
        close = last['close']
        e8, e13, e21, e55, e200 = last['EMA_8'], last['EMA_13'], last['EMA_21'], last['EMA_55'], last['EMA_200']
        if e200 < e55 < e21 < e13 < e8 < close:
            return "BULLISH"
        elif e200 > e55 > e21 > e13 > e8 > close:
            return "BEARISH"
        return "NEUTRAL"

    def detect_impulse(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[Optional[str], float, float]:
        recent = df.tail(lookback)
        low, high = recent['low'].min(), recent['high'].max()
        impulse_up = (high - low) / low
        impulse_down = (high - low) / high
        if impulse_up >= self.config['impulse_threshold']:
            return "SHORT", low, high 
        elif impulse_down >= self.config['impulse_threshold']:
            return "LONG", high, low
        return None, 0.0, 0.0

    def get_swing_pivots(self, df: pd.DataFrame, strength: int = 2) -> List[Dict]:
        pivots = []
        for i in range(strength, len(df) - strength):
            is_high = all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, strength+1)) and \
                      all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, strength+1))
            is_low = all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, strength+1)) and \
                     all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, strength+1))
            if is_high: pivots.append({'index': i, 'price': df['high'].iloc[i], 'type': 'H'})
            if is_low: pivots.append({'index': i, 'price': df['low'].iloc[i], 'type': 'L'})
        return pivots

    def validate_elliott_wave(self, pivots: List[Dict], direction: str) -> Tuple[bool, Dict]:
        """Simplified heuristic for a 5-wave Elliott structure"""
        if len(pivots) < 6: return False, {}
        recent = pivots[-6:]
        types = "".join([p['type'] for p in recent])
        if direction == "SHORT" and types == "LHLHLH":
            w1_start, w1, w2, w3, w4, w5 = recent
            if w3['price'] > w1['price'] and w5['price'] > w3['price'] and w2['price'] > w1_start['price'] and w4['price'] > w2['price'] and w4['price'] > w1['price']:
                return True, {'w3': w3, 'w5': w5}
        elif direction == "LONG" and types == "HLHLHL":
            w1_start, w1, w2, w3, w4, w5 = recent
            if w3['price'] < w1['price'] and w5['price'] < w3['price'] and w2['price'] < w1_start['price'] and w4['price'] < w2['price'] and w4['price'] < w1['price']:
                return True, {'w3': w3, 'w5': w5}
        return False, {}

    def check_divergence_and_momentum(self, df: pd.DataFrame, wave_count: Dict, direction: str) -> Tuple[bool, bool, bool]:
        w3_idx, w5_idx = wave_count['w3']['index'], wave_count['w5']['index']
        rsi_w3 = df['RSI_14'].iloc[w3_idx]
        rsi_w5 = df['RSI_14'].iloc[w5_idx]
        hist_w3 = df['MACDh_12_26_9'].iloc[w3_idx]
        hist_w5 = df['MACDh_12_26_9'].iloc[w5_idx]
        macd = df['MACD_12_26_9']
        signal = df['MACDs_12_26_9']
        crossovers = 0
        for i in range(1, 30):
            if (macd.iloc[-i-1] > signal.iloc[-i-1] and macd.iloc[-i] < signal.iloc[-i]) or \
               (macd.iloc[-i-1] < signal.iloc[-i-1] and macd.iloc[-i] > signal.iloc[-i]):
                crossovers += 1
        crossover_ok = crossovers >= 2
        if direction == "SHORT":
            rsi_div = (rsi_w5 < rsi_w3) and (rsi_w5 > 70)
            hist_loss = (hist_w5 < hist_w3)
            return rsi_div, hist_loss, crossover_ok
        elif direction == "LONG":
            rsi_div = (rsi_w5 > rsi_w3) and (rsi_w5 < 30)
            hist_loss = (abs(hist_w5) < abs(hist_w3))
            return rsi_div, hist_loss, crossover_ok

    def get_balance(self) -> float:
        try:
            balance = self.exchange.fetch_balance()
            if 'USDT' in balance['total']:
                val = float(balance['total']['USDT'])
            else:
                val = 0.0
            self.stats['current_balance'] = val
            return val
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return self.stats['current_balance']

    def execute_ladder(self, direction: str, imp_start: float, imp_end: float, w5_price: float):
        logger.info(f"INITIATING {direction} LADDER")
        self.stats['current_setup']['status'] = f"Executing {direction} Ladder..."
        self.save_dashboard_data()
        
        balance = self.get_balance()
        if balance < 1:
            logger.error(f"Insufficient balance to trade.")
            return

        diff = imp_end - imp_start
        fib_382 = imp_end - (0.382 * diff) if direction == "SHORT" else imp_end + (0.382 * abs(diff))
        fib_618 = imp_end - (0.618 * diff) if direction == "SHORT" else imp_end + (0.618 * abs(diff))
        sl_price = w5_price * 1.015 if direction == "SHORT" else w5_price * 0.985
        
        margin_usdt = balance * self.config['risk_per_trade']
        total_position_usdt = margin_usdt * self.config['leverage']
        side = 'sell' if direction == "SHORT" else 'buy'
        
        try:
            # Set Leverage
            try: self.exchange.set_leverage(self.config['leverage'], self.symbol)
            except: pass

            # Entry 1: 40% at Market
            amt1 = (total_position_usdt * 0.40) / w5_price
            self.exchange.create_order(self.symbol, 'market', side, amt1)
            
            # Entry 2: 35% at 0.3% worse price (Limit)
            price2 = w5_price * (1.003 if direction == "SHORT" else 0.997)
            amt2 = (total_position_usdt * 0.35) / price2
            self.exchange.create_order(self.symbol, 'limit', side, amt2, price2)

            # Entry 3: 25% at 61.8% Fib (Limit)
            price3 = fib_618
            amt3 = (total_position_usdt * 0.25) / price3
            self.exchange.create_order(self.symbol, 'limit', side, amt3, price3)

            # Note: TP/SL logic simplified for universal exchange support
            logger.info(f"Position executed. TP target: {fib_382}, SL target: {sl_price}")

            self.active_position = {
                'direction': direction, 'entry_price': w5_price, 'tp_price': fib_382, 'sl_price': sl_price,
                'total_qty': (total_position_usdt / w5_price), 'open_time': time.time()
            }
            self.save_dashboard_data()
        except Exception as e:
            logger.error(f"EXECUTION FAILED: {e}")

    def monitor_position(self, current_price: float):
        if not self.active_position: return
        # Simple local monitor for demo purposes
        target = self.active_position['tp_price']
        stop = self.active_position['sl_price']
        
        if (self.active_position['direction'] == "SHORT" and current_price <= target) or \
           (self.active_position['direction'] == "LONG" and current_price >= target):
            logger.info("TARGET REACHED!")
            self.stats['wins'] += 1
            self.active_position = None
        elif (self.active_position['direction'] == "SHORT" and current_price >= stop) or \
             (self.active_position['direction'] == "LONG" and current_price <= stop):
            logger.warning("STOP LOSS TRIGGERED!")
            self.stats['losses'] += 1
            self.active_position = None
        self.save_dashboard_data()

    def generate_dashboard(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(Layout(name="stats", ratio=1), Layout(name="market", ratio=1))

        header_text = Text(f"ELLIOT WAVE TRADING BOT - {datetime.now().strftime('%H:%M:%S')} - {self.symbol}", style="bold cyan", justify="center")
        layout["header"].update(Panel(header_text, border_style="cyan"))

        stats_table = Table(show_header=False, box=None)
        pnl = self.stats['current_balance'] - self.stats['initial_balance']
        stats_table.add_row("Balance", f"[bold white]${self.stats['current_balance']:,.2f}[/]")
        stats_table.add_row("Total PnL", f"[{'green' if pnl >= 0 else 'red'}]${pnl:,.2f}[/]")
        stats_table.add_row("Wins/Losses", f"[green]{self.stats['wins']}[/] / [red]{self.stats['losses']}[/]")
        layout["stats"].update(Panel(stats_table, title="Account Stats", border_style="white"))

        market_table = Table(show_header=False, box=None)
        market_table.add_row("Status", f"[bold yellow]{self.stats['current_setup']['status']}[/]")
        market_table.add_row("Macro Bias", f"[white]{self.stats['current_setup']['macro_bias']}[/]")
        market_table.add_row("Wave Count", f"[cyan]{self.stats['current_setup']['wave_count']}[/]")
        market_table.add_row("Impulse", f"[bold]{self.stats['current_setup']['direction'] or 'NONE'}[/]")
        layout["market"].update(Panel(market_table, title="Market Setup", border_style="cyan"))

        if self.active_position:
            pos_text = Text(f"ACTIVE {self.active_position['direction']}: Entry {self.active_position['entry_price']:.2f} | Target {self.active_position['tp_price']:.2f}", style="bold yellow", justify="center")
            layout["footer"].update(Panel(pos_text, border_style="yellow", title="Active Position"))
        else:
            layout["footer"].update(Panel(Text("No Active Position", justify="center", style="dim"), border_style="dim"))
        return layout

    def run_cycle(self):
        self.stats['current_setup']['status'] = "Scanning market..."
        df_macro = self.calculate_indicators(self.fetch_data(self.config['tf_macro']))
        df_entry = self.calculate_indicators(self.fetch_data(self.config['tf_entry']))
        if df_macro.empty or df_entry.empty: return
        
        current_price = df_entry['close'].iloc[-1]
        macro_bias = self.get_macro_bias(df_macro)
        self.stats['current_setup']['macro_bias'] = macro_bias
        
        if self.active_position:
            self.monitor_position(current_price)
            self.save_dashboard_data()
            return

        direction, imp_start, imp_end = self.detect_impulse(df_entry)
        self.stats['current_setup']['direction'] = direction
        if not direction: 
            self.save_dashboard_data()
            return
            
        pivots = self.get_swing_pivots(df_entry)
        self.stats['current_setup']['wave_count'] = len(pivots)
        wave_valid, wave_count_details = self.validate_elliott_wave(pivots, direction)
        
        if wave_valid:
            rsi_div, hist_ok, cross_ok = self.check_divergence_and_momentum(df_entry, wave_count_details, direction)
            if rsi_div and hist_ok and cross_ok:
                self.execute_ladder(direction, imp_start, imp_end, current_price)
        
        self.save_dashboard_data()

if __name__ == "__main__":
    bot = ElliotWaveBot(CONFIG)
    def background_scan():
        while True:
            try: bot.run_cycle(); time.sleep(10)
            except: time.sleep(5)
    threading.Thread(target=background_scan, daemon=True).start()
    with Live(bot.generate_dashboard(), refresh_per_second=2, screen=True) as live:
        while True:
            try: live.update(bot.generate_dashboard()); time.sleep(0.5)
            except KeyboardInterrupt: break

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("ElliotWaveBacktester")

class ElliotWaveBacktester:
    def __init__(self, symbol='BTC/USDT', timeframe='5m', lookback_days=30):
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        self.exchange = ccxt.binance({'enableRateLimit': True})
        
        self.initial_balance = 10000.0
        self.balance = self.initial_balance
        self.trades = []

    def fetch_historical_data(self) -> pd.DataFrame:
        """Fetch historical data for backtesting"""
        logger.info(f"Fetching {self.lookback_days} days of {self.timeframe} data for {self.symbol}...")
        since = self.exchange.milliseconds() - (self.lookback_days * 24 * 60 * 60 * 1000)
        
        all_ohlcv = []
        while since < self.exchange.milliseconds():
            try:
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, since=since, limit=1000)
                if not ohlcv: break
                since = ohlcv[-1][0] + 1
                all_ohlcv.extend(ohlcv)
            except Exception as e:
                logger.error(f"Error fetching: {e}")
                break
                
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the trading indicator stack"""
        logger.info("Calculating indicators (RSI, MACD, EMAs)...")
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        for period in [8, 13, 21, 55, 200]:
            df.ta.ema(length=period, append=True)
        return df.dropna().reset_index(drop=True)

    def run_backtest(self, df: pd.DataFrame):
        """Simulate the trading logic over the historical dataset"""
        logger.info(f"Starting backtest on {len(df)} candles...")
        
        in_position = False
        pos_direction = None
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        pos_size = 0.0
        
        for i in range(200, len(df)):
            current = df.iloc[i]
            
            if in_position:
                if pos_direction == "SHORT":
                    if current['high'] >= stop_loss:
                        loss = pos_size * ((current['close'] - entry_price) / entry_price)
                        self.balance -= loss
                        self.trades.append({'type': 'LOSS', 'dir': 'SHORT', 'pnl': -loss})
                        in_position = False
                    elif current['low'] <= take_profit:
                        profit = pos_size * ((entry_price - take_profit) / entry_price)
                        self.balance += profit
                        self.trades.append({'type': 'WIN', 'dir': 'SHORT', 'pnl': profit})
                        in_position = False
                        
                elif pos_direction == "LONG":
                    if current['low'] <= stop_loss:
                        loss = pos_size * ((entry_price - current['close']) / entry_price)
                        self.balance -= loss
                        self.trades.append({'type': 'LOSS', 'dir': 'LONG', 'pnl': -loss})
                        in_position = False
                    elif current['high'] >= take_profit:
                        profit = pos_size * ((take_profit - entry_price) / entry_price)
                        self.balance += profit
                        self.trades.append({'type': 'WIN', 'dir': 'LONG', 'pnl': profit})
                        in_position = False
                continue

            # Impulse & Divergence Detection
            lookback_df = df.iloc[i-20:i]
            high_idx = lookback_df['high'].idxmax()
            low_idx = lookback_df['low'].idxmin()
            
            impulse_up = (lookback_df.loc[high_idx, 'high'] - lookback_df.loc[low_idx, 'low']) / lookback_df.loc[low_idx, 'low']
            impulse_down = (lookback_df.loc[high_idx, 'high'] - lookback_df.loc[low_idx, 'low']) / lookback_df.loc[high_idx, 'high']
            
            if impulse_up >= 0.04:
                rsi_now = current['RSI_14']
                rsi_prev = df.loc[high_idx, 'RSI_14']
                if current['high'] > df.loc[high_idx, 'high'] and rsi_now < rsi_prev and rsi_now > 70:
                    hist_now = current['MACDh_12_26_9']
                    hist_prev = df.loc[high_idx, 'MACDh_12_26_9']
                    if hist_now < hist_prev:
                        in_position = True
                        pos_direction = "SHORT"
                        entry_price = current['close']
                        stop_loss = current['high'] * 1.015
                        diff = current['high'] - lookback_df.loc[low_idx, 'low']
                        take_profit = current['high'] - (0.382 * diff)
                        pos_size = self.balance * 0.50
                        
            elif impulse_down >= 0.04:
                rsi_now = current['RSI_14']
                rsi_prev = df.loc[low_idx, 'RSI_14']
                if current['low'] < df.loc[low_idx, 'low'] and rsi_now > rsi_prev and rsi_now < 30:
                    hist_now = current['MACDh_12_26_9']
                    hist_prev = df.loc[low_idx, 'MACDh_12_26_9']
                    if abs(hist_now) < abs(hist_prev):
                        in_position = True
                        pos_direction = "LONG"
                        entry_price = current['close']
                        stop_loss = current['low'] * 0.985
                        diff = lookback_df.loc[high_idx, 'high'] - current['low']
                        take_profit = current['low'] + (0.382 * diff)
                        pos_size = self.balance * 0.50

    def print_results(self):
        """Output the compounding results"""
        wins = len([t for t in self.trades if t['type'] == 'WIN'])
        losses = len([t for t in self.trades if t['type'] == 'LOSS'])
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        logger.info("\n" + "="*40)
        logger.info("📊 ELLIOT WAVE BACKTEST RESULTS")
        logger.info("="*40)
        logger.info(f"Initial Balance: ${self.initial_balance:.2f}")
        logger.info(f"Final Balance:   ${self.balance:.2f}")
        logger.info(f"Net Profit:      ${self.balance - self.initial_balance:.2f} ({((self.balance - self.initial_balance)/self.initial_balance)*100:.2f}%)")
        logger.info(f"Total Trades:    {total_trades}")
        logger.info(f"Win Rate:        {win_rate:.1f}% ({wins}W / {losses}L)")
        logger.info("="*40)

if __name__ == "__main__":
    backtester = ElliotWaveBacktester(symbol='BTC/USDT', timeframe='5m', lookback_days=30)
    df_raw = backtester.fetch_historical_data()
    if not df_raw.empty:
        df_processed = backtester.calculate_indicators(df_raw)
        backtester.run_backtest(df_processed)
        backtester.print_results()
    else:
        logger.error("Failed to load historical data.")

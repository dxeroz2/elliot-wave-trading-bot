import time
from elliot_wave_bot import ElliotWaveBot, CONFIG

def run_mock_trade():
    print("Initializing bot for Mock Trade test...")
    bot = ElliotWaveBot(CONFIG)
    
    # Mock data for a LONG setup
    # Strategy: Impulse DOWN (sets up a LONG)
    direction = "LONG"
    imp_start = 68000.0  # High before drop
    imp_end = 65000.0    # Low after drop
    w5_price = 65100.0   # Current price
    
    print(f"\n[MOCK] Triggering {direction} Ladder Execution...")
    print(f"Impulse: {imp_start} -> {imp_end}")
    print(f"Current Price: {w5_price}")
    
    bot.execute_ladder(direction, imp_start, imp_end, w5_price)
    
    print("\n[MOCK] Trade logic triggered. Ensure EXCHANGE_API_KEY is set in your environment.")
    print("Wait 5 seconds for orders to process...")
    time.sleep(5)
    
    if bot.active_position:
        print("\n[SUCCESS] Bot successfully tracked the active position:")
        print(bot.active_position)
    else:
        print("\n[!] Check logs for errors. Order may have failed due to balance or permissions.")

if __name__ == "__main__":
    run_mock_trade()

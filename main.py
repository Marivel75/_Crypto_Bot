from src.collectors.market_collector import MarketCollector

if __name__ == "__main__":
    # Définir les paires et timeframes à collecter
    pairs = ["BTC/USDT", "ETH/USDT"]
    timeframes = ["1h", "4h"]

    collector = MarketCollector(pairs, timeframes)
    collector.fetch_and_store()

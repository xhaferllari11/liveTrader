import ccxt



print(ccxt.exchanges)


class Arbitrager:
    def __init__(self):
        self.exchanges = [
            ccxt.binanceus(),
            ccxt.bittrex(),
            # ccxt.coinbase(),   # coinbase has most currency pairs, by like 3 times the next highest, consider removing
            ccxt.gemini(),
            ccxt.kraken(),
            ccxt.livecoin(),
            ccxt.theocean()
        ]
        self.loadMarkets() #creates a markets variable in each exchange instance.  ex. exchages[0].markets will return markets
        common_tickers = self.getCommonTickers()
        # then only call fetch_tickers for common_tickers between exchanges
        self.startArbitrage()
    
    def loadMarkets(self):
        for e in self.exchanges:
            mkt = e.load_markets()

    def getCommonTickers(self):
        tickers = {}
        for e in self.exchanges:
            for symbol in list(e.markets.keys()):
                if symbol in tickers:
                    tickers[symbol].append(e.id)
                else:
                    tickers[symbol] = [e.id]

        ret_tickers = {}
        for key,val in tickers.items():
            if (len(val) > 1):
                ret_tickers[key] = val
        return ret_tickers

    def startArbitrage(self):
        print('---------------------------------------')
        pass


arbitObj = Arbitrager()
arbitObj.startArbitrage()


# • fetchMarkets (): Fetches a list of all available markets from an exchange and returns an array of markets
# (objects with properties such as symbol, base, quote etc.). Some exchanges do not have means for obtaining
# a list of markets via their online API. For those, the list of markets is hardcoded.
# 
# • fetchCurrencies (): Fetches all available currencies an exchange and returns an associative dictionary of
# currencies (objects with properties such as code, name, etc.). Some exchanges do not have means for obtaining
# currencies via their online API. For those, the currencies will be extracted from market pairs or hardcoded.
# 
# • loadMarkets ([reload]): Returns the list of markets as an object indexed by symbol and caches it with
# the exchange instance. Returns cached markets if loaded already, unless the reload = true flag is forced.
# 
# • fetchOrderBook (symbol[, limit = undefined[, params = {}]]): Fetch L2/L3 order
# book for a particular market trading symbol.
# 
# • fetchStatus ([, params = {}]): Returns information regarding the exchange status from either the
# info hardcoded in the exchange instance or the API, if available.
# 
# • fetchL2OrderBook (symbol[, limit = undefined[, params]]): Level 2 (priceaggregated) order book for a particular symbol.
# 
# • fetchTrades (symbol[, since[, [limit, [params]]]]): Fetch recent trades for a particular
# trading symbol.
# 
# • fetchTicker (symbol): Fetch latest ticker data by trading symbol.

# NOTE: use fetch_tickers() to get all ticker data. Some currencies, like Gemini Don't allow it
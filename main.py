import ccxt

class Arbitrager:
    def __init__(self):
        self.exchanges = {
            'binanceus': ccxt.binanceus(),
            'bittrex': ccxt.bittrex(),
            # 'coinbase': ccxt.coinbase(),   # coinbase has most currency pairs, by like 3 times the next highest, consider removing
            # 'gemini': ccxt.gemini(),
            # 'kraken': ccxt.kraken(),
            # 'livecoin': ccxt.livecoin(),
            # 'theocean': ccxt.theocean()
        }
        self.loadMarkets() #creates a markets variable in each exchange instance.  ex. exchages[0].markets will return markets
        self.commonTickers = self.getCommonTickers()
        # then only call fetch_tickers for common_tickers between exchanges
        self.minProfit = -10  #percent profit
        self.minVolume = 200 #in USD
        self.txfrCosts = []

    def loadMarkets(self):
        for key, e in self.exchanges.items():
            e.load_markets()

    def getCommonTickers(self):
        tickers = {}
        counter = 0     #only used in development 
        for key, e in self.exchanges.items():
            for symbol in list(e.markets.keys()):
                if (counter >2):      #only used in development
                    break
                if symbol in tickers:
                    counter +=1
                    tickers[symbol].append(key)
                else:
                    tickers[symbol] = [key]

        #keep the tickers that show up in more than 1 exchange
        retTickers = {}
        for key,val in tickers.items():
            if (len(val) > 1):
                retTickers[key] = val
        return retTickers


    def startArbitrage(self):
        print('---------------------------------------')
        self.currentBooks = self.getAllpairPrices()
        #calculate arb percent gain
        self.opportunities = self.findOpportunities()
        print(self.opportunities)

    def getAllpairPrices(self):
        prices = {}
        for tick, exchs in self.commonTickers.items():
            prices[tick] = {}
            for e in exchs:
                try:
                    prices[tick][e] = self.exchanges[e].fetchL2OrderBook(tick)
                except:
                    pass
        return prices

    def findOpportunities(self):
        opps = []         # this is a list of objs. each list is {highBid: {exch_name, buy_price, buy_amt}, lowAsk:  {exch_name, sell_price, sell_amt}, max_profit: number}
        for tick in self.currentBooks:
            highesBid = {"exchName": None, "buyPrice": 0, "buyAmt": 0}
            lowestAsk = {"exchName": None, "sellPrice": 9999999999, "sellAmt":0 }
            for e in self.currentBooks[tick]:
                # looking at second best bid and second best ask and put highest buy and lowest sell exchanges in the 2 variable defined
                eBid = self.currentBooks[tick][e]['bids'][1][0]     
                eAsk = self.currentBooks[tick][e]['asks'][1][0]     #NOTE: these disregard volume best volume and ask/bid price
                if (eBid > highesBid['buyPrice']):
                    highesBid = {
                        "exchName": e, "buyPrice": eBid,
                        "buyAmt": self.currentBooks[tick][e]['bids'][1][1]
                    }
                if (eAsk < lowestAsk['sellPrice']):
                    lowestAsk = {
                        "exchName": e, "sellPrice": eAsk,
                        "sellAmt": self.currentBooks[tick][e]['asks'][1][1]
                    }
            #NOTE: need to add logic in case could not get orderbook for more than 1 exchange

            # check if profit above threshhold
            diffPercentage = (highesBid['buyPrice'] - lowestAsk['sellPrice'])/highesBid['buyPrice']*100 
            if (diffPercentage > self.minProfit):
                opps.append({
                    'ticker': tick,
                    'highBid': highesBid,
                    'lowAsk': lowestAsk,
                    'maxProfit': diffPercentage
                })
        return opps


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




# prices format
# {
#   'ADA/USD': {
#     ccxt.binanceus(): {
#       'bids': [
#         [0.0351, 30469.9],
#         [0.035, 92924.9],
#         [0.0349, 31921.3],
#         [0.0348, 40142.7],
#       ],
#       'asks': [
#         [0.0352, 20522.7],
#         [0.0353, 483960.4],
#         [0.0354, 17653.0],
#         [0.0355, 20784.4],
#       ],
#       'timestamp': None,
#       'datetime': None,
#       'nonce': 20533044
#     },
#     ccxt.bittrex(): {
#       'bids': [
#         [0.0351, 31753.01909686],
#         [0.03501, 819.230988],
#         [0.035, 18538.48686046],
#         [0.03485, 1662.91923571],
#         [0.0181, 18853.59116022]
#       ],
#       'asks': [
#         [0.0352, 31795.302],
#         [0.03534, 291.556],
#         [0.03548, 28421.0],
#         [0.0355, 3457.08376422],
#         [0.03551, 175241.0],
#       ],
#       'timestamp': None,
#       'datetime': None,
#       'nonce': None
#     }
#   },
#   'ADA/USDT': {
#     ccxt.binanceus(): {
#       'bids': [
#         [0.03505, 10666.2],
#         [0.03504, 8561.6],
#         [0.03503, 3688.2],
#       ],
#       'asks': [
#         [0.03513, 8539.7],
#         [0.03514, 20113.1],
#         [0.03515, 110480.3],
#         [0.03686, 29934.4]
#       ],
#       'timestamp': None,
#       'datetime': None,
#       'nonce': 20234290
#     },
#     ccxt.bittrex(): {
#       'bids': [
#         [0.03504917, 13880.03],
#         [0.03503272, 53435.20844155],
#         [0.03483659, 21925.0],
#         [0.03483658, 21324.19255234],
#       ],
#       'asks': [
#         [0.03525624, 50000.0],
#         [0.03525625, 13889.801],
#         [0.03525626, 16856.0],
#         [0.03525627, 4633.6864924],
#       ],
#       'timestamp': None,
#       'datetime': None,
#       'nonce': None
#     }
#   }
# }




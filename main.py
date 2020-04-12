import ccxt
import config


# NOTE: dynamically calculate max profit function

class Arbitrager:
    def __init__(self):
        self.exchanges = {
            'binanceus': ccxt.binanceus(),
            'bittrex': ccxt.bittrex(),
            # 'coinbase': ccxt.coinbase(),   # coinbase has most currency pairs, by like 3 times the next highest, consider removing. Also coinbase limits API to 3-6 calls/sec
            'gemini': ccxt.gemini(),
            'kraken': ccxt.kraken(),
            'livecoin': ccxt.livecoin(),
            'theocean': ccxt.theocean(),
            # 'okex': ccxt.okex(),            #Canadian, does not allow us
            'bitmart': ccxt.bitmart(),
            'cex': ccxt.cex(),              #EU
            'bitbay': ccxt.bitbay(),        #EU
            # 'bcex': ccxt.bcex(),            #candian exch, their API is updating
            'bitbay': ccxt.bitbay(),
            'paymium': ccxt.paymium(),
            'binance': ccxt.binance(),
            'okcoin': ccxt.okcoin(),
            'bitfinex': ccxt.bitfinex()      # non-US
        }
        self.loadMarkets() #creates a markets variable in each exchange instance.  ex. exchages[0].markets will return markets
        # these are tickers available on exchnage, but not US customers, or don't allow deposits/withdrawals
        self.unavailableTickers = {
            'binanceus': [],
            'bittrex': ['LUNA/BTC', 'ABBC/BTC','Capricoin/BTC','DRGN/BTC','CVT/BTC','NXT/BTC'],
            # 'coinbase': [],
            'gemini': [],
            'kraken': [],
            'livecoin': ['BTM/BTC', 'BTM/ETH', 'NANO/BTC','NANO/ETH', 'XTZ/BTC', 'XTZ/ETH','THETA/BTC','THETA/ETH','ABBC/BTC','ABBC/ETH','AE/BTC','AE/ETH','IOST/BTC','IOST/ETH'],
            'theocean': [],
            # 'okex': ['AET/ETH','AET/BTC'],             # does not allow US, but allows canadian
            'bitmart': [],
            'cex': [],
            'bitbay': [],
            # 'bcex': [],             #candian exch, their API is updating
            'bitbay': [],
            'paymium': [],
            'binance': [],
            'okcoin': [],
            'bitfinex': []
            }
        self.commonTickers = self.getCommonTickers()
        # then only call fetch_tickers for common_tickers between exchanges
        self.minProfit = 1  # percent profit
        self.minVolume = 200 # in USD NOTE: still need to incorporate this. I think coinmarketcap API has a quick conversion call
        self.txfrCosts = []


    def loadMarkets(self):
        print('___________Loading Markets______________')
        for key, e in self.exchanges.items():
            print(key)
            try:
                e.load_markets()
            except:
                print(f'ccxt does not support {e} or {e} has updated their API')

    def getCommonTickers(self):
        print('-----------getting common tickers---------------')
        tickers = {}
        counter = 0     #only used in development 
        for key, e in self.exchanges.items():
            print(key)
            for symbol in list(e.markets.keys()):
                # if (counter >80):      #only used in development
                #     break
                if (symbol not in self.unavailableTickers[key]):
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
        print('--------------Starting Arbitrage-------------------------')
        self.currentBooks = self.getAllpairPrices()
        #calculate arb percent gain
        self.ArbOpps2Way = self.findOpportunities()
        print(self.ArbOpps2Way)
        self.ArbOpps2Way.sort(reverse=True, key=lambda el: el['maxProfit'])
        print(self.ArbOpps2Way)
        print('_______________')
        try:
            print(self.currentBooks[self.ArbOpps2Way[0]['ticker']])
        except:
            print('did not find any opportunities')
        # after getting all the data, need to re-call APIs to get order book for top arb contenders
        # so we have most updated orders, calling all the available pairs took 3 minutes, coinbase throttled back also


    def getAllpairPrices(self):
        print('----------get all prices--------------')
        prices = {}
        for tick, exchs in self.commonTickers.items():
            print(f'-------{tick}---{exchs}----')
            prices[tick] = {}
            for e in exchs:
                try:
                    prices[tick][e] = self.exchanges[e].fetchL2OrderBook(tick)
                except:
                    print(f'Could not get orderbook for {tick} from {e}')
        return prices

    def findOpportunities(self):
        print('----------------finding opps--------------')
        opps = []         # this is a list of objs. each list is {highBid: {exch_name, buy_price, buy_amt}, lowAsk:  {exch_name, sell_price, sell_amt}, max_profit: number}
        for tick in self.currentBooks:
            highesBid = {"exchName": None, "buyPrice": 0, "buyAmt": 0}
            lowestAsk = {"exchName": None, "sellPrice": 9999999999, "sellAmt":0 }

            for e in self.currentBooks[tick]:
                # make sure there is more than 2 open orders
                if (len(self.currentBooks[tick][e]['bids']) > 2 and len(self.currentBooks[tick][e]['asks']) > 2):
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

            #in case could not get orderbook for more than 1 exchange, or bid/asd didn't update
            if ((lowestAsk['sellPrice'] != 9999999999) and (highesBid['buyPrice'] != 0)): 
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

    def verifyOrderBook(self, ticker, exchHighBid, exchLowAsk):
        try:
            bidOrderBook = self.exchanges[exchHighBid].fetchL2OrderBook(ticker)
            askOrderBook = self.exchanges[exchLowAsk].fetchL2OrderBook(ticker)
        except:
            print('could not verify order book to trade on')
            return False

    def getTradingAndTransactionCosts(self, ticker, exch1, exch2):
        pass

    def placeOrder(self, ticker, exch, amt):
        # place order
        pass
    
    def verifyBalance(self, ticker, exch):
        try:
            balance = self.exchanges[exch].fetch_balance()
            coin = ticker.split('/')[1]
            return balance['free'][coin]
        except:
            print('----- could not verify balance in {exch}')

    def tradeOnOpps(self, opp = None):
        if (opp == None):
            if (len(self.ArbOpps2Way) > 0):
                opp = self.ArbOpps2Way[0]
        if (opp == None):
            print('pass in a ticker and exchanges to trade in dict format')
            return
        # need to verify bc running arbitrage for all tickers takes 1-2 mins, order books changes
        bidExch = opp['highBid']['exchName']
        askExch = opp['lowAsk']['exchName']
        if (self.verifyOrderBook(opp['ticker'], bidExch, askExch) != False):
        # calc tx/trading costs
            txCosts = self.getTradingAndTransactionCosts(
                opp['ticker'], bidExch, askExch)  #default this to .001 BTC
            if (txCosts < 0):
                print(f"------could not get tx costs for {opp['ticker']}")
                return
            # calc max profit based on costs
            maxProfitTradeAmt = 1000
            maxProfitAskPrice = .00002

            # sign into accounts
            self.exchanges[askExch].apiKey = config[askExch]['API_KEY']
            self.exchanges[askExch].secret = config[askExch]['API_SECRET']
            self.exchanges[bidExch].apiKey = config[bidExch]['API_KEY']
            self.exchanges[bidExch].secret = config[bidExch]['API_SECRET']

            # verify funds in account
            funds = self.verifyBalance(opp['ticker'],askExch)
            if (funds > maxProfitTradeAmt/maxProfitAskPrice):  
                self.placeOrder(opp['ticker'],askExch,maxProfitTradeAmt)
                #verify trade executed
                #transfer funds
                #sell on high bid exch
            
        else:
            print('-----missed opportunity--------')
            # maybe ask user to try again or try next opportunity
            return
        

arbitObj = Arbitrager()
arbitObj.startArbitrage()
# arbitObj.tradeOnOpps()




#Previous Opps:
# BTM/BTC bittrex to livecoin
# NANO/BTC and NANO/ETH kraken to livecoin


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




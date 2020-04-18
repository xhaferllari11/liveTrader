import ccxt
import config
import copy


# NOTE: dynamically calculate max profit function

class Arbitrager:
    def __init__(self):
        self.exchanges = {
            'binanceus': ccxt.binanceus(),
            'bittrex': ccxt.bittrex(),
            # 'coinbase': ccxt.coinbase(),   # coinbase has most currency pairs, by like 3 times the next highest, consider removing. Also coinbase limits API to 3-6 calls/sec
            'gemini': ccxt.gemini(),
            # 'kraken': ccxt.kraken(),       # updating their API
            'livecoin': ccxt.livecoin(),
            'theocean': ccxt.theocean(),
            # 'okex': ccxt.okex(),            #Canadian, does not allow us
            'bitmart': ccxt.bitmart(),
            # 'cex': ccxt.cex(),  # EU
            # 'bitbay': ccxt.bitbay(),  # EU, Updating API
            # 'bcex': ccxt.bcex(),            #candian exch, their API is updating
            # 'bitbay': ccxt.bitbay(),
            'paymium': ccxt.paymium(),
            'binance': ccxt.binance(),
            'okcoin': ccxt.okcoin(),
            'bitfinex': ccxt.bitfinex()      # non-US
        }
        # creates a markets variable in each exchange instance.  ex. exchages[0].markets will return markets
        self.loadMarkets()
        # these are tickers available on exchnage, but not US customers, or don't allow deposits/withdrawals
        self.unavailableTickers = {
            'binanceus': [],
            'bittrex': ['LUNA/BTC', 'ABBC/BTC', 'Capricoin/BTC', 'DRGN/BTC', 'CVT/BTC', 'NXT/BTC'],
            # 'coinbase': [],
            'gemini': [],
            # 'kraken': [],               # Updating their API
            'livecoin': ['BTM/BTC', 'BTM/ETH', 'NANO/BTC', 'NANO/ETH', 'XTZ/BTC', 'XTZ/ETH', 'THETA/BTC', 'THETA/ETH', 'ABBC/BTC', 'ABBC/ETH', 'AE/BTC', 'AE/ETH', 'IOST/BTC', 'IOST/ETH'],
            'theocean': [],
            # 'okex': ['AET/ETH','AET/BTC'],             # does not allow US, but allows canadian
            'bitmart': [],
            # 'cex': [],
            # 'bitbay': [],
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
        # in USD NOTE: still need to incorporate this. I think coinmarketcap API has a quick conversion call
        self.minVolume = 200
        self.txfrCosts = []

    def loadMarkets(self):
        print('___________Loading Markets______________')
        for key, e in self.exchanges.items():
            print(key)
            try:
                e.load_markets()
            except:
                print(
                    f'Error: either reached API limits, ccxt not synced with {e}, or {e} updated their API')

    def getCommonTickers(self):
        print('-----------getting common tickers---------------')
        tickers = {}
        counter = 0  # only used in development
        for key, e in self.exchanges.items():
            print(key)
            for symbol in list(e.markets.keys()):
                if (counter >30):      #only used in development
                    break
                if (symbol not in self.unavailableTickers[key]):
                    if symbol in tickers:
                        counter += 1
                        tickers[symbol].append(key)
                    else:
                        tickers[symbol] = [key]

        # keep the tickers that show up in more than 1 exchange
        retTickers = {}
        for key, val in tickers.items():
            if (len(val) > 1):
                retTickers[key] = val
        return retTickers

    def startArbitrage(self):
        print('--------------Starting Arbitrage-------------------------')
        self.currentBooks = self.getAllpairPrices()
        # calculate arb percent gain
        self.ArbOpps2Way = self.findOpportunities()
        print(self.ArbOpps2Way)
        self.ArbOpps2Way.sort(reverse=True, key=lambda el: el['pctProfit'])
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
        # this is a list of objs. each list is {highBid: {exch_name, buy_price, buy_amt}, lowAsk:  {exch_name, sell_price, sell_amt}, max_profit: number}
        opps = []
        for tick in self.currentBooks:
            highesBid = {"exchName": None, "buyPrice": 0, "buyAmt": 0}
            lowestAsk = {"exchName": None,
                         "sellPrice": 9999999999, "sellAmt": 0}

            for e in self.currentBooks[tick]:
                # make sure there is more than 2 open orders
                if (len(self.currentBooks[tick][e]['bids']) > 2 and len(self.currentBooks[tick][e]['asks']) > 2):
                    # looking at second best bid and second best ask and put highest buy and lowest sell exchanges in the 2 variable defined
                    eBid = self.currentBooks[tick][e]['bids'][1][0]
                    # NOTE: these disregard volume best volume and ask/bid price
                    eAsk = self.currentBooks[tick][e]['asks'][1][0]
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

            # in case could not get orderbook for more than 1 exchange, or bid/asd didn't update
            if ((lowestAsk['sellPrice'] != 9999999999) and (highesBid['buyPrice'] != 0)):
                # check if profit above threshhold
                diffPercentage = (
                    highesBid['buyPrice'] - lowestAsk['sellPrice'])/highesBid['buyPrice']*100
                if (diffPercentage > self.minProfit):
                    opps.append({
                        'ticker': tick,
                        'highBid': highesBid,
                        'lowAsk': lowestAsk,
                        'pctProfit': diffPercentage,
                        'maxProfit': self.getActualProfit(tick, highesBid['exchName'], lowestAsk['exchName']) if diffPercentage > 0 else 0
                    })

        return opps

    def getActualProfit(self, ticker, bidExch, askExch):
        bidsAvailable = copy.deepcopy(self.currentBooks[ticker][bidExch]['bids'])
        asksAvialable = copy.deepcopy(self.currentBooks[ticker][askExch]['asks'])
        profit = 0
        tradeVol = 0
        maxAskPrice = 0
        #orderbook (bidsavailable and asksavailable) is list of touples, 1st pram is price, 2nd param is volume
        #this is a simulation of buying/selling until no more arb opportunity, to calc profit
        while (bidsAvailable[0][0] > asksAvialable[0][0]):
            if (asksAvialable[0][0] > maxAskPrice):
                maxAskPrice = asksAvialable[0][0]
            volumeToTrade = min(bidsAvailable[0][1], asksAvialable[0][1])
            tradeVol += volumeToTrade
            profit += volumeToTrade * (bidsAvailable[0][0]-asksAvialable[0][0])
            bidsAvailable[0][1] -= volumeToTrade
            asksAvialable[0][1] -= volumeToTrade
            bidsAvailable.pop(0) if bidsAvailable[0][1] == 0 else asksAvialable.pop(0)
            
        return {'profit': profit, 'volume': tradeVol, 'maxAskPrice': maxAskPrice}
            

    def verifyOrderBook(self, ticker, exchHighBid, exchLowAsk):
        try:
            bidOrderBook = self.exchanges[exchHighBid].fetchL2OrderBook(ticker)
            askOrderBook = self.exchanges[exchLowAsk].fetchL2OrderBook(ticker)
        except:
            print('could not verify order book to trade on')
            return False

    def getTradingAndTransactionCosts(self, ticker, exch1, exch2):
        # try catch block, return -1 if could not get tx costs
        return .1

    def placeOrder(self, ticker, exch, amt, orderType, price):
        self.exchanges[exch].apiKey = config.exchanges[exch]['API_KEY']
        self.exchanges[exch].secret = config.exchanges[exch]['API_SECRET']
        # place order
        if (orderType == 'buy'):
            try:
                order = self.exchanges[exch].createLimitBuyOrder(ticker, amt, price)
                print(f'----bought {amt} {ticker} at {exch}------')
                return order
            except:
                print(f'----did not execute {orderType} order of {ticker} at {exch}----')

        elif (orderType == 'sell'):
            try:
                order = self.exchanges[exch].createLimitSellOrder(ticker, amt, price)
                print(f'----sold {amt} {ticker} at {exch}------')
                return order
            except:
                print(f'----did not execute {orderType} order of {ticker} at {exch}----')
        

    def verifyBalance(self, ticker, exch):
        print(exch)
        print(self.exchanges[exch])
        self.exchanges[exch].apiKey = config.exchanges[exch]['API_KEY']
        self.exchanges[exch].secret = config.exchanges[exch]['API_SECRET']
        try:
            balance = self.exchanges[exch].fetch_balance()
            coin = ticker.split('/')[1]
            return balance['free'][coin]
        except:
            print('----- could not verify balance in {exch}')

    def tradeOnOpps(self, opp=None):
        # can trade on passed in opportunities or on arb opportunities in class
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
                opp['ticker'], bidExch, askExch)  # default this to .1 BTC
            if (txCosts < 0):
                print(f"------could not get tx costs for {opp['ticker']}")
                return
            # calc max profit based on costs
            maxProfitTradeAmt = opp['maxProfit']['volume']
            maxAskPrice = opp['maxProfit']['maxAskPrice']
            
            # verify funds in account
            funds = self.verifyBalance(opp['ticker'], askExch)
            if (funds > maxProfitTradeAmt/maxAskPrice):
                self.placeOrder(opp['ticker'], askExch, maxProfitTradeAmt, 'buy', maxAskPrice)
                # verify trade executed
                # transfer funds
                # sell on high bid exch
                # self.placeOrder(opp['ticker'], bidExch, tradedAmt, 'sell')

        else:
            print('-----missed opportunity--------')
            # maybe ask user to try again or try next opportunity
            return



arbitObj = Arbitrager()
# arbitObj.startArbitrage()
# arbitObj.tradeOnOpps()
print(arbitObj.verifyBalance('BAT/BTC','bittrex'))
print(arbitObj.placeOrder('BAT/BTC','bittrex', 225, 'sell', .00002363))


# Previous Opps:
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
#     'binanceus': {
#       'bids': [
#         [0.0357, 30469.9],
#         [0.0356, 92924.9],
#         [0.0351, 31921.3],
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
#     'bittrex': {
#       'bids': [
#         [0.0351, 31753.01909686],
#         [0.03501, 819.230988],
#         [0.035, 18538.48686046],
#         [0.03485, 1662.91923571],
#         [0.0181, 18853.59116022]
#       ],
#       'asks': [
#         [0.035, 31795.302],
#         [0.0351, 291.556],
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


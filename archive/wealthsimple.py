import requests
import json
import time


class wealthsimple(object):
    def __init__(self, email, password, MFA=None):
        if MFA == None:
            r = requests.post('https://trade-service.wealthsimple.com/auth/login',
                              data={'email': email, 'password': password})
        else:
            r = requests.post('https://trade-service.wealthsimple.com/auth/login',
                              data={'email': email, 'password': password, 'otp': MFA})
        try:
            self.access_token = r.headers['X-Access-Token']
            self.refresh_token = r.headers['X-Refresh-Token']
            print('Authenticated!')
        except:
            pass
        self.url = 'https://trade-service.wealthsimple.com'

    def refresh(self):
        try:
            r = requests.post(self.url+'/auth/refresh',
                              data={'refresh_token': self.refresh_token})
            self.access_token = r.headers['X-Access-Token']
            self.refresh_token = r.headers['X-Refresh-Token']
            return True
        except:
            return False

    def balance(self, account_id):
        try:
            r = requests.get(self.url+'/account', params={'account_id': account_id}, headers={
                             'authorization': self.access_token})
            return r.json()['buying_power']['amount']
        except:
            return False

    def positions(self, account_id):
        try:
            r = requests.get(self.url+'/account/positions', params={
                             'account_id': account_id}, headers={'authorization': self.access_token})
            return r.json()['results']
        except:
            return False

    def accounts(self):
        try:
            r = requests.get(self.url+'/account/list',
                             headers={'authorization': self.access_token})
            return r.json()['results']
        except:
            return False

    def activities(self, account_id, limit=20):
        try:
            r = requests.get(self.url+'/account/activities', params={
                             'account_id': account_id, 'limit': limit}, headers={'authorization': self.access_token})
            return r.json()['results']
        except:
            return False

    def tick_id(self, ticker, exchange=None):  # ex is NASDAQ, TSX-V, TSX, NYSE
        try:
            r = requests.get(self.url+'/securities', params={'query': ticker}, headers={
                             'authorization': self.access_token})
            for i in range(0, r.json()['total_count']):
                if (r.json()['results'][i]['stock']['symbol'] == ticker and r.json()['results'][i]['stock']['primary_exchange'] == exchange) or exchange == None:
                    return r.json()['results'][i]['id']
            return False
        except:
            return False

    def tick_info(self, ticker):
        try:
            r = requests.get(self.url+'/securities', params={'query': ticker}, headers={
                             'authorization': self.access_token})
            return r.json()
        except:
            return False

    def order_history(self):  # depreceated?
        try:
            r = requests.get(self.url+'/orders',
                             headers={'authorization': self.access_token})
            return r.json()
        except:
            return False

    # time_in_force options = "until_cancel", "day"
    def limit_buy(self, tick_id, quantity, price, account_id=None):
        try:
            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity,
                                  'order_type': 'buy_quantity',  'order_sub_type': 'limit', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity, 'order_type': 'buy_quantity',
                                  'order_sub_type': 'limit', 'account_id': account_id, 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']

        except:
            return False

    def stop_limit_buy(self, tick_id, quantity, price, stop_price, account_id=None):
        try:
            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'stop_price': stop_price, 'quantity': quantity,
                                  'order_type': 'buy_quantity',  'order_sub_type': 'stop_limit', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'stop_price': stop_price, 'quantity': quantity,
                                  'order_type': 'buy_quantity',  'order_sub_type': 'stop_limit', 'account_id': account_id, 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']

        except:
            return False

    def limit_sell(self, tick_id, quantity, price, account_id=None):
        try:
            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity,
                                  'order_type': 'sell_quantity',  'order_sub_type': 'limit', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity, 'order_type': 'sell_quantity',
                                  'order_sub_type': 'limit', 'account_id': account_id, 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
        except:
            return False

    def stop_limit_sell(self, tick_id, quantity, price, stop_price, account_id=None):
        try:
            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'stop_price': stop_price, 'quantity': quantity,
                                  'order_type': 'sell_quantity',  'order_sub_type': 'stop_limit', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'stop_price': stop_price, 'quantity': quantity,
                                  'order_type': 'sell_quantity', 'account_id': account_id,  'order_sub_type': 'stop_limit', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']

        except:
            return False

    # all market buys must have limit price
    def market_buy(self, tick_id, quantity, price=1, account_id=None):
        try:
            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity,
                                  'order_type': 'buy_quantity', 'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'limit_price': price, 'quantity': quantity, 'order_type': 'buy_quantity',
                                  'account_id': account_id,  'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
        except:
            return False

    # all market sells must have limit price
    def market_sell(self, tick_id, quantity, price=1, account_id=None):
        try:

            if account_id == None:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'market_value': price, 'quantity': quantity,
                                  'order_type': 'sell_quantity', 'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
            else:
                r = requests.post(self.url+'/orders', json={'security_id': tick_id, 'market_value': price, 'quantity': quantity, 'order_type': 'sell_quantity',
                                  'account_id': account_id,  'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization': self.access_token})
                return r.json()['order_id']
        except:
            return False

    def cancel_order(self, order_id):
        try:
            r = requests.delete(self.url+'/orders/'+order_id,
                                headers={'authorization': self.access_token})
            if r.status_code != 200:
                return False
            else:
                return True
        except:
            return False

    def fx_buyrate(self, currency='USD'):
        try:
            r = requests.get(self.url+'/forex',
                             headers={'authorization': self.access_token})
            return r.json()['USD']['buy_rate']
        except:
            return False

    def fx_sellrate(self, currency='USD'):
        try:
            r = requests.get(self.url+'/forex',
                             headers={'authorization': self.access_token})
            return r.json()[currency]['sell_rate']
        except:
            return False

    def get(self, endpoint, params='', json=''):

        r = requests.get(self.url+endpoint, params=params, json=json,
                         headers={'authorization': self.access_token})
        return r

    def post(self, endpoint, params='', json=''):

        r = requests.post(self.url+endpoint, params=params,
                          json=json, headers={'authorization': self.access_token})
        return r.json()

    def delete(self, endpoint, params='', json=''):

        r = requests.delete(self.url+endpoint, params=params,
                            json=json, headers={'authorization': self.access_token})
        return r.json()


def quote(ticker, source, asset_class='stocks'):
    if source.lower() == 'nasdaq':
        try:
            r = requests.get('https://api.nasdaq.com/api/quote/'+ticker+'/info', params={
                             'assetclass': asset_class}, headers={'User-Agent': 'PostmanRuntime/7.26.2', 'Accept': '*/*'}, timeout=3)

            return float(r.json()['data']['primaryData']['lastSalePrice'].strip('$'))
        except:
            return False

    elif source.lower() == 'tsx' or source.lower() == 'tmx':
        try:
            r = requests.post('https://app-money.tmx.com/graphql', json={"operationName": "getQuoteBySymbol", "variables": {"symbol": ticker, "locale": "en"},
                              "query": "query getQuoteBySymbol($symbol: String, $locale: String) {  getQuoteBySymbol(symbol: $symbol, locale: $locale) {    symbol    name    price}}"}, timeout=3)
            return float(r.json()['data']['getQuoteBySymbol']['price'])
        except:
            return False

    elif source.lower() == 'yahoo':  # for . ticker.replace('.','-',1) e.g. BPY.UN.TO-->BPY-UN.TO
        try:
            r = requests.get(
                'https://query1.finance.yahoo.com/v8/finance/chart/'+ticker, timeout=3)
            return float(r.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        except:
            return False

    elif source.lower() == 'webull':
        try:
            r = requests.get('https://quotes-gw.webullfintech.com/api/search/pc/tickers',
                             params={'keyword': ticker, 'regionId': 6, 'pageIndex': 1, 'pageSize': 3})
            for i in range(len(r.json()['data'])):
                if ticker == r.json()['data'][i]['symbol']:
                    ticker_id = r.json()['data'][i]['tickerId']
                    break
            r = requests.get('https://quoteapi.webullfintech.com/api/quote/tickerRealTimes/v5/' +
                             str(ticker_id), params={'includeSecu': 1, 'includeQuote': 1, 'more': 1})
            return r.json()
        except:
            return False
    else:
        return False


# below is an example to make it work input desired parameters

# create a wealthsimple class, replace email with your email and password with your password
#ws=wealthsimple('email', 'password')


# create a limit buy order for appl

# first get the security id for AAPL by calling tick_id with AAPL as its parameter e.g ws.tick_id(ticker) where ticker is the stock symbol or ticker
#ticker_id=ws.tick_id('AAPL', 'NASDAQ')

# then enter the ticker_id along with the disired limit price and quantity e.g. ws.limit_buy(ticker_id, limit_price, quantity) where ticker_id is the
# variable we just got from the first step limit_price is the highest price you are willing to pay and quantity is the number of shares you want to purchase
# in this case we are buying 1 share of AAPL at the limit price of 300
#order_id=ws.limit_buy(ticker_id, 300, 1)

# changelog
# changelog 1/29/2021 added 2FA support. Input an addtional 2FA parameter when initializing the wealtsimple object. Use Authy to generate 2FA code or generate with app as required
# changelog 1/30/2021 added stop_limit_sell and stop_limit_buy, added custom request (get,post,delete) parameter, added account selection option, changed tick_id identifying factor to exchange name
# changelog 1/31/2021 added postions and order inqury, account id mandatory for balance, added results key to return to simplify output
# changelog 2/2/2021 rearranged limit buy variables
# changelog 2/3/2021 tweaked market order values
# changelog 2/4/2021 tick_id error patched

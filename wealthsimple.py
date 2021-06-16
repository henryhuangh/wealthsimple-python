import requests
import json
import time

class wealthsimple(object):
        def __init__(self, email, password):
                r=requests.post('https://trade-service.wealthsimple.com/auth/login', data={'email':email, 'password':password})
                self.access_token=r.headers['X-Access-Token']
                self.refresh_token=r.headers['X-Refresh-Token']
                self.url='https://trade-service.wealthsimple.com'
                
        def refresh(self):
                try:
                        r=requests.post(self.url+'/auth/refresh', data={'refresh_token':self.refresh_token})
                        self.access_token=r.headers['X-Access-Token']
                        self.refresh_token=r.headers['X-Refresh-Token']
                        return True
                except:
                        return False


        def balance(self):
                try:
                        r=requests.get(self.url+'/account/list', headers={'authorization':self.access_token})
                        return r.json()['results'][0]['buying_power']['amount']
                except:
                        return False
                
        def tick_id(self, ticker, country=None):#country is US or CA
                try:
                        r=requests.get(self.url+'/securities', params={'query':ticker}, headers={'authorization':self.access_token})
                        for i in range(0,r.json()['total_count']):
                                if (r.json()['results'][i]['stock']['symbol']==ticker and r.json()['results'][i]['stock']['country_of_issue']==country) or country==None:
                                        return r.json()['results'][0]['id']
                        return False
                except:
                        return False

        def tick_info(self, ticker):
                try:
                        r=requests.get(self.url+'/securities', params={'query':ticker}, headers={'authorization':self.access_token})
                        return r.json()
                except:
                        return False

        def limit_buy(self, tick_id, price, quantity):
                try:
                        r=requests.post(self.url+'/orders', json={'security_id':tick_id, 'limit_price':price, 'quantity': quantity, 'order_type': 'buy_quantity',  'order_sub_type': 'limit', 'time_in_force': 'day'}, headers={'authorization':self.access_token})
                        return r.json()['order_id']

                except:
                        return False
                
        def limit_sell(self, tick_id, price, quantity):
                try:
                        r=requests.post(self.url+'/orders', json={'security_id':tick_id, 'limit_price':price, 'quantity': quantity, 'order_type': 'sell_quantity',  'order_sub_type': 'limit', 'time_in_force': 'day'}, headers={'authorization':self.access_token})
                        return r.json()['order_id']

                except:
                        return False
                
        def market_buy(self, tick_id, quantity, price=1):
                try:
                        r=requests.post(self.url+'/orders', json={'security_id':tick_id, 'limit_price': price, 'quantity': quantity, 'order_type': 'buy_quantity',  'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization':self.access_token})
                        return r.json()
                except:
                        return False

        def market_sell(self, tick_id, quantity, price=1):
                try:
                        r=requests.post(self.url+'/orders', json={'security_id':tick_id, 'limit_price': price, 'quantity': quantity, 'order_type': 'sell_quantity',  'order_sub_type': 'market', 'time_in_force': 'day'}, headers={'authorization':self.access_token})
                        return r.json()
                except:
                        return False


        def cancel_order(self, order_id):
                try:
                        r=requests.delete(self.url+'/orders/'+order_id, headers={'authorization':self.access_token})
                        if r.status_code!=200:
                                return False
                        else:
                                return True
                except:
                        return False

        def fx_buyrate(self, currency='USD'):
                try:
                        r=requests.get(self.url+'/forex', headers={'authorization':self.access_token})
                        return r.json()['USD']['buy_rate']
                except:
                        return False

        def fx_sellrate(self, currency='USD'):
                try:
                        r=requests.get(self.url+'/forex', headers={'authorization':self.access_token})
                        return r.json()[currency]['sell_rate']
                except:
                        return False

def quote(ticker, source, asset_class='stocks'):
        if source.lower()=='nasdaq':
                try:
                        r=requests.get('https://api.nasdaq.com/api/quote/'+ticker+'/info', params={'assetclass':asset_class}, headers = {'User-Agent': 'PostmanRuntime/7.26.2', 'Accept':'*/*'}, timeout=3)
        
                        return float(r.json()['data']['primaryData']['lastSalePrice'].strip('$'))
                except:
                        return False

        elif source.lower()=='tsx' or source.lower()=='tmx':
                try:
                        r=requests.post('https://app-money.tmx.com/graphql', json={"operationName": "getQuoteBySymbol","variables": {"symbol": ticker, "locale": "en"}, "query":"query getQuoteBySymbol($symbol: String, $locale: String) {  getQuoteBySymbol(symbol: $symbol, locale: $locale) {    symbol    name    price}}"}, timeout=3)
                        return float(r.json()['data']['getQuoteBySymbol']['price'])
                except:
                        return False

        elif source.lower()=='yahoo':
                try:
                        r=requests.get('https://query1.finance.yahoo.com/v8/finance/chart/'+ticker, timeout=3)
                        return float(r.json()['chart']['result'][0]['meta']['regularMarketPrice'])
                except:
                        return False

        elif source.lower()=='webull':
                try:
                        r=requests.get('https://quotes-gw.webullfintech.com/api/search/pc/tickers',params={'keyword':ticker,'regionId':6,'pageIndex':1,'pageSize':3})
                        for i in range(len(r.json()['data'])):
                                if ticker==r.json()['data'][i]['symbol']:
                                        ticker_id=r.json()['data'][i]['tickerId']
                                        break
                        r=requests.get('https://quoteapi.webullfintech.com/api/quote/tickerRealTimes/v5/'+str(ticker_id), params={'includeSecu':1,'includeQuote':1,'more':1})
                        return r.json()
                except:
                        return False
        else:
                return False





#below is an example to make it work input desired parameters

#create a wealthsimple class, replace email with your email and password with your password		
#ws=wealthsimple('email', 'password')



#create a limit buy order for appl

#first get the security id for AAPL by calling tick_id with AAPL as its parameter e.g ws.tick_id(ticker) where ticker is the stock symbol or ticker
#ticker_id=ws.tick_id('AAPL')

#then enter the ticker_id along with the disired limit price and quantity e.g. ws.limit_buy(ticker_id, limit_price, quantity) where ticker_id is the
#variable we just got from the first step limit_price is the highest price you are willing to pay and quantity is the number of shares you want to purchase
#in this case we are buying 1 share of AAPL at the limit price of 300
#order_id=ws.limit_buy(ticker_id, 300, 1)

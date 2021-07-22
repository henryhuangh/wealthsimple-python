# wealthsimple-python

## Introduction
The objective of this project is to provide a library of trading functions that enable complete automation with python code. The goal is to have full functionality as the wealthsimple app. Included is the authy module which allow automatic logins even with 2FA enabled.

## Requirements
To use this module, requests must be installed. This can be downloaded with the line 'python -m pip install requests' in windows command prompt or just 'pip install requests' on linux.

## Features
- Basic buy and sell functionality (Stop Limit, Limit, Market, Good till Cancel, Good for Day)
- Built-in real time quotes support from TMX, NASDAQ and Yahoo
- Balance retreival

## Documentation

### Setup
Make sure the wealthsimple and authy module is in PATH.
Import the module wealthsimple

```python 
from weathsimple import wealthsimple
import authy
```

### Login
In order to login, the username and password must be entered into a wealthsimple object.

```python
ws=wealthsimple('email', 'password')
```

If 2FA is enabled, additional steps must be taken for the login process. Go to Two-step verification settings in the wealthsimple app and switch to method to 'Use a dedicated app'. Take note of the code and it can be used to generate a totp_token.

```python
ws=wealthsimple('email', 'password', MFA=authy.get_totp_token('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX='))
```


### Trading

To place a trade, ensure that there is enough funds avaliable, purchasing power can be retrieved by:

```python
ws.balance(account_id)
```

The account id can be retrieved by calling

```python
ws.accounts()
```

This will list out all the accounts associated with the login

#### Orders

Type | Syntax | Required
--- | --- | ---
Market Buy | ws.market_buy(tick_id, quantity, price, account_id) | tick_id, quantity
Market Sell | ws.market_sell(tick_id, quantity, price, account_id) | tick_id, quantity
Limit Buy | ws.limit_buy(tick_id, quantity, price, account_id) | tick_id, quantity, price
Limit Sell | ws.limit_sell(tick_id, quantity, price, account_id) | tick_id, quantity, price
Stop Limit Sell | ws.stop_limit_sell(tick_id, quantity, price, stop_price, account_id) | tick_id, quantity, price, stop_price
Stop Limit Buy | ws.stop_limit_buy(tick_id, quantity, price, stop_price, account_id) | tick_id, quantity, price, stop_price

##### Param Definitions
tick_id: tick_id is a unique idenitifier for a particular stock, this parameter can be retrieved by calling the `tick_id` method
Example: 
```python
ticker_id=ws.tick_id('AAPL', 'NASDAQ')
```
This will retrieve the the tick_id for AAPL INC. listed on NASDAQ

quantity: This refers to the quantity of stock to purchase or sell

price: This refers to the desired price to purchase or sell in a limit order. This price is usually better than market prices

stop_price: This is the price which will activate the order in a stop order. For a stop limit sell, the stop price is above the market value.


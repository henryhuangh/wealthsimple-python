# wealthsimple-python

## Table of Contents

- [wealthsimple-python](#wealthsimple-python)
  * [Introduction](#introduction)
  * [Dependencies](#dependencies)
  * [Features](#features)
  * [Documentation](#documentation)
    + [Setup](#setup)
    + [Authentication](#authentication)
      - [Entering MFA](#entering-mfa)
      - [Storing MFA code](#storing-mfa-code)
      - [Refreshing Session](#refreshing-session)
    + [Accounts](#accounts)
    + [Orders](#orders)
      - [Param Definitions](#param-definitions)
      - [Example](#example)
  * [Real-Time Quotes](#real-time-quotes)
    + [Sources](#sources)
    + [Specifications](#specifications)
    + [Example](#example-1)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>

## Introduction
The objective of this project is to provide a python library of trading functions for WealthSimple Trade. The goal is to have basic functionality to enable full trading automation. Included is the authy module which allows automatic logins even with 2FA enabled. Also included is a small library to obtain real-time quotes.

## Dependencies
The requests is required to be installed. This can be obtained with `python -m pip install requests` in windows command prompt or just `pip install requests` on linux.

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

### Authentication
In order to login, the username and password must be entered into a wealthsimple object.

```python
ws=wealthsimple('email', 'password')
```

If 2FA is enabled, additional steps must be taken for the login process. There are two methods that can be used to get around this.

#### Entering MFA

Entering the MFA for login is a simple process:

```python
ws=wealthsimple('email', 'password')
#login with the email and password credentials normally
#A MFA code will be sent to your device

MFA_token=input('MFA key:')
#enter the MFA token

ws=wealthsimple('email', 'password', MFA=MFA_token)
#the MFA token is included as a parameter for the ws object initiation
```

#### Storing MFA code

The 2FA key can be stored for auto-login. A secure storage method should be used but will not be discussed in this documentation.

To obtain the MFA key in the wealthsimple app, go to: settings > Two-step verification > Change method > Use a dedicated app. 

Take note of the code, the authy module can be used to generate the unique 6 digit token used for login.

```python
MFA_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX='

MFA_token=authy.get_totp_token(MFA_key)

ws=wealthsimple('email', 'password', MFA=MFA_token)

```
**Note: add '=' to the MFA_key string to meet length requirements**

#### Refreshing Session

After authenticating, the session will automatically log out after a set amount of time. To prevent this from happening, refresh the session with:

```python
ws.refresh()
```


### Accounts

To get the accounts associated with the login, call:

```python
accounts=ws.accounts()
```

The `accounts` variable will be an JSON array containing information for each account opened in wealthsimple. This is useful if multiple accounts were opened (e.g. Personal, TFSA, RRSP).

Some convenient keys where `i` is the index of the account:
```python
account_id=accounts[i]['id']
#the account id is used to identify the account

account_type=accounts[i]['account_type']
#this is where the account types: Personal, TFSA, RRSP will be returned

balance=accounts[i]['buying_power']['amount']
#the amount in CAD that is currently avaliable for trade

positions=accs[i]['position_quantities']
#an array containing a list of positions (represented in tick_id) you currently hold
```

To get the balance in CAD as a function use:

```python
ws.balance(account_id)
```



### Orders

Type | Syntax | Required
--- | --- | ---
Market Buy | ws.market_buy(tick_id, quantity, price, account_id) | tick_id, quantity
Market Sell | ws.market_sell(tick_id, quantity, price, account_id) | tick_id, quantity
Limit Buy | ws.limit_buy(tick_id, quantity, price, account_id) | tick_id, quantity, price
Limit Sell | ws.limit_sell(tick_id, quantity, price, account_id) | tick_id, quantity, price
Stop Limit Sell | ws.stop_limit_sell(tick_id, quantity, price, stop_price, account_id) | tick_id, quantity, price, stop_price
Stop Limit Buy | ws.stop_limit_buy(tick_id, quantity, price, stop_price, account_id) | tick_id, quantity, price, stop_price

#### Param Definitions
**tick_id:** tick_id is a unique idenitifier for a particular stock, this parameter can be retrieved by calling the `tick_id` method
Example: 
```python
ticker_id=ws.tick_id('AAPL', 'NASDAQ')
```
This will retrieve the the tick_id for AAPL INC. listed on NASDAQ

**quantity:** This refers to the quantity of stock to purchase or sell

**price:** This refers to the desired price to purchase or sell in a limit order. This price is usually better than market prices

**stop_price:** This is the price which will activate the order in a stop order. For a stop limit sell, the stop price is above the market value.

**account_id:** This parameter is optional for all order methods, by default it will place orders in the main account. If a custom account is required, simply add the account_id parameter retreived from the `accounts` method

#### Example

This example buys 10 Apple shares at 140 USD each:

```python
tick_id=ws.tick_id('AAPL', 'NASDAQ')

ws.limit_buy(tick_id, 10, 140)
```

## Real-Time Quotes

The wealthsimple module also provides a means to obtain real-time quotes. This can be used to send orders with up-to-date information. It can also be used to conduct technical analysis. For the time being, only the market value can obtained with the quote function.

### Sources

There are four supported sources:

- NASDAQ
- TMX
- YAHOO
- WEBULL

### Specifications

Since the same ticker may refer to different companies in different exchanges, these differences must be accounted for. When obtaining quotes on TMX for a US stock for instance ':US' must be added (e.g. 'AAPL' becomes 'AAPL:US')

Source | Canadian | US
--- | --- | ---
NASDAQ | unsupported | ticker
TMX | ticker | ticker + ':US'
YAHOO | ticker + '.TO' | ticker
WEBULL | unsupported | ticker

### Example

Obtain the current market value of Apple Inc. and store it in the variable `price`

```python
price=quote('AAPL', source='NASDAQ')
```
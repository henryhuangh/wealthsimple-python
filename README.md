# wealthsimple-python

<div align="center">

**Unofficial Python client for the Wealthsimple Trade platform**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Examples](#examples)

</div>

---

## ⚠️ Important Disclaimer

**This is an unofficial API client** for Wealthsimple Trade. It is not affiliated with, officially maintained by, or endorsed by Wealthsimple. Use at your own risk.

- ⚠️ No warranty or guarantee is provided
- 🧪 Always test with small amounts first
- 🔒 Keep your credentials secure
- 📝 API may change without notice

---

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Documentation](#documentation)
  - [Security Search & Quotes](#security-search--quotes)
  - [Account Management](#account-management)
  - [Stock Trading](#stock-trading)
  - [Options Trading](#options-trading)
  - [Activity & History](#activity--history)
- [Interactive Trading Tool](#interactive-trading-tool)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)
- [Legacy API](#legacy-api)

---

## ✨ Features

### 🔐 Authentication

- ✅ OAuth v2 authentication with automatic token refresh
- ✅ Support for 2FA/OTP
- ✅ Environment variable support for secure credential storage
- ✅ Token expiry management and auto-refresh

### 📊 Market Data

- ✅ Security search by ticker symbol or company name
- ✅ Real-time quotes with bid/ask spreads
- ✅ Detailed security information (fundamentals, market status)
- ✅ Support for stocks across multiple exchanges (NASDAQ, NYSE, TSX, etc.)

### 💼 Account Management

- ✅ Retrieve all accounts (Personal, TFSA, RRSP, etc.)
- ✅ Account balances and buying power
- ✅ Current positions with unrealized P/L
  - ✅ Activity feed and order history

### 📈 Stock Trading

- ✅ Market orders (buy/sell)
- ✅ Limit orders (buy/sell)
- ✅ Stop-limit orders (buy/sell)
- ✅ Good-Till-Cancelled (GTC) and Day orders
- ✅ Custom order creation

### 📉 Options Trading

- ✅ Full option chain retrieval
- ✅ Available expiry dates
- ✅ Option greeks (delta, gamma, theta, vega, rho)
- ✅ Implied volatility
- ✅ Buy to open/close
- ✅ Sell to open/close (writing covered calls)
- ✅ Transaction fee calculation

### 🎮 Interactive Trading Tool

- ✅ Command-line interface for easy trading
- ✅ Interactive security search
- ✅ Real-time quote viewing
- ✅ Order confirmation before execution
- ✅ Support for both stocks and options

---

## 📦 Installation

### Requirements

- Python 3.7 or higher
- `requests` library

### Install Dependencies

```bash
pip install requests
```

### Download the Library

Clone or download the repository:

```bash
git clone https://github.com/yourusername/wealthsimple-python.git
cd wealthsimple-python
```

Ensure `wealthsimple_v2.py` is in your project directory or Python path.

---

## 🚀 Quick Start

### Basic Usage

```python
from wealthsimple_v2 import WealthsimpleV2

# Initialize and authenticate
ws = WealthsimpleV2(
    username='your@email.com',
    password='yourpassword',
    otp='123456'  # Optional, only if 2FA is enabled
)

# Search for a security
results = ws.search_securities('AAPL')
security_id = ws.get_ticker_id('AAPL', 'NASDAQ')

# Get a real-time quote
quote = ws.get_security_quote(security_id)
print(f"AAPL: ${quote['price']} (Bid: ${quote['bid']}, Ask: ${quote['ask']})")

# Get your accounts
accounts = ws.get_accounts()
for account in accounts:
    print(f"{account['nickname']}: {account['id']}")

# Place a limit buy order
account_id = accounts[0]['id']
order = ws.limit_buy(
    account_id=account_id,
    security_id=security_id,
    quantity=1,
    limit_price=150.00
)
print(f"Order placed: {order['orderId']}")
```

### Using Environment Variables

For better security, store credentials in environment variables:

```bash
export WS_USERNAME='your@email.com'
export WS_PASSWORD='yourpassword'
export WS_OTP='123456'  # Optional
```

Then initialize without parameters:

```python
from wealthsimple_v2 import WealthsimpleV2

# Credentials are read from environment variables
ws = WealthsimpleV2()
```

---

## 🔐 Authentication

### Basic Authentication

```python
from wealthsimple_v2 import WealthsimpleV2

ws = WealthsimpleV2(username='your@email.com', password='yourpassword')
```

### With 2FA/OTP

If you have two-factor authentication enabled:

```python
ws = WealthsimpleV2(
    username='your@email.com',
    password='yourpassword',
    otp='123456'  # Your 6-digit 2FA code
)
```

### Automatic Token Refresh

The client automatically refreshes expired access tokens:

```python
# No need to manually refresh - it happens automatically
accounts = ws.get_accounts()  # Token is auto-refreshed if expired
```

### Manual Token Refresh

If needed, you can manually refresh:

```python
success = ws.refresh_access_token()
if success:
    print("Token refreshed successfully")
```

---

## 📚 Documentation

### Security Search & Quotes

#### Search for Securities

```python
# Search by ticker or company name
results = ws.search_securities('AAPL')

# Search with specific security groups
results = ws.search_securities('TSLA', security_group_ids=['stock', 'adr'])

# Display results
for security in results:
    print(f"{security['stock']['symbol']} - {security['stock']['name']}")
```

#### Get Ticker ID

```python
# Get security ID by ticker symbol
security_id = ws.get_ticker_id('AAPL', 'NASDAQ')
security_id = ws.get_ticker_id('SHOP', 'TSX')

# The ID is required for trading and quotes
print(f"Security ID: {security_id}")
```

#### Get Real-Time Quote

```python
# Get quote for a security
quote = ws.get_security_quote(security_id)

print(f"Price: ${quote['price']}")
print(f"Bid: ${quote['bid']} x {quote['bidSize']}")
print(f"Ask: ${quote['ask']} x {quote['askSize']}")
print(f"High: ${quote['high']} | Low: ${quote['low']}")
print(f"Volume: {quote['volume']}")
print(f"Market Status: {quote['quoteStatus']}")
```

#### Get Detailed Security Information

```python
# Get comprehensive security details
security = ws.get_security(security_id)

# Access various data points
stock = security['stock']
print(f"Symbol: {stock['symbol']}")
print(f"Name: {stock['name']}")
print(f"Exchange: {stock['primaryExchange']}")
print(f"Currency: {stock['currency']}")
print(f"52-Week High: ${stock['high52Week']}")
print(f"52-Week Low: ${stock['low52Week']}")

# Fundamentals
fundamentals = stock.get('fundamentals', {})
print(f"P/E Ratio: {fundamentals.get('peRatio')}")
print(f"Market Cap: ${fundamentals.get('marketCap')}")
print(f"Dividend Yield: {fundamentals.get('dividendYield')}%")
```

### Account Management

#### Get All Accounts

```python
# Retrieve all accounts
accounts = ws.get_accounts()

for account in accounts:
    print(f"Nickname: {account['nickname']}")
    print(f"ID: {account['id']}")
    print(f"Type: {account['accountType']}")
    print(f"Status: {account['status']}")
    print("---")
```

#### Get Account Financials

```python
# Get detailed financial information
account_ids = [acc['id'] for acc in accounts]
financials = ws.get_account_financials(account_ids)

for financial in financials:
    print(f"Account: {financial['accountId']}")
    print(f"Net Worth: ${financial['netWorth']['amount']} {financial['netWorth']['currency']}")
    print(f"Buying Power: ${financial['buyingPower']['amount']}")
    print(f"Cash Balance: ${financial['currentCashBalance']['amount']}")
    print("---")
```

#### Get Current Positions

```python
# Get all positions across all accounts
positions = ws.get_positions()

for position in positions:
    security = position['security']
    symbol = security['stock']['symbol']
    quantity = position['quantity']

    # Market value
    market_value = position['totalValue']['amount']

    # P/L information
    pnl = position.get('profitLossAmount', {}).get('amount', 0)
    pnl_pct = position.get('profitLossPercentage', 0)

    print(f"{symbol}: {quantity} shares")
    print(f"  Value: ${market_value}")
    print(f"  P/L: ${pnl} ({pnl_pct:.2f}%)")
```

#### Filter Positions by Account

```python
# Get positions for specific accounts
account_ids = [accounts[0]['id']]  # Only first account
positions = ws.get_positions(account_ids=account_ids)
```

### Stock Trading

#### Market Orders

```python
# Market buy
order = ws.market_buy(
    account_id=account_id,
    security_id=security_id,
    quantity=10
)

# Market sell
order = ws.market_sell(
    account_id=account_id,
    security_id=security_id,
    quantity=10
)

print(f"Order ID: {order['orderId']}")
print(f"Status: {order['status']}")
```

#### Limit Orders

```python
# Limit buy - buy at or below limit price
order = ws.limit_buy(
    account_id=account_id,
    security_id=security_id,
    quantity=5,
    limit_price=150.00
)

# Limit sell - sell at or above limit price
order = ws.limit_sell(
    account_id=account_id,
    security_id=security_id,
    quantity=5,
    limit_price=160.00
)
```

#### Stop-Limit Orders

```python
# Stop-limit buy
# When price rises to $155, place limit buy at $156
order = ws.stop_limit_buy(
    account_id=account_id,
    security_id=security_id,
    quantity=5,
    limit_price=156.00,
    stop_price=155.00
)

# Stop-limit sell (stop loss)
# When price drops to $145, place limit sell at $144
order = ws.stop_limit_sell(
    account_id=account_id,
    security_id=security_id,
    quantity=5,
    limit_price=144.00,
    stop_price=145.00
)
```

#### Custom Order Creation

```python
# Create a custom order with all parameters
order = ws.create_order(
    account_id=account_id,
    security_id=security_id,
    quantity=10,
    limit_price=150.00,
    order_type='BUY_QUANTITY',
    order_sub_type='LIMIT',
    time_in_force='GTC',  # Good-Till-Cancelled
    stop_price=None
)
```

### Options Trading

#### Get Option Expiry Dates

```python
# Get available expiry dates for an underlying security
expiry_dates = ws.get_option_expiry_dates(security_id)

print(f"Available expiry dates: {len(expiry_dates)}")
for date in expiry_dates[:5]:  # Show first 5
    print(f"  {date}")
```

#### Get Option Chain

```python
# Get call options for a specific expiry
options = ws.get_option_chain(
    security_id=security_id,
    expiry_date=expiry_dates[0],
    option_type='CALL'
)

# Display option chain
for option in options:
    symbol = option['optionSymbol']
    strike = option['strikePrice']['amount']

    # Greeks
    greeks = option.get('greeks', {})
    delta = greeks.get('delta')
    gamma = greeks.get('gamma')
    theta = greeks.get('theta')
    vega = greeks.get('vega')
    iv = greeks.get('impliedVolatility')

    # Quote
    quote = option.get('quote', {})
    bid = quote.get('bid')
    ask = quote.get('ask')

    print(f"{symbol}")
    print(f"  Strike: ${strike}")
    print(f"  Bid: ${bid} | Ask: ${ask}")
    print(f"  Delta: {delta:.4f} | IV: {iv:.2%}")
    print("---")
```

#### Get Put Options

```python
# Get put options
puts = ws.get_option_chain(
    security_id=security_id,
    expiry_date=expiry_dates[0],
    option_type='PUT'
)
```

#### Filter Options by Strike Price

```python
# Get options near a specific strike price
options = ws.get_option_chain(
    security_id=security_id,
    expiry_date=expiry_dates[0],
    option_type='CALL',
    min_strike=145.00,
    max_strike=155.00
)
```

#### Buy Options (Long Position)

```python
# Buy to open a call option
order = ws.buy_option(
    account_id=account_id,
    option_id=options[0]['id'],
    quantity=1,  # 1 contract = 100 shares
    limit_price=2.50  # Premium per share ($250 total)
)

# Buy to close a short position
order = ws.buy_option(
    account_id=account_id,
    option_id=option_id,
    quantity=1,
    limit_price=2.50,
    order_sub_type='LIMIT'
)
```

#### Sell Options (Short Position or Close Long)

```python
# Sell to open (write a covered call)
order = ws.sell_option(
    account_id=account_id,
    option_id=option_id,
    quantity=1,
    limit_price=2.50
)

# Sell to close a long position
order = ws.sell_option(
    account_id=account_id,
    option_id=option_id,
    quantity=1,
    limit_price=2.50,
    order_sub_type='LIMIT'
)
```

#### Calculate Option Fees

```python
# Calculate transaction fees for buying options
fees = ws.get_option_transaction_fees(
    side='BUY',
    premium=2.50,  # Price per share
    quantity=1,    # Number of contracts
    currency='USD'
)

print(f"Premium: ${fees['premium']['amount']}")
print(f"Commission: ${fees['commission']['amount']}")
print(f"Total Cost: ${fees['totalCost']['amount']}")
```

### Activity & History

#### Get Activity Feed

```python
# Get recent activities
activities = ws.get_activities(limit=50)

for activity in activities:
    activity_type = activity['type']
    symbol = activity.get('assetSymbol', 'N/A')
    date = activity.get('occurredAt')

    print(f"{date}: {activity_type} - {symbol}")
```

#### Filter Activities by Type

```python
# Get only buy/sell activities
activities = ws.get_activities(
    types=['buy', 'sell'],
    limit=20
)
```

#### Filter Activities by Account

```python
# Get activities for specific account
activities = ws.get_activities(
    account_ids=[account_id],
    limit=50
)
```

---

## 🎮 Interactive Trading Tool

An interactive command-line interface is included for easy testing and trading:

```bash
python interactive_trade.py
```

### Features

- 🔐 **Interactive Authentication**: Enter credentials securely
- 🔍 **Security Search**: Search by ticker or browse popular stocks
- 📊 **Real-Time Quotes**: View detailed security information
- 📈 **Stock Trading**: Place market and limit orders
- 📉 **Options Trading**: Browse option chains and trade options
- 💼 **Account Selection**: Choose from your trading accounts
- ✅ **Order Confirmation**: Review before executing

### Usage

```bash
# Set environment variables (optional)
export WS_USERNAME='your@email.com'
export WS_PASSWORD='yourpassword'
export WS_OTP='123456'

# Run the interactive tool
python interactive_trade.py
```

The script will guide you through:

1. **Authentication** - Login with your credentials
2. **Security Search** - Find stocks or options
3. **Quote Display** - View real-time data
4. **Account Selection** - Choose your trading account
5. **Trade Type** - Select stocks or options
6. **Order Placement** - Execute with confirmation

---

## 📖 Examples

### Example 1: Portfolio Summary

```python
from wealthsimple_v2 import WealthsimpleV2

ws = WealthsimpleV2()

# Get all positions
positions = ws.get_positions()

total_value = 0
print("Your Portfolio:")
print("=" * 60)

for position in positions:
    symbol = position['security']['stock']['symbol']
    quantity = position['quantity']
    value = position['totalValue']['amount']
    pnl = position.get('profitLossAmount', {}).get('amount', 0)

    total_value += value

    print(f"{symbol:6s} | Qty: {quantity:>6} | Value: ${value:>10.2f} | P/L: ${pnl:>8.2f}")

print("=" * 60)
print(f"Total Portfolio Value: ${total_value:,.2f}")
```

### Example 2: Buy Stock with Quote Check

```python
from wealthsimple_v2 import WealthsimpleV2

ws = WealthsimpleV2()

# Define trade parameters
ticker = 'AAPL'
exchange = 'NASDAQ'
quantity = 10

# Get security ID and current quote
security_id = ws.get_ticker_id(ticker, exchange)
quote = ws.get_security_quote(security_id)

current_price = quote['price']
print(f"Current price of {ticker}: ${current_price}")

# Calculate limit price (1% below current)
limit_price = round(current_price * 0.99, 2)
print(f"Placing limit buy at ${limit_price}")

# Get account
accounts = ws.get_accounts()
account_id = accounts[0]['id']

# Place order
order = ws.limit_buy(account_id, security_id, quantity, limit_price)
print(f"Order placed: {order['orderId']}")
print(f"Status: {order['status']}")
```

### Example 3: Sell Covered Call

```python
from wealthsimple_v2 import WealthsimpleV2

ws = WealthsimpleV2()

# Get security (stock you own)
ticker = 'AAPL'
security_id = ws.get_ticker_id(ticker, 'NASDAQ')

# Get option expiry dates
expiry_dates = ws.get_option_expiry_dates(security_id)
nearest_expiry = expiry_dates[0]

print(f"Expiry date: {nearest_expiry}")

# Get call options
calls = ws.get_option_chain(security_id, nearest_expiry, 'CALL')

# Find out-of-the-money call (strike > current price)
quote = ws.get_security_quote(security_id)
current_price = quote['price']

otm_calls = [c for c in calls if c['strikePrice']['amount'] > current_price]

if otm_calls:
    selected_call = otm_calls[0]  # Nearest OTM strike

    strike = selected_call['strikePrice']['amount']
    option_id = selected_call['id']

    # Get bid price
    bid = selected_call['quote']['bid']

    print(f"Selling covered call at ${strike} strike for ${bid} premium")

    # Sell to open
    account_id = ws.get_accounts()[0]['id']
    order = ws.sell_option(account_id, option_id, quantity=1, limit_price=bid)

    print(f"Order placed: {order['orderId']}")
```

### Example 4: Monitor Multiple Positions

```python
from wealthsimple_v2 import WealthsimpleV2
import time

ws = WealthsimpleV2()

def display_portfolio():
    positions = ws.get_positions()
    print("\n" + "=" * 80)
    print(f"{'Symbol':<10} {'Qty':<8} {'Value':<12} {'P/L $':<12} {'P/L %':<10}")
    print("=" * 80)

    for pos in positions:
        symbol = pos['security']['stock']['symbol']
        qty = pos['quantity']
        value = pos['totalValue']['amount']
        pnl_amt = pos.get('profitLossAmount', {}).get('amount', 0)
        pnl_pct = pos.get('profitLossPercentage', 0)

        print(f"{symbol:<10} {qty:<8} ${value:<11.2f} ${pnl_amt:<11.2f} {pnl_pct:>7.2f}%")

# Display portfolio every 60 seconds
while True:
    display_portfolio()
    time.sleep(60)
```

---

## 🔧 Advanced Usage

### Custom GraphQL Queries

```python
# Execute custom GraphQL queries
query = """
    query CustomQuery($securityId: ID!) {
        security(id: $securityId) {
            id
            stock {
                symbol
                name
                currency
            }
        }
    }
"""

variables = {"securityId": security_id}
result = ws.graphql_query("CustomQuery", query, variables)
```

### Error Handling

```python
from wealthsimple_v2 import WealthsimpleV2

try:
    ws = WealthsimpleV2(username='user@email.com', password='wrong_password')
except Exception as e:
    print(f"Authentication failed: {e}")

try:
    security_id = ws.get_ticker_id('INVALID_TICKER', 'NASDAQ')
    if not security_id:
        print("Security not found")
except Exception as e:
    print(f"Error: {e}")
```

### Token Management

```python
# Save tokens for reuse
ws = WealthsimpleV2(username='your@email.com', password='yourpassword')
access_token = ws.access_token
refresh_token = ws.refresh_token

# Later, reuse tokens
ws = WealthsimpleV2(access_token=access_token, refresh_token=refresh_token)
```

---

## 📋 API Reference

### Class: `WealthsimpleV2`

#### Initialization

```python
ws = WealthsimpleV2(
    username=None,
    password=None,
    otp=None,
    client_id=None,
    access_token=None,
    refresh_token=None
)
```

#### Authentication Methods

| Method                                       | Description                         |
| -------------------------------------------- | ----------------------------------- |
| `authenticate(username, password, otp=None)` | Authenticate with username/password |
| `refresh_access_token()`                     | Manually refresh the access token   |

#### Security Methods

| Method                                              | Description                             |
| --------------------------------------------------- | --------------------------------------- |
| `search_securities(query, security_group_ids=None)` | Search for securities by ticker or name |
| `get_security(security_id, currency=None)`          | Get detailed security information       |
| `get_security_quote(security_id, currency=None)`    | Get real-time quote                     |
| `get_ticker_id(ticker, exchange=None)`              | Get security ID from ticker symbol      |

#### Account Methods

| Method                                                                   | Description                   |
| ------------------------------------------------------------------------ | ----------------------------- |
| `get_accounts(identity_id=None)`                                         | Get all accounts              |
| `get_account_financials(account_ids, currency='CAD')`                    | Get account balances          |
| `get_positions(identity_id=None, account_ids=None, security_types=None)` | Get current positions         |
| `get_activities(account_ids=None, types=None, limit=50)`                 | Get activity feed             |
| `get_identity(identity_id=None)`                                         | Get user identity information |

#### Stock Trading Methods

| Method                                                                        | Description             |
| ----------------------------------------------------------------------------- | ----------------------- |
| `market_buy(account_id, security_id, quantity)`                               | Place market buy order  |
| `market_sell(account_id, security_id, quantity)`                              | Place market sell order |
| `limit_buy(account_id, security_id, quantity, limit_price)`                   | Place limit buy order   |
| `limit_sell(account_id, security_id, quantity, limit_price)`                  | Place limit sell order  |
| `stop_limit_buy(account_id, security_id, quantity, limit_price, stop_price)`  | Place stop-limit buy    |
| `stop_limit_sell(account_id, security_id, quantity, limit_price, stop_price)` | Place stop-limit sell   |
| `create_order(account_id, security_id, quantity, ...)`                        | Create custom order     |

#### Options Trading Methods

| Method                                                               | Description                |
| -------------------------------------------------------------------- | -------------------------- |
| `get_option_chain(security_id, expiry_date, option_type, ...)`       | Get option chain           |
| `get_option_expiry_dates(security_id, min_date=None, max_date=None)` | Get available expiry dates |
| `get_option_transaction_fees(side, premium, quantity, currency)`     | Calculate option fees      |
| `buy_option(account_id, option_id, quantity, limit_price, ...)`      | Buy option contract        |
| `sell_option(account_id, option_id, quantity, limit_price, ...)`     | Sell option contract       |

#### Utility Methods

| Method                                                 | Description                  |
| ------------------------------------------------------ | ---------------------------- |
| `graphql_query(operation_name, query, variables=None)` | Execute custom GraphQL query |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Areas for Improvement

- Add unit tests
- Implement rate limiting
- Add WebSocket support for real-time streaming
- Support for multi-leg option strategies
- Enhanced error handling and retry logic
- CLI improvements

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔗 Resources

- **API Documentation**: See `API_V2_SUMMARY.md` for detailed API information
- **Examples**: See `EXAMPLES_V2.md` for comprehensive usage examples
- **Wealthsimple**: [https://www.wealthsimple.com/](https://www.wealthsimple.com/)

---

## 📞 Support

For questions, issues, or feature requests, please open an issue on GitHub.

---

## ⚖️ Legal

This project is not affiliated with, officially maintained by, or endorsed by Wealthsimple. All trademarks are the property of their respective owners.

**USE AT YOUR OWN RISK.** This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses or damages resulting from the use of this software.

Always verify orders before executing and start with small amounts when testing.

---

## 📚 Legacy API

The original REST API (`archive/wealthsimple.py`) is still available but uses deprecated Trade API endpoints. It is strongly recommended to migrate to the v2 GraphQL API for new projects.

### Legacy API Quick Reference

The legacy API provided basic functionality:

```python
# Legacy API (deprecated)
from archive.wealthsimple import wealthsimple

ws = wealthsimple('email', 'password', MFA='123456')
accounts = ws.accounts()
tick_id = ws.tick_id('AAPL', 'NASDAQ')
ws.limit_buy(tick_id, 10, 140)
```

For legacy API documentation, see `archive/README.md`.

---

<div align="center">

**Made with ❤️ by the community**

⭐ Star this repo if you find it helpful!

</div>

# Wealthsimple API v2 - Usage Examples

Complete usage examples for `wealthsimple_v2.py`. For full detailed examples, see the comprehensive version in the repository.

## Quick Start

### Authentication

```python
from wealthsimple_v2 import WealthsimpleV2

ws = WealthsimpleV2(username='your@email.com', password='yourpassword', otp='123456')
```

### Search for Securities

```python
results = ws.search_securities("AAPL")
security_id = ws.get_ticker_id('AAPL', 'NASDAQ')
```

### Get Quote

```python
quote = ws.get_security_quote(security_id)
print(f"Price: ${quote['price']}")
```

### Get Accounts

```python
accounts = ws.get_accounts()
for acc in accounts:
    print(f"{acc['nickname']}: {acc['id']}")
```

### Place Orders

```python
account_id = accounts[0]['id']

# Limit buy
order = ws.limit_buy(account_id, security_id, quantity=1, limit_price=150.00)

# Market buy
order = ws.market_buy(account_id, security_id, quantity=1)
```

### Options Trading

```python
# Get option chain
expiry_dates = ws.get_option_expiry_dates(security_id)
options = ws.get_option_chain(security_id, expiry_dates[0], 'CALL')

# Buy option
order = ws.buy_option(account_id, options[0]['id'], quantity=1, limit_price=2.50)
```

### Get Positions

```python
positions = ws.get_positions()
for pos in positions:
    symbol = pos['security']['stock']['symbol']
    quantity = pos['quantity']
    value = pos['totalValue']['amount']
    print(f"{symbol}: {quantity} shares @ ${value}")
```

### Activity Feed

```python
activities = ws.get_activities(limit=50)
for activity in activities:
    print(f"{activity['type']}: {activity.get('assetSymbol', 'N/A')}")
```

## Key Features

- **Authentication**: OAuth v2 with 2FA support
- **Trading**: Market, limit, and stop-limit orders
- **Options**: Full option chain support with greeks
- **Accounts**: Get balances, positions, and activities
- **Search**: Find securities by ticker or name
- **Quotes**: Real-time quotes with bid/ask spreads

For more detailed examples, see the full documentation in the repository.

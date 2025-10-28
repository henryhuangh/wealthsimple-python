# Wealthsimple API v2 - Implementation Summary

## Created Files

### 1. wealthsimple_v2.py (40KB)
The main API client implementation with the following features:

**Authentication:**
- OAuth v2 authentication with automatic token refresh
- Support for 2FA/OTP
- Environment variable support
- Token expiry management

**Core Functionality:**
- GraphQL query execution
- Automatic authentication checks
- Error handling and retries

**Security & Trading:**
- `search_securities()` - Search by ticker or name
- `get_security()` - Detailed security information
- `get_security_quote()` - Real-time quotes
- `get_ticker_id()` - Convert ticker symbol to security ID
- `market_buy()`, `market_sell()` - Market orders
- `limit_buy()`, `limit_sell()` - Limit orders
- `stop_limit_buy()`, `stop_limit_sell()` - Stop-limit orders
- `create_order()` - Custom order creation

**Options Trading:**
- `get_option_chain()` - Get option contracts for an underlying
- `get_option_expiry_dates()` - Available expiry dates
- `get_option_transaction_fees()` - Calculate option fees
- `buy_option()` - Buy option contracts (long/close short)
- `sell_option()` - Sell option contracts (close long/write)

**Account Management:**
- `get_accounts()` - All accounts for user
- `get_account_financials()` - Account balances and buying power
- `get_positions()` - Current positions with P/L
- `get_activities()` - Activity feed with filtering
- `get_identity()` - User profile information

**Helper Functions:**
- `quote()` - Standalone function for quick quotes from multiple sources

### 2. test_wealthsimple_v2.py (2KB)
Basic test script demonstrating:
- Authentication
- Security search
- Account retrieval
- Error handling

### 3. EXAMPLES_V2.md (14KB)
Comprehensive documentation with examples for:
- All authentication methods
- Security search and quotes
- Account and position management
- Stock trading (all order types)
- Options trading (chains, greeks, strategies)
- Activity feed filtering
- Error handling
- Advanced use cases (trading bots, portfolio analysis, covered calls)

### 4. MIGRATION_GUIDE.md
Complete guide for migrating from legacy API to v2:
- Side-by-side comparison of all methods
- Data structure changes
- Common pitfalls
- Migration examples

### 5. Updated README.md
Added prominent section highlighting v2 API with quick start guide

## Key Features Implemented

### ✅ Authentication
- [x] OAuth v2 password grant
- [x] 2FA/OTP support
- [x] Automatic token refresh
- [x] Token expiry tracking
- [x] Environment variable support

### ✅ Security Information
- [x] Search by ticker/name
- [x] Get ticker ID by symbol
- [x] Detailed security info (fundamentals, quotes, etc.)
- [x] Real-time quotes with bid/ask
- [x] Market status and trading hours

### ✅ Trading
- [x] Market orders (buy/sell)
- [x] Limit orders (buy/sell)
- [x] Stop-limit orders (buy/sell)
- [x] Custom order creation
- [x] Time-in-force support (DAY, GTC)

### ✅ Options Trading
- [x] Option chain retrieval
- [x] Available expiry dates
- [x] Option greeks (delta, gamma, theta, vega, rho, IV)
- [x] Buy to open/close
- [x] Sell to open/close
- [x] Transaction fee calculation
- [x] Strike price filtering
- [x] Call and put options

### ✅ Account Management
- [x] List all accounts
- [x] Account financials (balance, buying power, cash)
- [x] Get positions with unrealized P/L
- [x] Filter positions by security type
- [x] Filter positions by account

### ✅ Activity & History
- [x] Activity feed retrieval
- [x] Filter by account
- [x] Filter by type (buy, sell, deposit, etc.)
- [x] Filter by status (pending, posted, etc.)

### ✅ User Information
- [x] Identity/profile information
- [x] Multi-profile support (tax, trade, invest)

## GraphQL Operations Extracted from HAR

From the HAR file analysis, the following GraphQL operations were identified and implemented:

1. **FetchSecuritySearchResult** - Search for securities
2. **FetchSecurity** - Get detailed security information
3. **FetchSecurityQuoteV2** - Get real-time quotes
4. **FetchOptionChain** - Get option contracts
5. **FetchOptionExpirationDates** - Get available expiry dates
6. **FetchOptionTransactionFees** - Calculate option fees
7. **FetchAllAccounts** - Get user accounts
8. **FetchAccountFinancials** - Get account balances
9. **FetchIdentityPositions** - Get positions
10. **FetchActivityFeedItems** - Get activity feed
11. **FetchIdentity** - Get user identity
12. **SoOrdersOrderCreate** - Create orders (mutation)

## API Endpoint

Base URL: `https://my.wealthsimple.com/graphql`
Auth URL: `https://api.production.wealthsimple.com/v1/oauth/v2/token`

## Required Headers

```python
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {access_token}",
    "User-Agent": "Mozilla/5.0 ...",
    "x-ws-api-version": "12",
    "x-platform-os": "web",
    "x-ws-locale": "en-CA",
    "x-ws-profile": "trade"
}
```

## Usage Quick Reference

```python
from wealthsimple_v2 import WealthsimpleV2

# Initialize
ws = WealthsimpleV2(username='email@example.com', password='pass', otp='123456')

# Search & Trade
security_id = ws.get_ticker_id('AAPL', 'NASDAQ')
accounts = ws.get_accounts()
order = ws.limit_buy(accounts[0]['id'], security_id, 1, 150.00)

# Options
expiry_dates = ws.get_option_expiry_dates(security_id)
options = ws.get_option_chain(security_id, expiry_dates[0], 'CALL')
order = ws.buy_option(accounts[0]['id'], options[0]['id'], 1, 2.50)

# Info
positions = ws.get_positions()
activities = ws.get_activities(limit=50)
```

## Testing

Set environment variables:
```bash
export WS_USERNAME='your@email.com'
export WS_PASSWORD='yourpassword'
export WS_OTP='123456'  # Optional
```

Run test:
```bash
python test_wealthsimple_v2.py
```

## Data Sources

The implementation is based on:
1. HAR file analysis from Wealthsimple web app (Safari network traffic)
2. GraphQL query extraction from 131 captured requests
3. OAuth v2 authentication flow from test_auth.py
4. Data structure analysis from response bodies

## Security Considerations

⚠️ **Important:**
- This is an unofficial API
- No warranty or guarantee
- Use at your own risk
- Always test with small amounts first
- Keep credentials secure
- Never commit API tokens to version control

## Next Steps

1. Test authentication with your credentials
2. Try basic operations (search, get accounts, positions)
3. Test paper trades with small amounts
4. Implement your trading strategy
5. Set up proper error handling and logging
6. Consider rate limiting and retry logic

## Known Limitations

- No websocket support for real-time streaming
- No multi-leg option strategies
- No support for mutual funds/managed portfolios
- Rate limits unknown (use responsibly)
- API may change without notice

## Support

- See EXAMPLES_V2.md for detailed usage examples
- See MIGRATION_GUIDE.md to migrate from legacy API
- Check docstrings in wealthsimple_v2.py for API reference

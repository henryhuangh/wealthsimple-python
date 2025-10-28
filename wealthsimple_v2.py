"""
Wealthsimple API v2 - Unofficial GraphQL-based API Client

This module provides an unofficial Python client for the Wealthsimple platform
using their GraphQL API. It supports authentication, security search, trading,
options trading, and account management.

Based on network traffic analysis from the Wealthsimple web application.

Usage:
    from wealthsimple_v2 import WealthsimpleV2
    
    ws = WealthsimpleV2(username='your@email.com', password='yourpassword')
    
    # Search for a security
    results = ws.search_securities('AAPL')
    
    # Get security details
    security = ws.get_security(security_id)
    
    # Place an order
    order = ws.create_order(
        account_id='tfsa-xxxxx',
        security_id='sec-s-xxxxx',
        quantity=1,
        limit_price=150.00,
        order_type='BUY_QUANTITY'
    )
"""

import requests
import json
import os
import time
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, date


class WealthsimpleV2:
    """
    Unofficial Wealthsimple API v2 Client
    
    This client uses the GraphQL API endpoint at https://my.wealthsimple.com/graphql
    with OAuth v2 authentication.
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, 
                 otp: Optional[str] = None, client_id: Optional[str] = None,
                 access_token: Optional[str] = None, refresh_token: Optional[str] = None):
        """
        Initialize the Wealthsimple API client.
        
        Args:
            username: Your Wealthsimple email/username
            password: Your Wealthsimple password
            otp: Optional OTP/2FA token if 2FA is enabled
            client_id: OAuth client ID (defaults to web client ID)
            access_token: Optional - provide an existing access token to skip authentication
            refresh_token: Optional - provide an existing refresh token
        """
        self.api_url = "https://my.wealthsimple.com/graphql"
        self.auth_url = "https://api.production.wealthsimple.com/v1/oauth/v2/token"
        self.client_id = client_id or "4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa"
        
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = None
        self.identity_id = None
        self.profiles = None
        
        # If credentials provided, authenticate
        if username and password:
            self.authenticate(username, password, otp)
        elif not access_token:
            # Try to get from environment variables
            username = os.getenv('WS_USERNAME')
            password = os.getenv('WS_PASSWORD')
            otp = os.getenv('WS_OTP')
            if username and password:
                self.authenticate(username, password, otp)
    
    def authenticate(self, username: str, password: str, otp: Optional[str] = None) -> Dict:
        """
        Authenticate with Wealthsimple using OAuth v2.
        
        Args:
            username: Your Wealthsimple email/username
            password: Your Wealthsimple password
            otp: Optional OTP/2FA token
            
        Returns:
            Dict containing authentication response
            
        Raises:
            Exception if authentication fails
        """
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "skip_provision": True,
            "scope": "invest.read invest.write trade.read trade.write tax.read tax.write",
            "client_id": self.client_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
        }
        
        if otp:
            headers["x-wealthsimple-otp"] = otp
        
        response = requests.post(self.auth_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in', 1800)
            self.token_expiry = time.time() + expires_in
            
            # Extract identity and profile information
            self.identity_id = data.get('identity_canonical_id')
            self.profiles = data.get('profiles', {})
            
            # If identity_id not in response, try to extract from JWT token
            if not self.identity_id:
                self._fetch_identity_id_from_token()
            
            return data
        else:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    def _fetch_identity_id_from_token(self):
        """
        Extract the identity ID from the JWT access token.
        This is a fallback method if the OAuth response doesn't include identity_canonical_id.
        """
        try:
            if self.access_token:
                # JWT tokens are base64 encoded, format: header.payload.signature
                parts = self.access_token.split('.')
                if len(parts) >= 2:
                    # Add padding if needed for base64 decoding
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    try:
                        decoded = base64.urlsafe_b64decode(payload)
                        token_data = json.loads(decoded)
                        
                        # Look for identity-related fields in the JWT payload
                        # Common fields: sub, identity_canonical_id, identity_id, user_id
                        for key in ['identity_canonical_id', 'identity_id', 'sub', 'user_id']:
                            if key in token_data:
                                value = token_data[key]
                                if isinstance(value, str) and value.startswith('identity-'):
                                    self.identity_id = value
                                    return
                    except (ValueError, KeyError):
                        # Failed to decode JWT, identity_id will remain None
                        pass
        except Exception:
            # Failed to extract identity_id from token, will remain None
            pass
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            return False
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            response = requests.post(self.auth_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                expires_in = data.get('expires_in', 1800)
                self.token_expiry = time.time() + expires_in
                return True
        except:
            pass
        
        return False
    
    def _ensure_authenticated(self):
        """Ensure we have a valid access token, refresh if needed."""
        if not self.access_token:
            raise Exception("Not authenticated. Please call authenticate() first.")
        
        # Check if token is about to expire (within 5 minutes)
        if self.token_expiry and (time.time() + 300) > self.token_expiry:
            if not self.refresh_access_token():
                raise Exception("Token expired and refresh failed. Please re-authenticate.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GraphQL requests."""
        self._ensure_authenticated()
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "x-ws-api-version": "12",
            "x-platform-os": "web",
            "x-ws-locale": "en-CA",
            "x-ws-profile": "trade"
        }
    
    def graphql_query(self, operation_name: str, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        Execute a GraphQL query or mutation.
        
        Args:
            operation_name: The operation name
            query: The GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Response data dictionary
            
        Raises:
            Exception if the request fails
        """
        payload = {
            "operationName": operation_name,
            "query": query,
            "variables": variables or {}
        }
        
        response = requests.post(self.api_url, json=payload, headers=self._get_headers())
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                raise Exception(f"GraphQL errors: {data['errors']}")
            return data
        else:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")
    
    # ==================== Security Search & Info ====================
    
    def search_securities(self, query: str, security_group_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Search for securities by ticker symbol or name.
        
        Args:
            query: Search query (ticker symbol or company name)
            security_group_ids: Optional list of security group IDs to filter by
            
        Returns:
            List of security results
        """
        gql_query = """
        query FetchSecuritySearchResult($query: String!, $securityGroupIds: [String!]) {
          securitySearch(input: {query: $query, securityGroupIds: $securityGroupIds}) {
            results {
              id
              buyable
              sellable
              optionsEligible
              securityType
              allowedOrderSubtypes
              status
              stock {
                symbol
                name
                primaryExchange
              }
              features
              logoUrl
              quoteV2(currency: null) {
                securityId
                currency
                price
                ... on EquityQuote {
                  marketStatus
                  close
                  high
                  low
                  open
                  volume: vol
                }
              }
            }
          }
        }
        """
        
        variables = {
            "query": query,
            "securityGroupIds": security_group_ids
        }
        
        result = self.graphql_query("FetchSecuritySearchResult", gql_query, variables)
        return result.get('data', {}).get('securitySearch', {}).get('results', [])
    
    def get_security(self, security_id: str, currency: Optional[str] = None) -> Dict:
        """
        Get detailed information about a security.
        
        Args:
            security_id: The security ID (e.g., 'sec-s-xxxxx')
            currency: Optional currency for fundamentals
            
        Returns:
            Security details dictionary
        """
        gql_query = """
        query FetchSecurity($securityId: ID!, $currency: Currency) {
          security(id: $securityId) {
            id
            active
            activeDate
            allowedOrderSubtypes
            buyable
            currency
            depositEligible
            features
            inactiveDate
            isVolatile
            logoUrl
            securityType
            sellable
            settleable
            status
            wsTradeEligible
            wsTradeIneligibilityReason
            optionsEligible
            equityTradingSessionType
            stock {
              description
              dividendFrequency
              name
              primaryExchange
              primaryMic
              symbol
            }
            fundamentals(currency: $currency) {
              avgVolume
              beta
              marketCap
              peRatio
              eps
              yield
              high52Week
              low52Week
              description
            }
            quoteV2(currency: $currency) {
              securityId
              currency
              price
              ask
              bid
              ... on EquityQuote {
                marketStatus
                close
                high
                low
                open
                volume: vol
                askSize
                bidSize
                last
                lastSize
                mid
              }
            }
            optionDetails {
              expiryDate
              maturity
              multiplier
              optionType
              osiSymbol
              strikePrice
              underlyingSecurity {
                id
                stock {
                  name
                  symbol
                  primaryExchange
                }
              }
            }
          }
        }
        """
        
        variables = {
            "securityId": security_id,
            "currency": currency
        }
        
        result = self.graphql_query("FetchSecurity", gql_query, variables)
        return result.get('data', {}).get('security', {})
    
    def get_security_quote(self, security_id: str, currency: Optional[str] = None) -> Dict:
        """
        Get real-time quote for a security.
        
        Args:
            security_id: The security ID
            currency: Optional currency
            
        Returns:
            Quote dictionary
        """
        gql_query = """
        query FetchSecurityQuoteV2($id: ID!, $currency: Currency = null) {
          security(id: $id) {
            id
            quoteV2(currency: $currency) {
              securityId
              ask
              bid
              currency
              price
              sessionPrice
              quotedAsOf
              previousBaseline
              ... on EquityQuote {
                marketStatus
                askSize
                bidSize
                close
                high
                last
                lastSize
                low
                open
                mid
                volume: vol
                referenceClose
              }
              ... on OptionQuote {
                marketStatus
                askSize
                bidSize
                close
                high
                last
                lastSize
                low
                open
                mid
                volume: vol
                breakEven
                inTheMoney
                liquidityStatus
                openInterest
                underlyingSpot
              }
            }
          }
        }
        """
        
        variables = {
            "id": security_id,
            "currency": currency
        }
        
        result = self.graphql_query("FetchSecurityQuoteV2", gql_query, variables)
        return result.get('data', {}).get('security', {}).get('quoteV2', {})
    
    def get_ticker_id(self, ticker: str, exchange: Optional[str] = None) -> Optional[str]:
        """
        Get security ID by ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            exchange: Optional exchange to filter by (e.g., 'NASDAQ', 'TSX')
            
        Returns:
            Security ID string or None if not found
        """
        results = self.search_securities(ticker)
        
        for result in results:
            stock = result.get('stock', {})
            if stock.get('symbol') == ticker:
                if exchange is None or stock.get('primaryExchange') == exchange:
                    return result.get('id')
        
        return None
    
    # ==================== Options Trading ====================
    
    def get_option_chain(self, security_id: str, expiry_date: str, option_type: str = 'CALL',
                        include_greeks: bool = True, real_time_quote: bool = True) -> List[Dict]:
        """
        Get option chain for a security.
        
        Args:
            security_id: Underlying security ID
            expiry_date: Expiry date in YYYY-MM-DD format
            option_type: 'CALL' or 'PUT'
            include_greeks: Include option greeks
            real_time_quote: Include real-time quotes
            
        Returns:
            List of option contracts
        """
        gql_query = """
        query FetchOptionChain($id: ID!, $expiryDate: Date!, $optionType: OptionType!, 
                               $realTimeQuote: Boolean, $includeGreeks: Boolean!) {
          security(id: $id) {
            id
            optionChain(
              expiryDate: $expiryDate
              optionType: $optionType
              realTimeQuote: $realTimeQuote
            ) {
              edges {
                node {
                  id
                  optionDetails {
                    strikePrice
                    optionType
                    expiryDate
                    multiplier
                    osiSymbol
                    greekSymbols @include(if: $includeGreeks) {
                      delta
                      gamma
                      theta
                      vega
                      rho
                      impliedVolatility
                      calculationTime
                    }
                  }
                  quoteV2(currency: null) {
                    securityId
                    ask
                    bid
                    currency
                    price
                    ... on OptionQuote {
                      marketStatus
                      askSize
                      bidSize
                      close
                      high
                      last
                      low
                      open
                      volume: vol
                      breakEven
                      inTheMoney
                      liquidityStatus
                      openInterest
                      underlyingSpot
                    }
                  }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        
        variables = {
            "id": security_id,
            "expiryDate": expiry_date,
            "optionType": option_type,
            "realTimeQuote": real_time_quote,
            "includeGreeks": include_greeks
        }
        
        result = self.graphql_query("FetchOptionChain", gql_query, variables)
        chain = result.get('data', {}).get('security', {}).get('optionChain', {})
        edges = chain.get('edges', [])
        
        return [edge.get('node', {}) for edge in edges]
    
    def get_option_expiry_dates(self, security_id: str, min_date: Optional[str] = None,
                               max_date: Optional[str] = None) -> List[str]:
        """
        Get available option expiry dates for a security.
        
        Args:
            security_id: Underlying security ID
            min_date: Minimum date in YYYY-MM-DD format
            max_date: Maximum date in YYYY-MM-DD format
            
        Returns:
            List of expiry dates
        """
        if not min_date:
            min_date = datetime.now().strftime('%Y-%m-%d')
        if not max_date:
            # Default to 2 years from now
            from datetime import timedelta
            max_date = (datetime.now() + timedelta(days=730)).strftime('%Y-%m-%d')
        
        gql_query = """
        query FetchOptionExpirationDates($securityId: ID!, $minDate: Date!, $maxDate: Date!) {
          security(id: $securityId) {
            id
            optionExpiryDates(minDate: $minDate, maxDate: $maxDate)
          }
        }
        """
        
        variables = {
            "securityId": security_id,
            "minDate": min_date,
            "maxDate": max_date
        }
        
        result = self.graphql_query("FetchOptionExpirationDates", gql_query, variables)
        return result.get('data', {}).get('security', {}).get('optionExpiryDates', [])
    
    def get_option_transaction_fees(self, side: str, premium: float, quantity: int,
                                   multiplier: int = 100, currency: str = 'CAD') -> Dict:
        """
        Calculate option transaction fees.
        
        Args:
            side: 'BUY_QUANTITY' or 'SELL_QUANTITY'
            premium: Option premium price
            quantity: Number of contracts
            multiplier: Contract multiplier (usually 100)
            currency: Currency
            
        Returns:
            Fee information dictionary
        """
        gql_query = """
        query FetchOptionTransactionFees($side: OrderType!, $premium: BigDecimal!, 
                                        $quantity: Int!, $multiplier: Int!, $currency: Currency!) {
          optionTransactionFees(
            side: $side
            premium: $premium
            quantity: $quantity
            multiplier: $multiplier
            currency: $currency
          ) {
            commission {
              amount
              currency
            }
            sec {
              amount
              currency
            }
            total {
              amount
              currency
            }
          }
        }
        """
        
        variables = {
            "side": side,
            "premium": str(premium),
            "quantity": quantity,
            "multiplier": multiplier,
            "currency": currency
        }
        
        result = self.graphql_query("FetchOptionTransactionFees", gql_query, variables)
        return result.get('data', {}).get('optionTransactionFees', {})
    
    # ==================== Account Management ====================
    
    def get_accounts(self, identity_id: Optional[str] = None) -> List[Dict]:
        """
        Get all accounts for the authenticated user.
        
        Args:
            identity_id: Optional identity ID (uses authenticated user's ID if not provided)
            
        Returns:
            List of accounts
        """
        if not identity_id:
            identity_id = self.identity_id
        
        if not identity_id:
            # Try to fetch identity ID one more time from JWT token
            self._fetch_identity_id_from_token()
            identity_id = self.identity_id
            
        if not identity_id:
            raise Exception("No identity ID available. Please authenticate first.")
        
        gql_query = """
        query FetchAllAccounts($identityId: ID!, $filter: AccountsFilter = {}, $pageSize: Int = 25) {
          identity(id: $identityId) {
            id
            accounts(filter: $filter, first: $pageSize) {
              edges {
                node {
                  id
                  branch
                  currency
                  nickname
                  status
                  unifiedAccountType
                  type
                  createdAt
                  custodianAccounts {
                    id
                    branch
                    custodian
                    status
                  }
                  accountFeatures {
                    name
                    enabled
                    functional
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "identityId": identity_id,
            "filter": {},
            "pageSize": 100
        }
        
        result = self.graphql_query("FetchAllAccounts", gql_query, variables)
        edges = result.get('data', {}).get('identity', {}).get('accounts', {}).get('edges', [])
        
        return [edge.get('node', {}) for edge in edges]
    
    def get_account_financials(self, account_ids: List[str], currency: str = 'CAD') -> List[Dict]:
        """
        Get financial information for specific accounts.
        
        Args:
            account_ids: List of account IDs
            currency: Currency for the financials
            
        Returns:
            List of account financial data
        """
        gql_query = """
        query FetchAccountFinancials($ids: [String!]!, $currency: Currency) {
          accounts(ids: $ids) {
            id
            custodianAccounts {
              id
              branch
              financials {
                current {
                  netLiquidation(currency: $currency) {
                    amount
                    currency
                  }
                  buyingPower(currency: $currency) {
                    amount
                    currency
                  }
                  availableToBuy(currency: $currency) {
                    amount
                    currency
                  }
                  cash(currency: $currency) {
                    amount
                    currency
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "ids": account_ids,
            "currency": currency
        }
        
        result = self.graphql_query("FetchAccountFinancials", gql_query, variables)
        return result.get('data', {}).get('accounts', [])
    
    def get_positions(self, identity_id: Optional[str] = None, account_ids: Optional[List[str]] = None,
                     currency: str = 'CAD', security_type: Optional[str] = None) -> List[Dict]:
        """
        Get positions for the authenticated user.
        
        Args:
            identity_id: Optional identity ID (uses authenticated user's ID if not provided)
            account_ids: Optional list of account IDs to filter by
            currency: Currency for position values
            security_type: Optional security type filter ('EQUITY', 'OPTION', 'CRYPTO')
            
        Returns:
            List of positions
        """
        if not identity_id:
            identity_id = self.identity_id
        
        if not identity_id:
            # Try to fetch identity ID one more time from JWT token
            self._fetch_identity_id_from_token()
            identity_id = self.identity_id
            
        if not identity_id:
            raise Exception("No identity ID available. Please authenticate first.")
        
        gql_query = """
        query FetchIdentityPositions($identityId: ID!, $currency: Currency!, $accountIds: [ID!], 
                                     $filter: PositionFilter) {
          identity(id: $identityId) {
            id
            financials(filter: {accounts: $accountIds}) {
              current(currency: $currency) {
                positions(filter: $filter) {
                  edges {
                    node {
                      id
                      quantity
                      percentageOfAccount
                      positionDirection
                      bookValue {
                        amount
                        currency
                      }
                      averagePrice {
                        amount
                        currency
                      }
                      totalValue {
                        amount
                        currency
                      }
                      unrealizedReturns {
                        amount
                        currency
                      }
                      security {
                        id
                        securityType
                        stock {
                          name
                          symbol
                          primaryExchange
                        }
                        optionDetails {
                          strikePrice
                          optionType
                          expiryDate
                          osiSymbol
                        }
                      }
                    }
                  }
                  totalCount
                }
              }
            }
          }
        }
        """
        
        position_filter = {}
        if security_type:
            position_filter['positionSecurityType'] = security_type
        
        variables = {
            "identityId": identity_id,
            "currency": currency,
            "accountIds": account_ids,
            "filter": position_filter if position_filter else None
        }
        
        result = self.graphql_query("FetchIdentityPositions", gql_query, variables)
        positions_data = result.get('data', {}).get('identity', {}).get('financials', {}).get('current', {}).get('positions', {})
        edges = positions_data.get('edges', [])
        
        return [edge.get('node', {}) for edge in edges]
    
    def get_activities(self, account_ids: Optional[List[str]] = None, types: Optional[List[str]] = None,
                      statuses: Optional[List[str]] = None, limit: int = 100) -> List[Dict]:
        """
        Get activity feed items (orders, trades, deposits, etc.).
        
        Args:
            account_ids: Optional list of account IDs to filter by
            types: Optional list of activity types to filter by
            statuses: Optional list of statuses to filter by
            limit: Maximum number of items to return
            
        Returns:
            List of activity items
        """
        gql_query = """
        query FetchActivityFeedItems($first: Int, $condition: ActivityCondition, 
                                     $orderBy: [ActivitiesOrderBy!] = OCCURRED_AT_DESC) {
          activityFeedItems(first: $first, condition: $condition, orderBy: $orderBy) {
            edges {
              node {
                accountId
                amount
                amountSign
                assetQuantity
                assetSymbol
                canonicalId
                currency
                occurredAt
                securityId
                status
                subType
                symbol
                type
                unifiedStatus
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        condition = {}
        if account_ids:
            condition['accountIds'] = account_ids
        if types:
            condition['types'] = types
        if statuses:
            condition['unifiedStatuses'] = statuses
        
        variables = {
            "first": limit,
            "condition": condition if condition else None,
            "orderBy": "OCCURRED_AT_DESC"
        }
        
        result = self.graphql_query("FetchActivityFeedItems", gql_query, variables)
        edges = result.get('data', {}).get('activityFeedItems', {}).get('edges', [])
        
        return [edge.get('node', {}) for edge in edges]
    
    # ==================== Trading ====================
    
    def create_order(self, account_id: str, security_id: str, quantity: int,
                    order_type: str = 'BUY_QUANTITY', execution_type: str = 'LIMIT',
                    limit_price: Optional[float] = None, stop_price: Optional[float] = None,
                    time_in_force: str = 'DAY', open_close: Optional[str] = None,
                    trading_session: str = 'EXTENDED') -> Dict:
        """
        Create a new order (stock or option).
        
        Args:
            account_id: Account ID to place the order in
            security_id: Security ID to trade
            quantity: Number of shares/contracts
            order_type: 'BUY_QUANTITY' or 'SELL_QUANTITY'
            execution_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
            limit_price: Limit price (required for LIMIT and STOP_LIMIT orders)
            stop_price: Stop price (required for STOP and STOP_LIMIT orders)
            time_in_force: 'DAY', 'GTC', etc.
            open_close: For options: 'OPEN' (to open position) or 'CLOSE' (to close position)
            trading_session: 'EXTENDED' (default) or 'REGULAR'
            
        Returns:
            Order creation response
        """
        import uuid
        
        gql_query = """
        mutation SoOrdersOrderCreate($input: SoOrders_CreateOrderInput!) {
          soOrdersCreateOrder(input: $input) {
            errors {
              code
              message
              __typename
            }
            order {
              orderId
              createdAt
              __typename
            }
            __typename
          }
        }
        """
        
        order_input = {
            "canonicalAccountId": account_id,
            "externalId": f"order-{uuid.uuid4()}",
            "executionType": execution_type,
            "orderType": order_type,
            "quantity": quantity,
            "securityId": security_id,
            "timeInForce": time_in_force,
            "tradingSession": trading_session
        }
        
        if limit_price is not None:
            order_input["limitPrice"] = limit_price
        
        if stop_price is not None:
            order_input["stopPrice"] = stop_price
        
        if open_close is not None:
            order_input["openClose"] = open_close
        
        variables = {
            "input": order_input
        }
        
        result = self.graphql_query("SoOrdersOrderCreate", gql_query, variables)
        return result.get('data', {}).get('soOrdersCreateOrder', {})
    
    # Convenience methods for common order types
    
    def market_buy(self, account_id: str, security_id: str, quantity: int) -> Dict:
        """Place a market buy order."""
        return self.create_order(account_id, security_id, quantity, 'BUY_QUANTITY', 'MARKET')
    
    def market_sell(self, account_id: str, security_id: str, quantity: int) -> Dict:
        """Place a market sell order."""
        return self.create_order(account_id, security_id, quantity, 'SELL_QUANTITY', 'MARKET')
    
    def limit_buy(self, account_id: str, security_id: str, quantity: int, limit_price: float) -> Dict:
        """Place a limit buy order."""
        return self.create_order(account_id, security_id, quantity, 'BUY_QUANTITY', 'LIMIT', limit_price=limit_price)
    
    def limit_sell(self, account_id: str, security_id: str, quantity: int, limit_price: float) -> Dict:
        """Place a limit sell order."""
        return self.create_order(account_id, security_id, quantity, 'SELL_QUANTITY', 'LIMIT', limit_price=limit_price)
    
    def stop_limit_buy(self, account_id: str, security_id: str, quantity: int, 
                      limit_price: float, stop_price: float) -> Dict:
        """Place a stop-limit buy order."""
        return self.create_order(account_id, security_id, quantity, 'BUY_QUANTITY', 'STOP_LIMIT',
                               limit_price=limit_price, stop_price=stop_price)
    
    def stop_limit_sell(self, account_id: str, security_id: str, quantity: int,
                       limit_price: float, stop_price: float) -> Dict:
        """Place a stop-limit sell order."""
        return self.create_order(account_id, security_id, quantity, 'SELL_QUANTITY', 'STOP_LIMIT',
                               limit_price=limit_price, stop_price=stop_price)
    
    # Options trading convenience methods
    
    def buy_option(self, account_id: str, option_id: str, quantity: int, limit_price: float,
                  open_close: str = 'OPEN') -> Dict:
        """
        Buy an option contract.
        
        Args:
            account_id: Account ID
            option_id: Option security ID
            quantity: Number of contracts
            limit_price: Limit price per contract
            open_close: 'OPEN' to open a new position or 'CLOSE' to close an existing short position
        """
        return self.create_order(account_id, option_id, quantity, 'BUY_QUANTITY', 'LIMIT',
                               limit_price=limit_price, open_close=open_close)
    
    def sell_option(self, account_id: str, option_id: str, quantity: int, limit_price: float,
                   open_close: str = 'CLOSE') -> Dict:
        """
        Sell an option contract.
        
        Args:
            account_id: Account ID
            option_id: Option security ID
            quantity: Number of contracts
            limit_price: Limit price per contract
            open_close: 'CLOSE' to close an existing long position or 'OPEN' to write/sell short
        """
        return self.create_order(account_id, option_id, quantity, 'SELL_QUANTITY', 'LIMIT',
                               limit_price=limit_price, open_close=open_close)
    
    # ==================== Identity & User Info ====================
    
    def get_identity(self, identity_id: Optional[str] = None) -> Dict:
        """
        Get identity information for the authenticated user.
        
        Args:
            identity_id: Optional identity ID (uses authenticated user's ID if not provided)
            
        Returns:
            Identity information dictionary
        """
        if not identity_id:
            identity_id = self.identity_id
        
        if not identity_id:
            # Try to fetch identity ID one more time from JWT token
            self._fetch_identity_id_from_token()
            identity_id = self.identity_id
            
        if not identity_id:
            raise Exception("No identity ID available. Please authenticate first.")
        
        gql_query = """
        query FetchIdentity($id: ID!) {
          identity(id: $id) {
            id
            createdAt
            email
            emailVerified
            fullName
            givenName
            familyName
            citizenship
            dateOfBirth
            phoneNumber
            address {
              streetAddress
              city
              province
              postalCode
              country
            }
          }
        }
        """
        
        variables = {
            "id": identity_id
        }
        
        result = self.graphql_query("FetchIdentity", gql_query, variables)
        return result.get('data', {}).get('identity', {})


# ==================== Helper Functions ====================

def quote(ticker: str, source: str = 'wealthsimple', asset_class: str = 'stocks') -> Optional[float]:
    """
    Get a quick quote for a ticker symbol.
    
    This is a standalone function that doesn't require authentication for some sources.
    For Wealthsimple source, you need to provide credentials via environment variables.
    
    Args:
        ticker: Stock ticker symbol
        source: Quote source ('wealthsimple', 'yahoo', 'nasdaq', 'tsx')
        asset_class: Asset class (default: 'stocks')
        
    Returns:
        Current price or None if unavailable
    """
    if source.lower() == 'wealthsimple':
        # Use Wealthsimple API (requires auth)
        ws = WealthsimpleV2()
        security_id = ws.get_ticker_id(ticker)
        if security_id:
            quote_data = ws.get_security_quote(security_id)
            return quote_data.get('price')
        return None
    
    elif source.lower() == 'yahoo':
        try:
            import requests
            r = requests.get(
                f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}', 
                timeout=3
            )
            return float(r.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        except:
            return None
    
    elif source.lower() == 'nasdaq':
        try:
            import requests
            r = requests.get(
                f'https://api.nasdaq.com/api/quote/{ticker}/info',
                params={'assetclass': asset_class},
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'},
                timeout=3
            )
            price_str = r.json()['data']['primaryData']['lastSalePrice'].strip('$')
            return float(price_str)
        except:
            return None
    
    elif source.lower() in ['tsx', 'tmx']:
        try:
            import requests
            r = requests.post(
                'https://app-money.tmx.com/graphql',
                json={
                    "operationName": "getQuoteBySymbol",
                    "variables": {"symbol": ticker, "locale": "en"},
                    "query": "query getQuoteBySymbol($symbol: String, $locale: String) { getQuoteBySymbol(symbol: $symbol, locale: $locale) { symbol name price }}"
                },
                timeout=3
            )
            return float(r.json()['data']['getQuoteBySymbol']['price'])
        except:
            return None
    
    return None


if __name__ == "__main__":
    # Example usage
    print("Wealthsimple API v2 - Example Usage")
    print("=" * 50)
    
    # Initialize with credentials from environment variables
    try:
        ws = WealthsimpleV2()
        print("✓ Authenticated successfully")
        print(f"✓ Identity ID: {ws.identity_id}")
        
        # Search for a security
        print("\n--- Searching for AAPL ---")
        results = ws.search_securities("AAPL")
        if results:
            print(f"Found {len(results)} result(s)")
            aapl = results[0]
            print(f"  Symbol: {aapl['stock']['symbol']}")
            print(f"  Name: {aapl['stock']['name']}")
            print(f"  Security ID: {aapl['id']}")
            
            # Get current quote
            quote_data = ws.get_security_quote(aapl['id'])
            print(f"  Price: ${quote_data.get('price', 'N/A')}")
        
        # Get accounts
        print("\n--- Fetching Accounts ---")
        accounts = ws.get_accounts()
        print(f"Found {len(accounts)} account(s)")
        for acc in accounts[:3]:  # Show first 3
            print(f"  {acc['nickname']} ({acc['id']}) - {acc['unifiedAccountType']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTo use this example, set environment variables:")
        print("  export WS_USERNAME='your@email.com'")
        print("  export WS_PASSWORD='yourpassword'")
        print("  export WS_OTP='123456'  # Optional, only if 2FA enabled")


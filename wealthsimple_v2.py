"""
Wealthsimple API v2 - Unofficial GraphQL-based API Client

This module provides an unofficial Python client for the Wealthsimple platform
using their GraphQL API. It supports authentication, security search, trading,
options trading, account management, and real-time WebSocket subscriptions.

Based on network traffic analysis from the Wealthsimple web application.

Features:
    - Secure token storage using keyring (OS credential storage)
    - Automatic token refresh and persistence
    - Real-time WebSocket subscriptions
    - Full trading support (stocks and options)
    - Comprehensive account management

Dependencies:
    - requests (required)
    - keyring (optional but recommended - for secure token storage)
    - websockets (optional - for real-time subscriptions)

Usage:
    from wealthsimple_v2 import WealthsimpleV2, OrderStatus, OrderType
    
    # Authenticate (tokens automatically saved to keyring)
    ws = WealthsimpleV2(username='your@email.com', password='yourpassword')
    
    # Later sessions - tokens automatically loaded from keyring
    ws = WealthsimpleV2()  # No credentials needed!
    
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
        order_type=OrderType.BUY_QUANTITY
    )
    
    # Get pending orders
    pending = ws.get_pending_orders(account_ids=['tfsa-xxxxx'])
    
    # Cancel an order
    ws.cancel_order(order['externalCanonicalId'])
    
    # Filter activities by status
    activities = ws.get_activities(
        statuses=[OrderStatus.FILLED],
        types=[OrderType.DIY_BUY]
    )
    
    # Logout and clear all tokens
    ws.logout()
    
    # Real-time subscriptions (requires 'websockets' package)
    import asyncio
    
    async def stream_quotes():
        async with ws.subscribe() as sub:
            async for msg in sub.stream_quotes(['sec-s-xxxxx']):
                quote = msg['payload']['data']['securityQuoteUpdates']['quoteV2']
                print(f"Price: {quote['price']}")
    
    asyncio.run(stream_quotes())
"""

import requests
import json
import os
import time
import base64
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from datetime import datetime, date

# Optional WebSocket support for subscriptions
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None
    WebSocketClientProtocol = None

# Optional keyring support for secure token storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None


# ==================== Constants & Enums ====================

class OrderStatus:
    """Order status constants for filtering activities."""
    PENDING = 'PENDING'        # Order submitted but not yet executed
    FILLED = 'FILLED'          # Order completed/executed
    CANCELLED = 'CANCELLED'    # Order cancelled
    SUBMITTED = 'SUBMITTED'    # Order submitted to exchange
    REJECTED = 'REJECTED'      # Order rejected
    EXPIRED = 'EXPIRED'        # Order expired
    COMPLETED = 'COMPLETED'    # Order completed (alternative to FILLED)


class OrderType:
    """Order type constants."""
    BUY_QUANTITY = 'BUY_QUANTITY'
    SELL_QUANTITY = 'SELL_QUANTITY'
    
    # Activity types for filtering
    DIY_BUY = 'DIY_BUY'
    DIY_SELL = 'DIY_SELL'
    OPTIONS_BUY = 'OPTIONS_BUY'
    OPTIONS_SELL = 'OPTIONS_SELL'
    OPTIONS_MULTILEG = 'OPTIONS_MULTILEG'
    MANAGED_BUY = 'MANAGED_BUY'
    MANAGED_SELL = 'MANAGED_SELL'
    CRYPTO_BUY = 'CRYPTO_BUY'
    CRYPTO_SELL = 'CRYPTO_SELL'
    DIVIDEND = 'DIVIDEND'


class OrderSubType:
    """Order sub-type constants."""
    LIMIT_ORDER = 'LIMIT_ORDER'
    MARKET_ORDER = 'MARKET_ORDER'
    STOP_ORDER = 'STOP_ORDER'
    STOP_LIMIT_ORDER = 'STOP_LIMIT_ORDER'
    FRACTIONAL_ORDER = 'FRACTIONAL_ORDER'
    DIVIDEND_REINVESTMENT = 'DIVIDEND_REINVESTMENT'


class ExecutionType:
    """Execution type constants for order creation."""
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP = 'STOP'
    STOP_LIMIT = 'STOP_LIMIT'


class TimeInForce:
    """Time in force constants."""
    DAY = 'DAY'          # Day order
    GTC = 'GTC'          # Good till cancelled
    GTD = 'GTD'          # Good till date
    IOC = 'IOC'          # Immediate or cancel
    FOK = 'FOK'          # Fill or kill


class WealthsimpleV2:
    """
    Unofficial Wealthsimple API v2 Client
    
    This client uses the GraphQL API endpoint at https://my.wealthsimple.com/graphql
    with OAuth v2 authentication.
    
    Tokens are securely stored using the keyring library (if available), which uses
    the operating system's credential storage (Keychain on macOS, Credential Locker
    on Windows, Secret Service on Linux).
    """
    
    # Keyring service name for token storage
    KEYRING_SERVICE = "wealthsimple-python"
    
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
            # Try to load tokens from keyring first (most secure)
            if self._load_tokens_from_keyring():
                # Successfully loaded tokens from keyring
                self._fetch_identity_id_from_token()
            else:
                # Fallback: Try to get tokens from environment variables
                env_access_token = os.getenv('WS_ACCESS_TOKEN')
                env_refresh_token = os.getenv('WS_REFRESH_TOKEN')
                
                if env_access_token and env_refresh_token:
                    # Use existing tokens from environment
                    self.access_token = env_access_token
                    self.refresh_token = env_refresh_token
                    # Extract identity ID from token
                    self._fetch_identity_id_from_token()
                else:
                    # Try to authenticate with credentials from environment variables
                    username = os.getenv('WS_USERNAME')
                    password = os.getenv('WS_PASSWORD')
                    otp = os.getenv('WS_OTP')
                    if username and password:
                        self.authenticate(username, password, otp)
    
    def _save_tokens_to_keyring(self, username: Optional[str] = None) -> bool:
        """
        Save tokens to keyring (secure credential storage).
        
        Args:
            username: Optional username to use as keyring username (defaults to 'default')
            
        Returns:
            True if tokens were successfully saved, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False
        
        keyring_username = username or os.getenv('WS_USERNAME') or 'default'
        
        try:
            saved_any = False
            if self.access_token:
                keyring.set_password(self.KEYRING_SERVICE, f"{keyring_username}_access_token", self.access_token)
                saved_any = True
            if self.refresh_token:
                keyring.set_password(self.KEYRING_SERVICE, f"{keyring_username}_refresh_token", self.refresh_token)
                saved_any = True
            if self.token_expiry:
                keyring.set_password(self.KEYRING_SERVICE, f"{keyring_username}_token_expiry", str(self.token_expiry))
                saved_any = True
            return saved_any
        except Exception as e:
            print(f"Failed to save to keyring: {e}")
            # If keyring fails, silently continue (tokens won't be persisted)
            # In debug mode, you could log this: print(f"Failed to save to keyring: {e}")
            return False
    
    def _load_tokens_from_keyring(self, username: Optional[str] = None) -> bool:
        """
        Load tokens from keyring (secure credential storage).
        
        Args:
            username: Optional username to use as keyring username (defaults to 'default')
            
        Returns:
            True if tokens were successfully loaded, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False
        
        keyring_username = username or os.getenv('WS_USERNAME') or 'default'
        
        try:
            access_token = keyring.get_password(self.KEYRING_SERVICE, f"{keyring_username}_access_token")
            refresh_token = keyring.get_password(self.KEYRING_SERVICE, f"{keyring_username}_refresh_token")
            token_expiry_str = keyring.get_password(self.KEYRING_SERVICE, f"{keyring_username}_token_expiry")
            
            if access_token and refresh_token:
                self.access_token = access_token
                self.refresh_token = refresh_token
                if token_expiry_str:
                    try:
                        self.token_expiry = float(token_expiry_str)
                    except ValueError:
                        self.token_expiry = None
                return True
        except Exception:
            pass
        
        return False
    
    def _delete_tokens_from_keyring(self, username: Optional[str] = None) -> None:
        """
        Delete tokens from keyring.
        
        Args:
            username: Optional username to use as keyring username (defaults to 'default')
        """
        if not KEYRING_AVAILABLE:
            return
        
        keyring_username = username or os.getenv('WS_USERNAME') or 'default'
        
        try:
            keyring.delete_password(self.KEYRING_SERVICE, f"{keyring_username}_access_token")
        except Exception:
            pass
        
        try:
            keyring.delete_password(self.KEYRING_SERVICE, f"{keyring_username}_refresh_token")
        except Exception:
            pass
        
        try:
            keyring.delete_password(self.KEYRING_SERVICE, f"{keyring_username}_token_expiry")
        except Exception:
            pass
    
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
            
            # Extract identity and profile information FIRST (before saving tokens)
            self.identity_id = data.get('identity_canonical_id')
            self.profiles = data.get('profiles', {})
            
            # If identity_id not in response, try to extract from JWT token
            if not self.identity_id and self.access_token:
                self._fetch_identity_id_from_token()
            
            # Save tokens to keyring (secure storage)
            # Note: We save after extracting identity_id so we have all the info
            self._save_tokens_to_keyring('default')
            print(f"Saved tokens to keyring")
            
            # Also save to environment variables as fallback
            if self.access_token:
                os.environ['WS_ACCESS_TOKEN'] = self.access_token
            if self.refresh_token:
                os.environ['WS_REFRESH_TOKEN'] = self.refresh_token
            
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
    
    def logout(self) -> None:
        """
        Logout and clear all stored tokens from keyring and environment variables.
        
        This will delete tokens from:
        - Keyring (secure OS credential storage)
        - Environment variables
        - Instance variables
        """
        # Clear tokens from keyring
        self._delete_tokens_from_keyring()
        
        # Clear tokens from environment variables
        if 'WS_ACCESS_TOKEN' in os.environ:
            del os.environ['WS_ACCESS_TOKEN']
        if 'WS_REFRESH_TOKEN' in os.environ:
            del os.environ['WS_REFRESH_TOKEN']
        
        # Clear instance variables
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.identity_id = None
        self.profiles = None
    
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
                
                # Save updated tokens to keyring (secure storage)
                self._save_tokens_to_keyring()
                
                # Also update tokens in environment variables as fallback
                if self.access_token:
                    os.environ['WS_ACCESS_TOKEN'] = self.access_token
                if self.refresh_token:
                    os.environ['WS_REFRESH_TOKEN'] = self.refresh_token
                
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
                        include_greeks: bool = True, real_time_quote: bool = True,
                        first: Optional[int] = None, cursor: Optional[str] = None) -> List[Dict]:
        """
        Get option chain for a security.
        
        Args:
            security_id: Underlying security ID
            expiry_date: Expiry date in YYYY-MM-DD format
            option_type: 'CALL' or 'PUT'
            include_greeks: Include option greeks
            real_time_quote: Include real-time quotes
            first: Optional limit on number of results
            cursor: Optional cursor for pagination
            
        Returns:
            List of option contracts
        """
        gql_query = """
        query FetchOptionChain($id: ID!, $expiryDate: Date!, $optionType: OptionType!, $realTimeQuote: Boolean, $cursor: String, $first: Int, $includeGreeks: Boolean!) {
          security(id: $id) {
            id
            optionChain(
              expiryDate: $expiryDate
              optionType: $optionType
              realTimeQuote: $realTimeQuote
              first: $first
              after: $cursor
            ) {
              edges {
                node {
                  ...OptionChainSecurity
                  __typename
                }
                __typename
              }
              pageInfo {
                hasNextPage
                endCursor
                __typename
              }
              __typename
            }
            __typename
          }
        }
        
        fragment OptionChainSecurity on Security {
          id
          ...OptionDetailsSummary
          quoteV2(currency: null) {
            ...SecurityQuoteV2
            __typename
          }
          __typename
        }
        
        fragment OptionDetailsSummary on Security {
          optionDetails {
            strikePrice
            optionType
            greekSymbols @include(if: $includeGreeks) {
              ...OptionGreekSymbols
              __typename
            }
            __typename
          }
          __typename
        }
        
        fragment OptionGreekSymbols on OptionGreekSymbols {
          id
          rho
          vega
          delta
          theta
          gamma
          impliedVolatility
          calculationTime
          __typename
        }
        
        fragment StreamedSecurityQuoteV2 on UnifiedQuote {
          __typename
          securityId
          ask
          bid
          currency
          price
          sessionPrice
          quotedAsOf
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
            __typename
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
            __typename
          }
        }
        
        fragment SecurityQuoteV2 on UnifiedQuote {
          ...StreamedSecurityQuoteV2
          previousBaseline
          __typename
        }
        """
        
        variables = {
            "id": security_id,
            "expiryDate": expiry_date,
            "optionType": option_type,
            "realTimeQuote": real_time_quote,
            "cursor": cursor,
            "first": first,
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
            # Default to 3 years from now
            from datetime import timedelta
            max_date = (datetime.now() + timedelta(days=1095)).strftime('%Y-%m-%d')
        
        gql_query = """
        query FetchOptionExpirationDates($securityId: ID!, $minDate: Date!, $maxDate: Date!) {
          security(id: $securityId) {
            id
            optionExpirationDates(minDate: $minDate, maxDate: $maxDate) {
              ...OptionExpirationDates
              __typename
            }
            __typename
          }
        }
        
        fragment OptionExpirationDates on OptionExpirationDates {
          expirationDates
          __typename
        }
        """
        
        variables = {
            "securityId": security_id,
            "minDate": min_date,
            "maxDate": max_date
        }
        
        result = self.graphql_query("FetchOptionExpirationDates", gql_query, variables)
        option_dates = result.get('data', {}).get('security', {}).get('optionExpirationDates', {})
        return option_dates.get('expirationDates', [])
    
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
    
    def get_account_funding_balances(self, account_ids: List[str]) -> List[Dict]:
        """
        Get account funding balances (available trading cash).
        
        Args:
            account_ids: List of account IDs
            
        Returns:
            List of account funding balances with trading_balances for each currency
        """
        gql_query = """
        query FetchAccountFundingBalances($accountIds: [ID!]!) {
          account_funding_balances(account_ids: $accountIds) {
            ...AccountFundingBalance
            __typename
          }
        }
        
        fragment AccountFundingBalance on AccountFundingBalance {
          id
          trading_balances {
            amount
            currency
            __typename
          }
          __typename
        }
        """
        
        variables = {
            "accountIds": account_ids
        }
        
        result = self.graphql_query("FetchAccountFundingBalances", gql_query, variables)
        return result.get('data', {}).get('account_funding_balances', [])
    
    def get_account_financials(self, account_ids: List[str], currency: str = 'CAD', 
                              start_date: Optional[str] = None) -> List[Dict]:
        """
        Get financial information for specific accounts.
        
        Args:
            account_ids: List of account IDs
            currency: Currency for the financials
            start_date: Optional start date for returns calculation (YYYY-MM-DD)
            
        Returns:
            List of account financial data
        """
        gql_query = """
        query FetchAccountFinancials($ids: [String!]!, $startDate: Date, $currency: Currency) {
          accounts(ids: $ids) {
            id
            ...AccountFinancials
            __typename
          }
        }
        
        fragment AccountFinancials on Account {
          id
          custodianAccounts {
            id
            branch
            financials {
              current {
                ...CustodianAccountCurrentFinancialValues
                __typename
              }
              __typename
            }
            __typename
          }
          financials {
            currentCombined(currency: $currency) {
              id
              ...AccountCurrentFinancials
              __typename
            }
            __typename
          }
          __typename
        }
        
        fragment CustodianAccountCurrentFinancialValues on CustodianAccountCurrentFinancialValues {
          deposits {
            ...Money
            __typename
          }
          earnings {
            ...Money
            __typename
          }
          netDeposits {
            ...Money
            __typename
          }
          netLiquidationValue {
            ...Money
            __typename
          }
          withdrawals {
            ...Money
            __typename
          }
          __typename
        }
        
        fragment Money on Money {
          amount
          cents
          currency
          __typename
        }
        
        fragment AccountCurrentFinancials on AccountCurrentFinancials {
          id
          netLiquidationValueV2 {
            ...Money
            __typename
          }
          netDeposits: netDepositsV2 {
            ...Money
            __typename
          }
          simpleReturns(referenceDate: $startDate) {
            ...SimpleReturns
            __typename
          }
          totalDeposits: totalDepositsV2 {
            ...Money
            __typename
          }
          totalWithdrawals: totalWithdrawalsV2 {
            ...Money
            __typename
          }
          __typename
        }
        
        fragment SimpleReturns on SimpleReturns {
          amount {
            ...Money
            __typename
          }
          asOf
          rate
          referenceDate
          __typename
        }
        """
        
        variables = {
            "ids": account_ids,
            "currency": currency,
            "startDate": start_date
        }
        
        result = self.graphql_query("FetchAccountFinancials", gql_query, variables)
        return result.get('data', {}).get('accounts', [])
    
    def get_positions(self, identity_id: Optional[str] = None, account_ids: Optional[List[str]] = None,
                     currency: Optional[str] = None, security_type: Optional[str] = None,
                     include_security: bool = True, first: int = 500, aggregated: bool = False) -> List[Dict]:
        """
        Get positions for the authenticated user.
        
        Args:
            identity_id: Optional identity ID (uses authenticated user's ID if not provided)
            account_ids: Optional list of account IDs to filter by
            currency: Currency for position values (default: None). If not set, currency_override is set to 'MARKET'
            security_type: Optional security type filter ('EQUITY', 'OPTION', 'CRYPTO')
            include_security: Include full security details in response
            first: Maximum number of positions to return
            aggregated: Whether to aggregate positions across accounts
            
        Returns:
            List of positions
        """
        # Set currency_override based on currency: if currency not set, use 'MARKET', otherwise None
        if currency is None:
            currency_override = 'MARKET'
            # If currency is not provided, default to 'CAD' for GraphQL query (required field)
            currency = 'CAD'
        else:
            currency_override = None
        
        if not identity_id:
            identity_id = self.identity_id
        
        if not identity_id:
            # Try to fetch identity ID one more time from JWT token
            self._fetch_identity_id_from_token()
            identity_id = self.identity_id
            
        if not identity_id:
            raise Exception("No identity ID available. Please authenticate first.")
        
        gql_query = """
        query FetchIdentityPositions($identityId: ID!, $currency: Currency!, $first: Int, $cursor: String, 
                                     $accountIds: [ID!], $aggregated: Boolean, $currencyOverride: CurrencyOverride, 
                                     $filter: PositionFilter, $includeSecurity: Boolean = false) {
          identity(id: $identityId) {
            id
            financials(filter: {accounts: $accountIds}) {
              current(currency: $currency) {
                id
                positions(first: $first, after: $cursor, aggregated: $aggregated, filter: $filter) {
                  edges {
                    node {
                      id
                      quantity
                      percentageOfAccount
                      positionDirection
                      bookValue {
                        amount
                        currency
                        __typename
                      }
                      averagePrice {
                        amount
                        currency
                        __typename
                      }
                      marketAveragePrice: averagePrice(currencyOverride: $currencyOverride) {
                        amount
                        currency
                        __typename
                      }
                      marketBookValue: bookValue(currencyOverride: $currencyOverride) {
                        amount
                        currency
                        __typename
                      }
                      totalValue(currencyOverride: $currencyOverride) {
                        amount
                        currency
                        __typename
                      }
                      unrealizedReturns {
                        amount
                        currency
                        __typename
                      }
                      marketUnrealizedReturns: unrealizedReturns(currencyOverride: $currencyOverride) {
                        amount
                        currency
                        __typename
                      }
                      security {
                        id
                        securityType
                        currency
                        status
                        logoUrl
                        features
                        stock @include(if: $includeSecurity) {
                          name
                          symbol
                          primaryExchange
                          primaryMic
                          __typename
                        }
                        optionDetails @include(if: $includeSecurity) {
                          strikePrice
                          optionType
                          expiryDate
                          osiSymbol
                          multiplier
                          maturity
                          underlyingSecurity {
                            id
                            stock {
                              name
                              symbol
                              primaryExchange
                              __typename
                            }
                            __typename
                          }
                          __typename
                        }
                        quoteV2(currency: null) @include(if: $includeSecurity) {
                          securityId
                          currency
                          price
                          sessionPrice
                          ask
                          bid
                          quotedAsOf
                          previousBaseline
                          __typename
                        }
                        __typename
                      }
                      __typename
                    }
                    __typename
                  }
                  pageInfo {
                    hasNextPage
                    endCursor
                    __typename
                  }
                  totalCount
                  status
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
        }
        """
        
        position_filter = {}
        if security_type:
            position_filter['positionSecurityType'] = security_type
        
        variables = {
            "identityId": identity_id,
            "currency": currency,
            "currencyOverride": currency_override,
            "accountIds": account_ids,
            "filter": position_filter if position_filter else None,
            "first": first,
            "aggregated": aggregated,
            "includeSecurity": include_security,
            "cursor": None
        }
        
        result = self.graphql_query("FetchIdentityPositions", gql_query, variables)
        positions_data = result.get('data', {}).get('identity', {}).get('financials', {}).get('current', {}).get('positions', {})
        edges = positions_data.get('edges', [])
        
        return [edge.get('node', {}) for edge in edges]
    
    def get_activities(self, account_ids: Optional[List[str]] = None, types: Optional[List[str]] = None,
                      statuses: Optional[List[str]] = None, sub_types: Optional[List[str]] = None,
                      security_ids: Optional[List[str]] = None, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, limit: int = 100, cursor: Optional[str] = None) -> Dict:
        """
        Get activity feed items (orders, trades, deposits, etc.).
        
        Args:
            account_ids: Optional list of account IDs to filter by
            types: Optional list of activity types to filter by (e.g., 'DIY_BUY', 'DIY_SELL', 
                   'OPTIONS_BUY', 'OPTIONS_SELL', 'CRYPTO_BUY', 'DIVIDEND', etc.)
            statuses: Optional list of statuses to filter by (e.g., 'PENDING', 'COMPLETED', 'CANCELLED')
            sub_types: Optional list of sub-types to filter by (e.g., 'LIMIT_ORDER', 'MARKET_ORDER', 
                      'STOP_LIMIT_ORDER', 'FRACTIONAL_ORDER', 'DIVIDEND_REINVESTMENT', etc.)
            security_ids: Optional list of security IDs to filter by specific securities
            start_date: Optional start date in ISO format (e.g., '2025-10-01T00:00:00.000Z')
            end_date: Optional end date in ISO format (e.g., '2025-10-29T23:59:59.999Z')
            limit: Maximum number of items to return
            cursor: Optional cursor for pagination
            
        Returns:
            Dictionary containing 'items' (list of activity items) and 'pageInfo' for pagination
        """
        gql_query = """
        query FetchActivityFeedItems($first: Int, $cursor: Cursor, $condition: ActivityCondition, 
                                     $orderBy: [ActivitiesOrderBy!] = OCCURRED_AT_DESC) {
          activityFeedItems(first: $first, after: $cursor, condition: $condition, orderBy: $orderBy) {
            edges {
              node {
                ...Activity
                __typename
              }
              __typename
            }
            pageInfo {
              hasNextPage
              endCursor
              __typename
            }
            __typename
          }
        }
        
        fragment Activity on ActivityFeedItem {
          accountId
          aftOriginatorName
          aftTransactionCategory
          aftTransactionType
          amount
          amountSign
          assetQuantity
          assetSymbol
          canonicalId
          currency
          eTransferEmail
          eTransferName
          externalCanonicalId
          groupId
          identityId
          institutionName
          occurredAt
          p2pHandle
          p2pMessage
          spendMerchant
          securityId
          billPayCompanyName
          billPayPayeeNickname
          redactedExternalAccountNumber
          opposingAccountId
          status
          subType
          type
          strikePrice
          contractType
          expiryDate
          chequeNumber
          provisionalCreditAmount
          primaryBlocker
          interestRate
          frequency
          counterAssetSymbol
          rewardProgram
          counterPartyCurrency
          counterPartyCurrencyAmount
          counterPartyName
          fxRate
          fees
          reference
          transferType
          optionStrategy
          rejectionReason
          resolvable
          __typename
        }
        """
        
        condition = {}
        if account_ids:
            condition['accountIds'] = account_ids
        if types:
            condition['types'] = types
        if statuses:
            condition['unifiedStatuses'] = statuses
        if sub_types:
            condition['subTypes'] = sub_types
        if security_ids:
            condition['securityIds'] = security_ids
        if start_date:
            condition['startDate'] = start_date
        if end_date:
            condition['endDate'] = end_date
        
        variables = {
            "first": limit,
            "cursor": cursor,
            "condition": condition if condition else None,
            "orderBy": "OCCURRED_AT_DESC"
        }
        
        result = self.graphql_query("FetchActivityFeedItems", gql_query, variables)
        activity_data = result.get('data', {}).get('activityFeedItems', {})
        edges = activity_data.get('edges', [])
        
        return {
            'items': [edge.get('node', {}) for edge in edges],
            'pageInfo': activity_data.get('pageInfo', {})
        }
    
    def get_pending_orders(self, account_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Get all pending orders for specified accounts.
        
        This is a convenience method that filters for pending buy/sell orders.
        
        Args:
            account_ids: Optional list of account IDs to filter by
            
        Returns:
            List of pending order items
        """
        order_types = [
            'MANAGED_BUY', 'CRYPTO_BUY', 'DIY_BUY', 'OPTIONS_BUY',
            'MANAGED_SELL', 'CRYPTO_SELL', 'DIY_SELL', 'OPTIONS_SELL',
            'OPTIONS_MULTILEG'
        ]
        
        order_subtypes = [
            'FRACTIONAL_ORDER', 'MARKET_ORDER', 'STOP_ORDER', 
            'LIMIT_ORDER', 'STOP_LIMIT_ORDER'
        ]
        
        result = self.get_activities(
            account_ids=account_ids,
            types=order_types,
            statuses=['PENDING'],
            sub_types=order_subtypes,
            limit=100
        )
        
        return result['items']
    
    def get_security_activities(self, security_id: str, account_ids: Optional[List[str]] = None,
                               start_date: Optional[str] = None, end_date: Optional[str] = None,
                               limit: int = 100) -> List[Dict]:
        """
        Get all activities for a specific security (trades, dividends, etc.).
        
        Args:
            security_id: Security ID to filter by
            account_ids: Optional list of account IDs to filter by
            start_date: Optional start date in ISO format (e.g., '2025-10-01T00:00:00.000Z')
            end_date: Optional end date in ISO format (e.g., '2025-10-29T23:59:59.999Z')
            limit: Maximum number of items to return
            
        Returns:
            List of activity items for the security
        """
        result = self.get_activities(
            account_ids=account_ids,
            security_ids=[security_id],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return result['items']
    
    # ==================== Trading ====================
    
    def create_order(self, account_id: str, security_id: str, quantity: int,
                    order_type: str = 'BUY_QUANTITY', execution_type: str = 'LIMIT',
                    limit_price: Optional[float] = None, stop_price: Optional[float] = None,
                    time_in_force: str = 'DAY', open_close: Optional[str] = None,
                    trading_session: Optional[str] = None) -> Dict:
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
            trading_session: Optional - 'EXTENDED' or 'REGULAR'. If not specified, the API will
                           determine appropriate session based on market hours and account capabilities.
            
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
            "timeInForce": time_in_force
        }
        
        if limit_price is not None:
            order_input["limitPrice"] = limit_price
        
        if stop_price is not None:
            order_input["stopPrice"] = stop_price
        
        if open_close is not None:
            order_input["openClose"] = open_close
        
        if trading_session is not None:
            order_input["tradingSession"] = trading_session
        
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
    
    def stop_limit_sell_option(self, account_id: str, option_id: str, quantity: int,
                              limit_price: float, stop_price: float, open_close: str = 'CLOSE') -> Dict:
        """
        Place a stop-limit sell order for an option contract (for stop-loss protection).
        
        Args:
            account_id: Account ID
            option_id: Option security ID
            quantity: Number of contracts
            limit_price: Limit price per contract (price to sell at once stop is triggered)
            stop_price: Stop price (triggers the order when option price falls to this level)
            open_close: 'CLOSE' to close an existing long position
            
        Returns:
            Order creation response
        """
        return self.create_order(account_id, option_id, quantity, 'SELL_QUANTITY', 'STOP_LIMIT',
                               limit_price=limit_price, stop_price=stop_price, open_close=open_close)
    
    def cancel_order(self, external_id: str) -> Dict:
        """
        Cancel an existing order.
        
        Args:
            external_id: The external order ID that was used when creating the order
                        (e.g., 'order-da8e68b0-6a66-4783-b5a6-44e5efc30c3f')
            
        Returns:
            Cancel order response containing the externalId and any errors
            
        Raises:
            Exception if cancellation fails or if there are errors in the response
        """
        gql_query = """
        mutation SoOrdersOrderCancel($cancelOrderRequest: CancelOrderRequest!) {
          orderServiceCancelOrder(cancelOrderRequest: $cancelOrderRequest) {
            externalId
            errors {
              code
              message
              __typename
            }
            __typename
          }
        }
        """
        
        variables = {
            "cancelOrderRequest": {
                "externalId": external_id
            }
        }
        
        result = self.graphql_query("SoOrdersOrderCancel", gql_query, variables)
        cancel_response = result.get('data', {}).get('orderServiceCancelOrder', {})
        
        # Check for errors in the response
        if cancel_response.get('errors'):
            errors = cancel_response['errors']
            error_messages = [f"{err.get('code', 'UNKNOWN')}: {err.get('message', 'No message')}" for err in errors]
            raise Exception(f"Failed to cancel order: {'; '.join(error_messages)}")
        
        return cancel_response
    
    def get_extended_order(self, external_id: str, branch_id: str = 'TR') -> Dict:
        """
        Get extended order details including fill information and status.
        
        This provides detailed information about an order including:
        - Fill prices and quantities
        - Commission and fees
        - Order status (posted, cancelled, pending)
        - Submission and expiry times
        - Exchange rates and net values
        
        Args:
            external_id: The external order ID (e.g., 'order-da8e68b0-6a66-4783-b5a6-44e5efc30c3f')
            branch_id: Branch ID (default: 'TR' for Trade account)
            
        Returns:
            Extended order details dictionary containing:
            - averageFilledPrice: Average price of filled orders
            - filledQuantity: Quantity that has been filled
            - filledCommissionFee: Commission fee for filled portion
            - filledTotalFee: Total fees for filled portion
            - status: Order status ('posted', 'cancelled', 'pending', etc.)
            - limitPrice: Limit price if applicable
            - stopPrice: Stop price if applicable
            - orderType: Type of order (e.g., 'BUY_QUANTITY', 'SELL_QUANTITY')
            - submittedQuantity: Originally submitted quantity
            - submittedNetValue: Net value when submitted
            - timeInForce: Time in force setting ('DAY', 'GTC', etc.)
            - And many other fields
            
        Example:
            order = ws.get_extended_order('order-fc166199-8832-49ba-832d-6a2b0065a2d7')
            print(f"Status: {order['status']}")
            print(f"Filled: {order['filledQuantity']} @ {order['averageFilledPrice']}")
        """
        gql_query = """
        query FetchSoOrdersExtendedOrder($branchId: String!, $externalId: String!) {
          soOrdersExtendedOrder(branchId: $branchId, externalId: $externalId) {
            ...SoOrdersExtendedOrder
            __typename
          }
        }
        
        fragment SoOrdersExtendedOrder on SoOrders_ExtendedOrderResponse {
          averageFilledPrice
          filledExchangeRate
          filledQuantity
          filledCommissionFee
          filledTotalFee
          firstFilledAtUtc
          lastFilledAtUtc
          limitPrice
          openClose
          orderType
          optionMultiplier
          rejectionCause
          rejectionCode
          securityCurrency
          status
          stopPrice
          submittedAtUtc
          submittedExchangeRate
          submittedNetValue
          submittedQuantity
          submittedTotalFee
          timeInForce
          accountId
          canonicalAccountId
          cancellationCutoff
          tradingSession
          expiredAtUtc
          __typename
        }
        """
        
        variables = {
            "branchId": branch_id,
            "externalId": external_id
        }
        
        result = self.graphql_query("FetchSoOrdersExtendedOrder", gql_query, variables)
        return result.get('data', {}).get('soOrdersExtendedOrder', {})
    
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
    
    def subscribe(self, device_id: Optional[str] = None) -> 'WealthsimpleSubscriptions':
        """
        Create a WebSocket subscription client for real-time data streams.
        
        Args:
            device_id: Optional device ID (auto-generated if not provided)
            
        Returns:
            WealthsimpleSubscriptions instance
            
        Raises:
            Exception if websockets library is not installed
            
        Example:
            async with ws.subscribe() as sub:
                async for msg in sub.stream_quotes(['sec-s-xxxxx']):
                    print(f"Quote update: {msg}")
        """
        if not WEBSOCKETS_AVAILABLE:
            raise Exception(
                "WebSocket support requires the 'websockets' library. "
                "Install it with: pip install websockets"
            )
        
        self._ensure_authenticated()
        return WealthsimpleSubscriptions(
            access_token=self.access_token,
            identity_id=self.identity_id,
            device_id=device_id
        )


# ==================== WebSocket Subscriptions ====================

class WealthsimpleSubscriptions:
    """
    WebSocket subscription client for Wealthsimple real-time data streams.
    
    This class handles GraphQL subscriptions over WebSocket using the
    graphql-transport-ws protocol for real-time updates on:
    - Security quotes (real-time price updates)
    - Account activity feed updates
    - Identity and account core updates
    - Custodian account balance changes
    
    Usage:
        async with ws.subscribe() as sub:
            # Stream real-time quotes
            async for msg in sub.stream_quotes(['sec-s-xxxxx']):
                print(f"Price: {msg['payload']['data']['securityQuoteUpdates']['quoteV2']['price']}")
    """
    
    def __init__(self, access_token: str, identity_id: Optional[str] = None, 
                 device_id: Optional[str] = None):
        """
        Initialize subscription client.
        
        Args:
            access_token: OAuth access token
            identity_id: Optional identity ID
            device_id: Optional device ID (auto-generated if not provided)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise Exception(
                "WebSocket support requires the 'websockets' library. "
                "Install it with: pip install websockets"
            )
        
        self.access_token = access_token
        self.identity_id = identity_id
        self.device_id = device_id or uuid.uuid4().hex
        self.ws: Optional[WebSocketClientProtocol] = None
        self._connection_ack_event = asyncio.Event()
        self._subscriptions: Dict[str, asyncio.Queue] = {}
        self._receiver_task: Optional[asyncio.Task] = None
        
        # Possible WebSocket URLs to try
        self.candidate_urls = [
            "wss://realtime-api.wealthsimple.com/subscription",
            "wss://my.wealthsimple.com/graphql",
            "wss://my.wealthsimple.com/subscriptions",
            "wss://my.wealthsimple.com/subscription",
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get WebSocket connection headers."""
        return {
            "Origin": "https://my.wealthsimple.com",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Authorization": f"Bearer {self.access_token}",
            "x-ws-api-version": "12",
            "x-platform-os": "web",
            "x-ws-locale": "en-CA",
            "x-ws-profile": "trade",
        }
    
    async def connect(self) -> None:
        """
        Establish WebSocket connection and initialize the graphql-transport-ws protocol.
        
        Raises:
            Exception if connection fails
        """
        headers = self._get_headers()
        last_exc = None
        
        # Try candidate URLs sequentially
        for url in self.candidate_urls:
            try:
                # Try modern websockets arg first, fall back to older version
                try:
                    self.ws = await websockets.connect(
                        url,
                        additional_headers=headers,
                        subprotocols=["graphql-transport-ws"],
                        max_size=None,
                        open_timeout=20,
                        close_timeout=10,
                    )
                except TypeError:
                    self.ws = await websockets.connect(
                        url,
                        extra_headers=headers,
                        subprotocols=["graphql-transport-ws"],
                        max_size=None,
                        open_timeout=20,
                        close_timeout=10,
                    )
                break
            except Exception as e:
                last_exc = e
                continue
        
        if self.ws is None:
            raise last_exc or RuntimeError("Failed to establish WebSocket connection")
        
        # Send connection_init per GraphQL over WebSocket Protocol
        init_payload = {
            "Authorization": f"Bearer {self.access_token}",
            "x-ws-api-version": "12",
            "x-ws-locale": "en-CA",
            "x-ws-profile": "trade",
            "x-platform-os": "web",
            "x-ws-device-id": self.device_id,
        }
        await self._send_message({"type": "connection_init", "payload": init_payload})
        
        # Start receiver task
        self._receiver_task = asyncio.create_task(self._receiver())
        
        # Wait for connection_ack (best-effort)
        try:
            await asyncio.wait_for(self._connection_ack_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            # Continue anyway, but connection might not be ready
            pass
    
    async def close(self) -> None:
        """Close the WebSocket connection and clean up resources."""
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            try:
                await self.ws.close(code=1000, reason="client shutdown")
            except Exception:
                pass
            self.ws = None
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message over the WebSocket."""
        if not self.ws:
            raise Exception("WebSocket not connected")
        await self.ws.send(json.dumps(message))
    
    async def _receiver(self) -> None:
        """Background task to receive and route WebSocket messages."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "connection_ack":
                        self._connection_ack_event.set()
                    elif msg_type == "next":
                        # Route subscription data to appropriate queue
                        sub_id = data.get("id")
                        if sub_id and sub_id in self._subscriptions:
                            await self._subscriptions[sub_id].put(data)
                    elif msg_type == "error":
                        # Route errors to subscription queues
                        sub_id = data.get("id")
                        if sub_id and sub_id in self._subscriptions:
                            await self._subscriptions[sub_id].put(data)
                    elif msg_type == "complete":
                        # Subscription completed
                        sub_id = data.get("id")
                        if sub_id and sub_id in self._subscriptions:
                            await self._subscriptions[sub_id].put(None)  # Signal completion
                except json.JSONDecodeError:
                    pass  # Ignore non-JSON messages
                except Exception:
                    pass  # Ignore other parsing errors
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # Connection closed or error
    
    async def _subscribe(self, operation_name: str, query: str, 
                        variables: Optional[Dict] = None) -> AsyncIterator[Dict]:
        """
        Internal method to create a subscription and yield messages.
        
        Args:
            operation_name: GraphQL operation name
            query: GraphQL subscription query
            variables: Optional variables
            
        Yields:
            Subscription message dictionaries
        """
        sub_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        self._subscriptions[sub_id] = queue
        
        try:
            # Send subscribe message
            subscribe_msg = {
                "id": sub_id,
                "type": "subscribe",
                "payload": {
                    "operationName": operation_name,
                    "query": query,
                    "variables": variables or {}
                }
            }
            await self._send_message(subscribe_msg)
            
            # Yield messages from queue
            while True:
                msg = await queue.get()
                if msg is None:  # Completion signal
                    break
                yield msg
        finally:
            # Cleanup
            if sub_id in self._subscriptions:
                del self._subscriptions[sub_id]
    
    async def stream_quotes(self, security_ids: List[str], 
                           currency: Optional[str] = None) -> AsyncIterator[Dict]:
        """
        Stream real-time quote updates for one or more securities.
        
        Args:
            security_ids: List of security IDs to subscribe to
            currency: Optional currency filter
            
        Yields:
            Quote update messages with structure:
            {
                "type": "next",
                "id": "subscription-id",
                "payload": {
                    "data": {
                        "securityQuoteUpdates": {
                            "id": "sec-s-xxxxx",
                            "quoteV2": {
                                "price": 150.25,
                                "bid": 150.20,
                                "ask": 150.30,
                                ...
                            }
                        }
                    }
                }
            }
        """
        query = """
        subscription QuoteV2BySecurityIdStream($id: ID!, $currency: Currency = null) {
          securityQuoteUpdates(id: $id) {
            id
            quoteV2(currency: $currency) {
              __typename
              securityId
              ask
              bid
              currency
              price
              sessionPrice
              quotedAsOf
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
                __typename
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
                __typename
              }
            }
            __typename
          }
        }
        """
        
        # Create tasks for each security subscription
        async def stream_single(security_id: str):
            async for msg in self._subscribe(
                "QuoteV2BySecurityIdStream",
                query,
                {"id": security_id, "currency": currency}
            ):
                yield msg
        
        # If only one security, stream directly
        if len(security_ids) == 1:
            async for msg in stream_single(security_ids[0]):
                yield msg
        else:
            # Multiple securities - merge streams
            queues = [stream_single(sid) for sid in security_ids]
            # Note: For simplicity, we stream them sequentially in this implementation
            # A more advanced implementation could merge streams concurrently
            for queue in queues:
                async for msg in queue:
                    yield msg
    
    async def stream_activity_updates(self) -> AsyncIterator[Dict]:
        """
        Stream activity feed updates.
        
        Yields:
            Activity update messages with structure:
            {
                "type": "next",
                "id": "subscription-id",
                "payload": {
                    "data": {
                        "activityFeedUpdates": {
                            "accountId": "tfsa-xxxxx",
                            "activityId": "activity-xxxxx",
                            "updatedAt": "2025-10-31T...",
                            "__typename": "ActivityFeedUpdate"
                        }
                    }
                }
            }
        """
        query = """
        subscription ActivityFeedUpdate {
          activityFeedUpdates {
            accountId
            activityId
            updatedAt
            __typename
          }
        }
        """
        
        async for msg in self._subscribe("ActivityFeedUpdate", query):
            yield msg
    
    async def stream_identity_updates(self, identity_id: Optional[str] = None) -> AsyncIterator[Dict]:
        """
        Stream identity and account core updates.
        
        Args:
            identity_id: Identity ID (uses instance identity_id if not provided)
            
        Yields:
            Identity/account update messages
        """
        if not identity_id:
            identity_id = self.identity_id
        
        if not identity_id:
            raise Exception("identity_id is required for identity updates subscription")
        
        query = """
        subscription IdentityAccountCoreUpdates($identityId: ID!) {
          identityAccountCoreUpdates(identityId: $identityId) {
            __typename
            ... on AccountUpdate {
              id
              eventName
              __typename
            }
            ... on IdentityUpdate {
              id
              eventName
              __typename
            }
          }
        }
        """
        
        async for msg in self._subscribe(
            "IdentityAccountCoreUpdates",
            query,
            {"identityId": identity_id}
        ):
            yield msg
    
    async def stream_balance_changes(self, custodian_account_ids: List[str]) -> AsyncIterator[Dict]:
        """
        Stream custodian account cash balance changes.
        
        Args:
            custodian_account_ids: List of custodian account IDs
            
        Yields:
            Balance change messages
        """
        query = """
        subscription CustodianAccountBalanceChanges($custodianAccountIds: [ID!]!) {
          custodianAccountCashBalanceChanges(custodianAccountIds: $custodianAccountIds) {
            id
            __typename
          }
        }
        """
        
        async for msg in self._subscribe(
            "CustodianAccountBalanceChanges",
            query,
            {"custodianAccountIds": custodian_account_ids}
        ):
            yield msg
    
    async def ping(self) -> None:
        """Send a ping message to keep the connection alive."""
        await self._send_message({"type": "ping", "payload": {}})


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


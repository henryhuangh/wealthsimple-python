#!/usr/bin/env python3
"""
Interactive Wealthsimple Trading Script

This script provides an interactive command-line interface to:
1. Authenticate with Wealthsimple
2. Search for securities
3. View security details and options
4. Place stock or option orders
"""

import os
import sys
import getpass
from datetime import datetime
from typing import Optional, List, Dict
from wealthsimple_v2 import WealthsimpleV2


def get_credentials():
    """Get credentials from environment or prompt user."""
    print("=" * 60)
    print("Wealthsimple Interactive Trading")
    print("=" * 60)
    
    username = os.getenv('WS_USERNAME')
    password = os.getenv('WS_PASSWORD')
    otp = os.getenv('WS_OTP')
    
    # Prompt for credentials if not set in environment
    if not username:
        username = input("\nEnter Wealthsimple username/email: ")
    else:
        print(f"\nUsing username from environment: {username}")
    
    if not password:
        password = getpass.getpass("Enter Wealthsimple password: ")
    else:
        print("Using password from environment")
    
    if not otp:
        otp_input = input("Enter OTP/2FA token (press Enter to skip if 2FA not enabled): ").strip()
        otp = otp_input if otp_input else None
    else:
        print("Using OTP from environment")
    
    return username, password, otp


def search_securities(ws: WealthsimpleV2):
    """Allow user to search for securities."""
    print("\n" + "=" * 60)
    print("SEARCH SECURITIES")
    print("=" * 60)
    
    # Popular symbols as default suggestions
    popular_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    print("\nOptions:")
    print("1. Search by symbol/name")
    print("2. View popular symbols")
    
    choice = input("\nSelect an option (1-2): ").strip()
    
    results = []
    
    if choice == "2":
        print(f"\nFetching popular symbols: {', '.join(popular_symbols)}")
        for symbol in popular_symbols:
            try:
                search_results = ws.search_securities(symbol)
                if search_results:
                    results.append(search_results[0])
            except Exception as e:
                print(f"Warning: Could not fetch {symbol}: {e}")
    else:
        query = input("\nEnter ticker symbol or company name: ").strip()
        if not query:
            print("No query entered.")
            return None
        
        print(f"Searching for '{query}'...")
        try:
            results = ws.search_securities(query)
        except Exception as e:
            print(f"Error searching: {e}")
            return None
    
    if not results:
        print("No results found.")
        return None
    
    # Display results (limit to 5)
    print(f"\nFound {len(results)} result(s):")
    print("-" * 60)
    
    display_results = results[:5]
    for idx, result in enumerate(display_results, 1):
        stock = result.get('stock', {})
        quote = result.get('quoteV2', {})
        
        symbol = stock.get('symbol', 'N/A')
        name = stock.get('name', 'N/A')
        exchange = stock.get('primaryExchange', 'N/A')
        price = quote.get('price', 'N/A')
        
        buyable = "✓" if result.get('buyable') else "✗"
        options = "✓" if result.get('optionsEligible') else "✗"
        
        print(f"{idx}. {symbol} - {name}")
        print(f"   Exchange: {exchange} | Price: ${price}")
        print(f"   Buyable: {buyable} | Options: {options}")
        print()
    
    # Let user select
    selection = input(f"Select a security (1-{len(display_results)}) or 'q' to quit: ").strip()
    
    if selection.lower() == 'q':
        return None
    
    try:
        idx = int(selection) - 1
        if 0 <= idx < len(display_results):
            return display_results[idx]
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Invalid input.")
        return None


def select_account(ws: WealthsimpleV2) -> Optional[str]:
    """Let user select a trading account."""
    print("\n" + "=" * 60)
    print("SELECT ACCOUNT")
    print("=" * 60)
    
    try:
        accounts = ws.get_accounts()
        
        if not accounts:
            print("No accounts found.")
            return None
        
        # Filter to active trading accounts with branch 'TR'
        trading_accounts = [
            acc for acc in accounts 
            if acc.get('status') == 'open' and acc.get('branch') == 'TR'
        ]
        
        if not trading_accounts:
            print("No active trading accounts with branch 'TR' found.")
            return None
        
        print("\nYour trading accounts (branch: TR):")
        for idx, acc in enumerate(trading_accounts, 1):
            nickname = acc.get('nickname', 'N/A')
            acc_type = acc.get('unifiedAccountType', 'N/A')
            acc_id = acc.get('id', 'N/A')
            print(f"{idx}. {nickname} ({acc_type})")
            print(f"   ID: {acc_id}")
        
        selection = input(f"\nSelect account (1-{len(trading_accounts)}): ").strip()
        
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(trading_accounts):
                return trading_accounts[idx]['id']
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input.")
            return None
            
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return None


def display_security_details(ws: WealthsimpleV2, security: Dict):
    """Display detailed security information."""
    print("\n" + "=" * 60)
    print("SECURITY DETAILS")
    print("=" * 60)
    
    security_id = security.get('id')
    
    try:
        details = ws.get_security(security_id)
        
        stock = details.get('stock', {})
        quote = details.get('quoteV2', {})
        fundamentals = details.get('fundamentals', {})
        
        print(f"\nSymbol: {stock.get('symbol', 'N/A')}")
        print(f"Name: {stock.get('name', 'N/A')}")
        print(f"Exchange: {stock.get('primaryExchange', 'N/A')}")
        print(f"\nCurrent Price: ${quote.get('price', 'N/A')}")
        print(f"Bid: ${quote.get('bid', 'N/A')} | Ask: ${quote.get('ask', 'N/A')}")
        
        if 'open' in quote:
            print(f"Open: ${quote.get('open', 'N/A')} | Close: ${quote.get('close', 'N/A')}")
            print(f"High: ${quote.get('high', 'N/A')} | Low: ${quote.get('low', 'N/A')}")
        
        if fundamentals:
            print(f"\nMarket Cap: {fundamentals.get('marketCap', 'N/A')}")
            print(f"P/E Ratio: {fundamentals.get('peRatio', 'N/A')}")
            print(f"52-Week High: ${fundamentals.get('high52Week', 'N/A')}")
            print(f"52-Week Low: ${fundamentals.get('low52Week', 'N/A')}")
        
        print(f"\nBuyable: {'Yes' if details.get('buyable') else 'No'}")
        print(f"Options Eligible: {'Yes' if details.get('optionsEligible') else 'No'}")
        
        return details
        
    except Exception as e:
        print(f"Error fetching security details: {e}")
        return security


def trade_stock(ws: WealthsimpleV2, account_id: str, security: Dict):
    """Handle stock trading flow."""
    print("\n" + "=" * 60)
    print("STOCK TRADING")
    print("=" * 60)
    
    stock = security.get('stock', {})
    quote = security.get('quoteV2', {})
    
    print(f"\nSecurity: {stock.get('symbol')} - {stock.get('name')}")
    print(f"Current Price: ${quote.get('price', 'N/A')}")
    
    # Order type
    print("\nOrder Type:")
    print("1. Buy")
    print("2. Sell")
    
    order_choice = input("Select (1-2): ").strip()
    
    if order_choice == "1":
        order_type = "BUY_QUANTITY"
        action = "buy"
    elif order_choice == "2":
        order_type = "SELL_QUANTITY"
        action = "sell"
    else:
        print("Invalid choice.")
        return
    
    # Execution type
    print("\nExecution Type:")
    print("1. Market Order")
    print("2. Limit Order")
    
    exec_choice = input("Select (1-2): ").strip()
    
    if exec_choice == "1":
        execution_type = "MARKET"
        limit_price = None
    elif exec_choice == "2":
        execution_type = "LIMIT"
        try:
            limit_price = float(input("Enter limit price: $").strip())
        except ValueError:
            print("Invalid price.")
            return
    else:
        print("Invalid choice.")
        return
    
    # Quantity
    try:
        quantity = int(input("Enter quantity (number of shares): ").strip())
        if quantity <= 0:
            print("Quantity must be positive.")
            return
    except ValueError:
        print("Invalid quantity.")
        return
    
    # Confirmation
    print("\n" + "-" * 60)
    print("ORDER SUMMARY")
    print("-" * 60)
    print(f"Action: {action.upper()}")
    print(f"Security: {stock.get('symbol')} - {stock.get('name')}")
    print(f"Quantity: {quantity} shares")
    print(f"Order Type: {execution_type}")
    if limit_price:
        print(f"Limit Price: ${limit_price}")
        print(f"Estimated Total: ${limit_price * quantity:.2f}")
    print(f"Account: {account_id}")
    print("-" * 60)
    
    confirm = input("\nConfirm order? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Order cancelled.")
        return
    
    # Place order
    print("\nPlacing order...")
    try:
        result = ws.create_order(
            account_id=account_id,
            security_id=security['id'],
            quantity=quantity,
            order_type=order_type,
            execution_type=execution_type,
            limit_price=limit_price
        )
        
        errors = result.get('errors', [])
        if errors:
            print("\n✗ Order failed:")
            for error in errors:
                print(f"  - {error.get('code')}: {error.get('message')}")
        else:
            order = result.get('order', {})
            print("\n✓ Order placed successfully!")
            print(f"Order ID: {order.get('orderId')}")
            print(f"Status: {order.get('status')}")
            print(f"Created At: {order.get('createdAt')}")
            
    except Exception as e:
        print(f"\n✗ Error placing order: {e}")


def trade_options(ws: WealthsimpleV2, account_id: str, security: Dict):
    """Handle options trading flow."""
    print("\n" + "=" * 60)
    print("OPTIONS TRADING")
    print("=" * 60)
    
    stock = security.get('stock', {})
    security_id = security.get('id')
    
    print(f"\nUnderlying: {stock.get('symbol')} - {stock.get('name')}")
    
    # Get expiry dates
    print("\nFetching available expiry dates...")
    try:
        expiry_dates = ws.get_option_expiry_dates(security_id)
        
        if not expiry_dates:
            print("No option expiry dates available.")
            return
        
        print(f"\nAvailable expiry dates (showing first 10):")
        display_dates = expiry_dates[:10]
        for idx, date in enumerate(display_dates, 1):
            print(f"{idx}. {date}")
        
        date_selection = input(f"\nSelect expiry date (1-{len(display_dates)}): ").strip()
        
        try:
            date_idx = int(date_selection) - 1
            if 0 <= date_idx < len(display_dates):
                expiry_date = display_dates[date_idx]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return
        
    except Exception as e:
        print(f"Error fetching expiry dates: {e}")
        return
    
    # Option type
    print("\nOption Type:")
    print("1. Call")
    print("2. Put")
    
    option_choice = input("Select (1-2): ").strip()
    
    if option_choice == "1":
        option_type = "CALL"
    elif option_choice == "2":
        option_type = "PUT"
    else:
        print("Invalid choice.")
        return
    
    # Get option chain
    print(f"\nFetching {option_type} option chain for {expiry_date}...")
    try:
        option_chain = ws.get_option_chain(security_id, expiry_date, option_type)
        
        if not option_chain:
            print("No options available for this expiry date.")
            return
        
        # Get current stock price from security quote
        current_price = None
        quote = security.get('quoteV2', {})
        if quote:
            price_str = quote.get('price')
            if price_str:
                try:
                    current_price = float(price_str)
                except (ValueError, TypeError):
                    pass
        
        # If we don't have a current price from security, try to get it from the option chain
        if current_price is None:
            for option in option_chain:
                opt_quote = option.get('quoteV2', {})
                underlying_spot = opt_quote.get('underlyingSpot')
                if underlying_spot:
                    try:
                        current_price = float(underlying_spot)
                        break
                    except (ValueError, TypeError):
                        pass
        
        # Sort option chain by strike price
        sorted_chain = sorted(option_chain, key=lambda x: float(x.get('optionDetails', {}).get('strikePrice', 0)))
        
        # Find the at-the-money strike (closest to current price)
        if current_price is not None:
            atm_idx = 0
            min_diff = float('inf')
            for idx, option in enumerate(sorted_chain):
                strike = float(option.get('optionDetails', {}).get('strikePrice', 0))
                diff = abs(strike - current_price)
                if diff < min_diff:
                    min_diff = diff
                    atm_idx = idx
            
            # Get 5 strikes above and 5 below ATM
            start_idx = max(0, atm_idx - 5)
            end_idx = min(len(sorted_chain), atm_idx + 6)  # +6 to include ATM and 5 above
            display_options = sorted_chain[start_idx:end_idx]
            
            print(f"\nCurrent Stock Price: ${current_price:.2f}")
            print(f"Available strikes (centered around ATM):")
        else:
            # Fallback: show first 10 if we can't determine current price
            display_options = sorted_chain[:10]
            print(f"\nAvailable strikes (showing first 10):")
        
        print("-" * 60)
        for idx, option in enumerate(display_options, 1):
            option_details = option.get('optionDetails', {})
            quote = option.get('quoteV2', {})
            
            strike = option_details.get('strikePrice', 'N/A')
            
            bid = quote.get('bid', 'N/A')
            ask = quote.get('ask', 'N/A')
            last = quote.get('last', 'N/A')
            in_the_money = quote.get('inTheMoney', False)
            
            # Mark ATM strike
            atm_marker = " [ATM]" if current_price and abs(float(strike) - current_price) == min_diff else ""
            itm_marker = " [ITM]" if in_the_money else ""
            
            print(f"{idx}. Strike: ${strike}{atm_marker}{itm_marker}")
            print(f"   Last: ${last} | Bid: ${bid} | Ask: ${ask}")
        
        print("-" * 60)
        option_selection = input(f"\nSelect option (1-{len(display_options)}): ").strip()
        
        try:
            option_idx = int(option_selection) - 1
            if 0 <= option_idx < len(display_options):
                selected_option = display_options[option_idx]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return
        
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Trade direction
    print("\nTrade Action:")
    print("1. Buy to Open (Long)")
    print("2. Sell to Close (Close Long Position)")
    print("3. Sell to Open (Short/Write)")
    print("4. Buy to Close (Close Short Position)")
    
    action_choice = input("Select (1-4): ").strip()
    
    if action_choice == "1":
        order_type = "BUY_QUANTITY"
        open_close = "OPEN"
        action = "Buy to Open"
    elif action_choice == "2":
        order_type = "SELL_QUANTITY"
        open_close = "CLOSE"
        action = "Sell to Close"
    elif action_choice == "3":
        order_type = "SELL_QUANTITY"
        open_close = "OPEN"
        action = "Sell to Open"
    elif action_choice == "4":
        order_type = "BUY_QUANTITY"
        open_close = "CLOSE"
        action = "Buy to Close"
    else:
        print("Invalid choice.")
        return
    
    # Quantity
    try:
        quantity = int(input("Enter quantity (number of contracts): ").strip())
        if quantity <= 0:
            print("Quantity must be positive.")
            return
    except ValueError:
        print("Invalid quantity.")
        return
    
    # Limit price
    try:
        limit_price = float(input("Enter limit price per contract: $").strip())
    except ValueError:
        print("Invalid price.")
        return
    
    # Confirmation
    option_details = selected_option.get('optionDetails', {})
    strike = option_details.get('strikePrice', 'N/A')
    symbol = option_details.get('osiSymbol', 'N/A')
    
    print("\n" + "-" * 60)
    print("ORDER SUMMARY")
    print("-" * 60)
    print(f"Action: {action}")
    print(f"Underlying: {stock.get('symbol')}")
    print(f"Option: {option_type} ${strike} exp {expiry_date}")
    print(f"Symbol: {symbol}")
    print(f"Quantity: {quantity} contracts")
    print(f"Limit Price: ${limit_price} per contract")
    print(f"Estimated Total: ${limit_price * quantity * 100:.2f}")
    print(f"Account: {account_id}")
    print("-" * 60)
    
    confirm = input("\nConfirm order? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Order cancelled.")
        return
    
    # Place order
    print("\nPlacing order...")
    try:
        result = ws.create_order(
            account_id=account_id,
            security_id=selected_option['id'],
            quantity=quantity,
            order_type=order_type,
            execution_type='LIMIT',
            limit_price=limit_price,
            open_close=open_close
        )
        
        errors = result.get('errors', [])
        if errors:
            print("\n✗ Order failed:")
            for error in errors:
                print(f"  - {error.get('code')}: {error.get('message')}")
        else:
            order = result.get('order', {})
            print("\n✓ Order placed successfully!")
            print(f"Order ID: {order.get('orderId')}")
            print(f"Status: {order.get('status')}")
            print(f"Created At: {order.get('createdAt')}")
            
    except Exception as e:
        print(f"\n✗ Error placing order: {e}")


def main():
    """Main interactive trading loop."""
    try:
        # Get credentials
        username, password, otp = get_credentials()
        
        # Authenticate
        print("\nAuthenticating...")
        ws = WealthsimpleV2(username=username, password=password, otp=otp)
        
        print("✓ Authentication successful!")
        print(f"✓ Identity ID: {ws.identity_id}")
        
        while True:
            # Search for security
            security = search_securities(ws)
            if not security:
                retry = input("\nTry another search? (yes/no): ").strip().lower()
                if retry not in ['yes', 'y']:
                    break
                continue
            
            # Show details
            security = display_security_details(ws, security)
            
            # Select account
            account_id = select_account(ws)
            if not account_id:
                print("No account selected.")
                continue
            
            # Choose trading type
            print("\n" + "=" * 60)
            print("SELECT TRADING TYPE")
            print("=" * 60)
            print("1. Trade Stock")
            
            if security.get('optionsEligible'):
                print("2. Trade Options")
                choice = input("\nSelect (1-2): ").strip()
            else:
                print("\nNote: Options trading not available for this security.")
                choice = "1"
            
            if choice == "1":
                trade_stock(ws, account_id, security)
            elif choice == "2" and security.get('optionsEligible'):
                trade_options(ws, account_id, security)
            else:
                print("Invalid choice.")
            
            # Continue?
            print("\n" + "=" * 60)
            another = input("Place another trade? (yes/no): ").strip().lower()
            if another not in ['yes', 'y']:
                break
        
        print("\nThank you for using Wealthsimple Interactive Trading!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


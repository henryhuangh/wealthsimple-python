#!/usr/bin/env python3
import asyncio
import json
import os
import signal
import contextlib
import requests
import getpass
from typing import Dict, Any, Optional, List
from wealthsimple_v2 import WealthsimpleV2


def getenv_str(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _parse_csv_env_list(name: str) -> List[str]:
    v = os.getenv(name)
    if not v:
        return []
    return [s.strip() for s in v.split(",") if s.strip()]


async def connect_and_print_messages(
    access_token: str,
    runtime_seconds: Optional[int] = None,
    subscribe_activity: bool = False,
    identity_id: Optional[str] = None,
    quote_security_ids: Optional[List[str]] = None,
    custodian_account_ids: Optional[List[str]] = None,
) -> None:
    """
    Connect to Wealthsimple WebSocket and print incoming messages.
    Uses the WealthsimpleV2 subscription client.
    """
    try:
        # Create WealthsimpleV2 client using access token
        ws_client = WealthsimpleV2(access_token=access_token)
        
        print("Using subprotocol: graphql-transport-ws")
        print("Connecting to Wealthsimple subscription service...")
        
        # Use the subscription client from the library
        async with ws_client.subscribe() as sub:
            print("✓ WebSocket connection established")
            
            # Create tasks for each subscription type
            tasks = []
            
            # Activity updates subscription
            if subscribe_activity:
                async def handle_activity():
                    print("\n[SUBSCRIPTION] Activity feed updates")
                    async for msg in sub.stream_activity_updates():
                        print(f"\n[RECEIVED] Type: {msg.get('type', 'unknown')}")
                        print(json.dumps(msg, indent=2))
                tasks.append(asyncio.create_task(handle_activity()))
            
            # Identity updates subscription
            if identity_id:
                async def handle_identity():
                    print(f"\n[SUBSCRIPTION] Identity updates for {identity_id}")
                    async for msg in sub.stream_identity_updates(identity_id):
                        print(f"\n[RECEIVED] Type: {msg.get('type', 'unknown')}")
                        print(json.dumps(msg, indent=2))
                tasks.append(asyncio.create_task(handle_identity()))
            
            # Quote subscriptions
            if quote_security_ids:
                async def handle_quotes():
                    print(f"\n[SUBSCRIPTION] Quotes for securities: {', '.join(quote_security_ids)}")
                    async for msg in sub.stream_quotes(quote_security_ids):
                        print(f"\n[RECEIVED] Type: {msg.get('type', 'unknown')}")
                        print(json.dumps(msg, indent=2))
                        
                        # Extract and display quote info for easier reading
                        try:
                            quote_data = msg.get('payload', {}).get('data', {}).get('securityQuoteUpdates', {})
                            if 'quoteV2' in quote_data:
                                quote = quote_data['quoteV2']
                                print(f"  └─ Price: ${quote.get('price')}, Bid: ${quote.get('bid')}, Ask: ${quote.get('ask')}")
                        except Exception:
                            pass
                tasks.append(asyncio.create_task(handle_quotes()))
            
            # Balance changes subscription
            if custodian_account_ids:
                async def handle_balances():
                    print(f"\n[SUBSCRIPTION] Balance changes for accounts: {', '.join(custodian_account_ids)}")
                    async for msg in sub.stream_balance_changes(custodian_account_ids):
                        print(f"\n[RECEIVED] Type: {msg.get('type', 'unknown')}")
                        print(json.dumps(msg, indent=2))
                tasks.append(asyncio.create_task(handle_balances()))
            
            if not tasks:
                print("\n⚠️  No subscriptions requested. Use --activity, --quote-sec-id, etc.")
                return
            
            # Send a ping to keep connection alive
            await asyncio.sleep(0.5)
            await sub.ping()
            print("\n[SENT] Ping message")
            
            print("\n" + "="*60)
            print("Connected. Listening for messages... (Ctrl+C to exit)")
            print("="*60 + "\n")
            
            # Wait for all tasks or timeout
            try:
                if runtime_seconds is None:
                    await asyncio.gather(*tasks)
                else:
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=runtime_seconds)
            except asyncio.TimeoutError:
                print(f"\n✓ Timed out after {runtime_seconds}s; closing...")
            finally:
                # Cancel any remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
                print("\n✓ WebSocket closed")
                
    except Exception as e:
        print(f"✗ Connection error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def get_access_token_from_client() -> str:
    """
    Authenticate to Wealthsimple OAuth v2 API and return access token.
    Uses the same authentication method as test_auth.py.
    """
    # Get credentials from environment variables or prompt
    username = getenv_str("WS_USERNAME")
    password = getenv_str("WS_PASSWORD")
    client_id = getenv_str("WS_CLIENT_ID", "4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa")
    otp = getenv_str("WS_OTP")
    
    # Prompt for credentials if not set in environment
    if not username:
        username = input("Enter Wealthsimple username/email: ")
    if not password:
        password = getpass.getpass("Enter Wealthsimple password: ")
    if not otp:
        otp_input = input("Enter OTP/2FA token (press Enter to skip if 2FA not enabled): ").strip()
        otp = otp_input if otp_input else None
    
    # API endpoint
    url = "https://api.production.wealthsimple.com/v1/oauth/v2/token"
    
    # Prepare the request payload
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "skip_provision": True,
        "scope": "invest.read invest.write trade.read trade.write tax.read tax.write",
        "client_id": client_id
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    # Add OTP to headers if provided
    if otp:
        headers["x-wealthsimple-otp"] = otp
    
    try:
        # Make the authentication request
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            if 'access_token' in response_data:
                return response_data['access_token']
            else:
                raise SystemExit(f"Authentication successful but no access_token in response: {response_data}")
        elif response.status_code == 401:
            raise SystemExit("Authentication failed: Invalid credentials or OTP required")
        else:
            raise SystemExit(f"Authentication failed with status {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Request error during authentication: {e}")


def interactive_select_security_for_quote(access_token: str) -> Optional[str]:
    """
    Interactively search and select a security, returning its security ID.
    Uses WealthsimpleV2 with the provided access token.
    """
    try:
        ws = WealthsimpleV2(access_token=access_token)
    except Exception as e:
        print(f"\n✗ Unable to initialize API client: {e}")
        return None

    print("\n" + "=" * 60)
    print("SUBSCRIBE TO SECURITY QUOTE")
    print("=" * 60)

    query = input("\nEnter ticker symbol or company name: ").strip()
    if not query:
        print("No query entered.")
        return None

    try:
        results = ws.search_securities(query)
    except Exception as e:
        print(f"\n✗ Error searching: {e}")
        return None

    if not results:
        print("No results found.")
        return None

    display_results = results[:5]
    print(f"\nFound {len(results)} result(s) (showing first {len(display_results)}):")
    print("-" * 60)
    for idx, result in enumerate(display_results, 1):
        stock = result.get("stock", {})
        quote = result.get("quoteV2", {})
        symbol = stock.get("symbol", "N/A")
        name = stock.get("name", "N/A")
        exch = stock.get("primaryExchange", "N/A")
        price = quote.get("price", "N/A")
        print(f"{idx}. {symbol} - {name}")
        print(f"   Exchange: {exch} | Price: {price}")

    selection = input(f"\nSelect a security (1-{len(display_results)}) or 'q' to cancel: ").strip()
    if selection.lower() == "q":
        return None
    try:
        sel_idx = int(selection) - 1
        if 0 <= sel_idx < len(display_results):
            chosen = display_results[sel_idx]
            sec_id = chosen.get("id")
            if sec_id:
                print(f"\n✓ Selected: {chosen.get('stock', {}).get('symbol', 'N/A')} ({sec_id})")
                return sec_id
    except ValueError:
        pass
    print("Invalid selection.")
    return None


def main() -> None:
    import argparse
    import contextlib

    parser = argparse.ArgumentParser(description="Connect to Wealthsimple subscription WS and print messages.")
    parser.add_argument(
        "--seconds",
        type=int,
        default=None,
        help="Optional runtime duration in seconds (default: run until interrupted)",
    )
    parser.add_argument(
        "--activity",
        action="store_true",
        help="Subscribe to ActivityFeedUpdate",
    )
    parser.add_argument(
        "--identity-id",
        type=str,
        default=os.getenv("WS_IDENTITY_ID"),
        help="Identity ID for identityAccountCoreUpdates (defaults to WS_IDENTITY_ID or derived from JWT)",
    )
    parser.add_argument(
        "--quote-sec-id",
        action="append",
        default=None,
        help="Security ID to subscribe to QuoteV2BySecurityIdStream (repeatable)",
    )
    parser.add_argument(
        "--quote-sec-ids",
        type=str,
        default=os.getenv("WS_QUOTE_SEC_IDS"),
        help="Comma-separated security IDs for quote subscriptions (alternative to --quote-sec-id)",
    )
    parser.add_argument(
        "--custodian-account-ids",
        type=str,
        default=os.getenv("WS_CUSTODIAN_ACCOUNT_IDS"),
        help="Comma-separated custodian account IDs for balance change subscriptions",
    )
    parser.add_argument(
        "--select-security",
        action="store_true",
        help="Interactively search and select a security to subscribe to quotes",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Resolve and subscribe to a ticker symbol (e.g., AAPL)",
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default=None,
        help="Optional exchange filter for --ticker (e.g., NASDAQ, TSX)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Search term to find securities (use with --pick to choose index)",
    )
    parser.add_argument(
        "--pick",
        type=int,
        default=1,
        help="When using --query, pick the Nth result (default: 1)",
    )
    args = parser.parse_args()

    token = getenv_str("WS_ACCESS_TOKEN") or get_access_token_from_client()

    # Build lists from args/env
    quote_ids: List[str] = []
    if args.quote_sec_id:
        quote_ids.extend(args.quote_sec_id)
    if args.quote_sec_ids:
        quote_ids.extend([s.strip() for s in args.quote_sec_ids.split(",") if s.strip()])
    # Optional interactive selection
    if args.select_security:
        selected = interactive_select_security_for_quote(token)
        if selected:
            quote_ids.append(selected)

    # Non-interactive: resolve from ticker
    if args.ticker:
        try:
            ws = WealthsimpleV2(access_token=token)
            sec_id = ws.get_ticker_id(args.ticker, args.exchange)
            if sec_id:
                quote_ids.append(sec_id)
                print(f"\n✓ Resolved ticker {args.ticker}{'/' + args.exchange if args.exchange else ''} -> {sec_id}")
            else:
                print(f"\n✗ Could not resolve ticker {args.ticker}{' on ' + args.exchange if args.exchange else ''}")
        except Exception as e:
            print(f"\n✗ Error resolving ticker: {e}")

    # Non-interactive: search and pick by index
    if args.query:
        try:
            ws = WealthsimpleV2(access_token=token)
            results = ws.search_securities(args.query)
            if results:
                idx = max(1, args.pick)
                if idx <= len(results):
                    chosen = results[idx - 1]
                    sec_id = chosen.get("id")
                    if sec_id:
                        quote_ids.append(sec_id)
                        sym = chosen.get("stock", {}).get("symbol", "N/A")
                        print(f"\n✓ Selected [{idx}] {sym} -> {sec_id}")
                else:
                    print(f"\n✗ pick index {args.pick} out of range (results: {len(results)})")
            else:
                print(f"\n✗ No results for query '{args.query}'")
        except Exception as e:
            print(f"\n✗ Error searching securities: {e}")
    custodian_ids: List[str] = []
    if args.custodian_account_ids:
        custodian_ids.extend([s.strip() for s in args.custodian_account_ids.split(",") if s.strip()])

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Graceful Ctrl+C
    stop = asyncio.Event()

    def _handle_sigint(*_):
        if not stop.is_set():
            stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_sigint)
        except NotImplementedError:
            pass

    async def runner():
        task = asyncio.create_task(
            connect_and_print_messages(
                token,
                args.seconds,
                subscribe_activity=args.activity,
                identity_id=args.identity_id,
                quote_security_ids=quote_ids or None,
                custodian_account_ids=custodian_ids or None,
            )
        )
        if args.seconds is None:
            await stop.wait()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        else:
            await task

    try:
        loop.run_until_complete(runner())
    finally:
        loop.stop()
        loop.close()


if __name__ == "__main__":
    main()



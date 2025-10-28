import requests
import json
import os
import getpass


def test_wealthsimple_auth():
    """
    Simple test for Wealthsimple OAuth v2 authentication.
    
    This test authenticates to the new Wealthsimple OAuth v2 API.
    Set the following environment variables to test:
    - WS_USERNAME: Your Wealthsimple username/email
    - WS_PASSWORD: Your Wealthsimple password
    - WS_CLIENT_ID: The client ID for the API
    - WS_OTP: (Optional) Your OTP/2FA token if 2FA is enabled
    """
    
    # Get credentials from environment variables or prompt from console
    username = os.getenv('WS_USERNAME')
    password = os.getenv('WS_PASSWORD')
    client_id = os.getenv('WS_CLIENT_ID', '4da53ac2b03225bed1550eba8e4611e086c7b905a3855e6ed12ea08c246758fa')
    otp = os.getenv('WS_OTP')  # Optional, use None if 2FA is not enabled
    
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
    
    print(f"\nTesting authentication to: {url}")
    print(f"Username: {username}")
    print(f"OTP enabled: {otp is not None}")
    
    try:
        # Make the authentication request
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to parse JSON response
        try:
            response_data = response.json()
            print(f"\nResponse Body:")
            print(json.dumps(response_data, indent=2))
            
            # Check if authentication was successful
            if response.status_code == 200:
                print("\n✓ Authentication successful!")
                
                # Check for access token
                if 'access_token' in response_data:
                    print(f"✓ Access token received (length: {len(response_data['access_token'])})")
                if 'refresh_token' in response_data:
                    print(f"✓ Refresh token received (length: {len(response_data['refresh_token'])})")
                if 'token_type' in response_data:
                    print(f"✓ Token type: {response_data['token_type']}")
                if 'expires_in' in response_data:
                    print(f"✓ Token expires in: {response_data['expires_in']} seconds")
                    
                return True
            elif response.status_code == 401:
                print("\n✗ Authentication failed: Invalid credentials or OTP required")
                return False
            else:
                print(f"\n✗ Unexpected status code: {response.status_code}")
                return False
                
        except json.JSONDecodeError:
            print(f"\nRaw Response Text:")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request error: {e}")
        return False


if __name__ == "__main__":
    # Run the test
    result = test_wealthsimple_auth()
    exit(0 if result else 1)


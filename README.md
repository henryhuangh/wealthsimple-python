# wealthsimple-python

## Introduction
The objective of this project is to provide a library of trading functions that enable complete automation with python code. The goal is to have full functionality as the wealthsimple app. Included is the authy module which allow automatic logins even with 2FA enabled.

## Requirements
To use this module, requests must be installed. This can be downloaded with the line 'python -m pip install requests' in windows command prompt or just 'pip install requests' on linux.

## Features
- Basic buy and sell functionality (Stop Limit, Limit, Market, Good till Cancel, Good for Day)
- Real time quotes from TMX, NASDAQ and Yahoo
- Balance retreival

## Documentation

### Setup
Make sure the wealthsimple and authy module is in PATH.
Import the module wealthsimple

`from weathsimple import wealthsimple`

`import authy`

### Login
In order to login, the username and password must be entered into a wealthsimple object.

`ws=wealthsimple('email', 'password')`

If 2FA is enabled, additional steps must be taken for the login process. Go to Two-step verification settings in the wealthsimple app and switch to method to 'Use a dedicated app'. Take note of the code and it can be used to generate a totp_token.

`ws=wealthsimple('email', 'password', MFA=authy.get_totp_token('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX='))`


### Trading

To place a trade, ensure that there is enough funds avaliable

# Hello this is ALGO2
# 
import signal
import requests
from time import sleep
from time import time

from Arbitrage_Trading_Model import VOLUME_COUNT


# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '90P5EPK6'}
TICKERS = []
shutdown = False
POSITION_LIMIT = 0.5
PRICE_LIST = []
MOVING_AVG = []
MOVING_AVG_LIMIT = 0.4
TRADING_FEES = {}
VOLUME_PER = 0.7
SLEEP_TIME = 0.3

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
    pass

# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# this helper method returns the current 'tick' of the running case
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick']
    raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')

# this helper method returns the bid and ask for a given security
def ticker_bid_ask(session, ticker):

# This function will count each and make sure we have a favorable price => return a quantity => return where buy and sell

# Price + moving avg

# This function process moving avg -> give True/False + where should we buy or sell

# Position function -> True, unwind, False

def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        while tick > 0 and tick < 300 and not shutdown:
            # get_book
            # moving_avg => True, buy
            # count function
            # Position

            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()
    
    
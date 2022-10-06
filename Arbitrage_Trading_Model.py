import signal
import requests
from time import sleep
from time import time

## LOGIC TESTED, NEED TO TEST ITS PERFORMANCE WITH HUMAN TRADERS

## I will set the arbitrage trading logic as following:
# We will define two global variables, Volume to count and Volume to Trade. And if we find on both bids and asks side, when we count to volume to count, the price is still favorable, we will submit order in quantity of volume to trade.
# Besides all the basic functions, the codes wil have the following functions:
# ticker_bid_ask(session, ticker):
    # It will first get the bids and asks's price of a ticker on market and counts until fullfill the volume to count
    # It returns two prices for bids and asks seperately: highest bids on market, bid price at volume to count, lowest asks on market, ask price as volume to count

# main():
    # If bid_price at volume to count at market 1 is higher than the ask at market 2, we will submit a buy limit order at the market 2 and sell in market 1
    # We will set the price in a price mixture ratio of highest bids/lowest asks + price at volume to count
    # After experiment, It's better to submit market order as soon as the gap is identified, I Tried ratio of 0.5 and 0.8, more than 40% of limit orders eventually are not fullfilled
    # stopper => (After Experiment, don't sleep work the best as soon as the volume is small enough)
        # I left the function here for future potential use
        # We will set another global variable called bids allowed in one second
        # This stopper will take the above global variable and slow down the speed of order submitting
        # We will put the code to sleep after every judgement no matter a bid submitted or not

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '90P5EPK6'}
shutdown = False
VOLUME_COUNT = 5000
VOLUME_SUBMIT = 3000
# Notes, When 10000 & 5000 => 65,281
# When 20000 & 10000 => 76,026
# When 18000 & 10000 => 78,091
# When 16000 & 10000 => 87,285
# When 14000 & 10000 => 102,163
# When 7000 & 5000 => 116,241/ 120,581 (Most ideal combination)
# When 5000 & 1000 => 57,041

# In class, adjust to safer combinatio and submit smaller order sizes
# With human traders, 5000, 2000 => 70,248.50
# Another trial: 130,201

PRICE_RATIO = 0.5 # The weight highst bid/lowest ask should take
BIDS_IN_1 = 2 # We are allowed to submit this number of orders per second
MARKET1 = 'CRZY_M'
MARKET2 = 'CRZY_A'
SLEEPTIME =0.2

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
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        bid_book = book['bids']
        ask_book = book['asks']
    else: raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    
    highest_bid, lowest_ask = bid_book[0]['price'], ask_book[0]['price']

    volume_got_bid = 0
    bid_book_num = 0
    while abs(volume_got_bid) < VOLUME_COUNT:
        volume_got_bid += bid_book[bid_book_num]['quantity']
        bid_book_num+=1
    bid_at_count = bid_book[bid_book_num-1]['price']

    volume_got_ask = 0
    ask_book_num = 0
    while abs(volume_got_ask) < VOLUME_COUNT:
        volume_got_ask += ask_book[ask_book_num]['quantity']
        ask_book_num+=1
    ask_at_count = ask_book[ask_book_num-1]['price']

    return[highest_bid, bid_at_count, lowest_ask, ask_at_count]

def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        while tick > 0 and tick < 300 and not shutdown:
            
            start_time = time()
            highest_bid1, bid_count1, lowest_ask1, ask_count1 = ticker_bid_ask(s, MARKET1)
            highest_bid2, bid_count2, lowest_ask2, ask_count2 = ticker_bid_ask(s, MARKET2)

            if bid_count1 > ask_count2:
                # ask_price2 = PRICE_RATIO*lowest_ask2+(1-PRICE_RATIO)*ask_count2
                # bid_price1 = PRICE_RATIO*highest_bid1+(1-PRICE_RATIO)*bid_count1
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET2, 'type': 'MARKET', 'quantity': VOLUME_SUBMIT, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET1, 'type': 'MARKET', 'quantity': VOLUME_SUBMIT, 'action': 'SELL'})
                # now_time = time()
                # remaining_time = 1/BIDS_IN_1 - (now_time-start_time)
                sleep(SLEEPTIME)

            if bid_count2 > ask_count1:
                # ask_price1 = PRICE_RATIO*lowest_ask1+(1-PRICE_RATIO)*ask_count1
                # bid_price2 = PRICE_RATIO*highest_bid2+(1-PRICE_RATIO)*bid_count2
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET1, 'type': 'MARKET', 'quantity': VOLUME_SUBMIT,'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET2, 'type': 'MARKET', 'quantity': VOLUME_SUBMIT,'action': 'SELL'})
                # now_time = time()
                # remaining_time = 1/BIDS_IN_1 - (now_time-start_time)
                sleep(SLEEPTIME)
                
            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()
    
    
# CASE 2: Rebates counts toward majority of profits -> frequency
    # Market Trend -> need to work with and without trend
    # Manage inventory risk
    # Where to place the order and time priority
    # If get more than 4 orders, cancel the oldest

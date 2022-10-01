import signal
import requests
from time import sleep
from time import time

## LOGIC TESTED, ENTIRE CODE NOT TESTED as API FUNCTION IS NOT ENABLED
## I will set the arbitrage trading logic as following:
# We will define two global variables, Volume to count and Volume to Trade. And if we find on both bids and asks side, when we count to volume to count, the price is still favorable, we will submit order in quantity of volume to trade.
# Besides all the basic functions, the codes wil have the following functions:
# ticker_bid_ask(session, ticker):
    # It will first get the bids and asks's price of a ticker on market and counts until fullfill the volume to count
    # It returns two prices for bids and asks seperately: highest bids on market, bid price at volume to count, lowest asks on market, ask price as volume to count

# main():
    # If bid_price at volume to count at market 1 is higher than the ask at market 2, we will submit a buy limit order at the market 2 and sell in market 1
    # We will set the price in a price mixture ratio of highest bids/lowest asks + price at volume to count
    # stopper:
        # We will set another global variable called bids allowed in one second
        # This stopper will take the above global variable and slow down the speed of order submitting
        # We will put the code to sleep after every judgement no matter a bid submitted or not

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '837E5K0H'}
shutdown = False
VOLUME_COUNT = 5000
VOLUME_SUBMIT = 1000
PRICE_RATIO = 0.8 # The weight highst bid/lowest ask should take
BIDS_IN_1 = 2 # We are allowed to submit this number of orders per second
MARKET1 = 'CRZY_M'
MARKET2 = 'CRZY_A'

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

        while tick > 5 and tick < 295 and not shutdown:
            
            start_time = time()
            highest_bid1, bid_count1, lowest_ask1, ask_count1 = ticker_bid_ask(s, MARKET1)
            highest_bid2, bid_count2, lowest_ask2, ask_count2 = ticker_bid_ask(s, MARKET2)

            if bid_count1 > ask_count2:
                ask_price2 = PRICE_RATIO*lowest_ask2+(1-PRICE_RATIO)*ask_count2
                bid_price1 = PRICE_RATIO*highest_bid1+(1-PRICE_RATIO)*bid_count1
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET2, 'type': 'LIMIT', 'quantity': VOLUME_SUBMIT, 'price':ask_price2, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET1, 'type': 'LIMIT', 'quantity': VOLUME_SUBMIT, 'price':bid_price1, 'action': 'SELL'})
                now_time = time()
                remaining_time = 1/BIDS_IN_1 - (now_time-start_time)
                sleep((remaining_time))

            if bid_count2 > ask_count1:
                ask_price1 = PRICE_RATIO*lowest_ask1+(1-PRICE_RATIO)*ask_count1
                bid_price2 = PRICE_RATIO*highest_bid2+(1-PRICE_RATIO)*bid_count2
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET1, 'type': 'LIMIT', 'quantity': VOLUME_SUBMIT, 'price':ask_price1,'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': MARKET2, 'type': 'LIMIT', 'quantity': VOLUME_SUBMIT, 'price':bid_price2,'action': 'SELL'})
                now_time = time()
                remaining_time = 1/BIDS_IN_1 - (now_time-start_time)
                sleep((remaining_time))
                
            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()
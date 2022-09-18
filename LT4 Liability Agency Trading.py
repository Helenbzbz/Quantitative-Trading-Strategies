import os
import functools
import operator
import itertools
from time import sleep
import signal
import requests

## Below are pseudo codes I wrote for this code
# I know it's ideal if we can combine the use of market and limit order together to take advntage of the compensation fee from alternative market. However, I can't think of a safe way to add the limit order while ensuring the orders can be executed.
# Therefore, I will use market order only. For ensuring all the orders can be executed, accept command won't be sent unless there is a 20% volume safe buffer for the stock (there should be 20% more volume price lower/higher than the offered price).
# The function that will be here are:
# 1. get_ticker() to get the current time
# 2. read tender to get the quantity, stock ticker, offered price
# 3. a.Get the current book order quantity and price by order. b.Following the logic, add up all the orders on buy/sell side until the volume cover until 120% of the requested volume. Check the price, if the price is favorable, we accept the order))
# 4. Buy/Sell command. If the command 3 returns a true, 4 will execute the orders as market order immediately

class ApiException(Exception):
    pass

# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# set your API key to authenticate to the RIT client
API_KEY = {'X-API-Key': '837E5K0H'}
shutdown = False

# Function 1. This helper method returns the current 'tick' of the running case
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    case = resp.json()
    return case['tick']

# Function 2. This function read the tender and get quantity
def get_tender(session):
    try:
        resp = session.get('http://localhost:9999/v1/tenders')
        return resp.json()[0]
    except: return []

# Function 3.a. Get current book order quantity and price by order
def get_book_order(session, tender_info):
    ticker = (tender_info['ticker'])
    resp = session.get(f'http://localhost:9999/v1/securities/book?ticker={ticker}')
    if tender_info['action'] == 'BUY':
        print((resp.json())['asks'])
    else:
        print((resp.json())['bids'])

# Function 3.b. Add up all the orders returned by 3.a and check if the requested price is favorable
# def tender_decision()

# this is the main method containing the actual order routing logic
def main():
    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)

        # while the time is <= 300
        while tick <= 300:
            # get current tender
            tender_info = get_tender(s)

            # if there is a valid tendr, get the book_order
            if tender_info != []:
                get_book_order(s, tender_info)

            # refresh the case time. THIS IS IMPORTANT FOR THE WHILE LOOP
            tick = get_tick(s)

# this calls the main() method when you type 'python lt3.py' into the command prompt
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()

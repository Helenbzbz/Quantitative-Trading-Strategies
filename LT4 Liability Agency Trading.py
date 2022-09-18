import os
import functools
import operator
import itertools
from time import sleep
import signal
import requests

## Below are pseudo codes I wrote for this code
# I know it's ideal if we can combine the use of market and limit order together to take advntage of the compensation fee from alternative market. However, I can't think of a safe way to add the limit order while ensuring the orders can be executed.
# Therefore, I will use market order only. For ensuring all the orders can be executed, accept command won't be sent unless there is a 20% price safe buffer for the stock (there should be 20% price lower/higher at the offered volume).
# The function that will be here are:
# 1. get_ticker() to get the current time
# 2. read tender to get the quantity, stock ticker, offered price
# 3. a.Get the current book order quantity and price by order. b.Following the logic, add up all the orders on buy/sell side until the volume cover the requested volume.
    # I think a better way is to take order from both alternative and main market. As soon as the two markets add up at a price meet the volume and also gives 120% favorable price, we should accept the order
    # In considering both market, we should for sure add the transaction fee in price comparison
    # I don't think we need to decline the order in any situation. we ca take the 30 seconds window as an opportunity, if the price on the market is not favarable, we can hold it, get the tick again and rerun to see if the market comes towards a favorable position. If the time passed, the order will be declind automatically.
# 4. Buy/Sell command. If the command 3 returns a true, 4 will execute the orders as market order immediately


class ApiException(Exception):
    pass

# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# We define the global variable here
API_KEY = {'X-API-Key': '837E5K0H'}
MARKET_TICKER = {
    'main':'_M',
    'alternative1':'_A'
    }
SAFE_BUFFER = 1.2
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

# Function 3-1. Get current book order quantity and price form both markets (let's experiment with taking the first 20 orders first)
# The order limit might have to change after in class parctice when we have human traders
## !! when use 'bid' as key return people who want to buy; when use 'asks' as key return people who want to sell
def get_book_order(session, tender_info):
    ticker = (tender_info['ticker'])
    main_ticker = ticker[0:4]+MARKET_TICKER['main']
    alternative_ticker = ticker[0:4]+MARKET_TICKER['alternative1']
    main_resp = session.get(f'http://localhost:9999/v1/securities/book?ticker={main_ticker}')
    alternative_resp = session.get(f'http://localhost:9999/v1/securities/book?ticker={alternative_ticker}')
    tender_action = tender_info['action']
    if tender_action == 'BUY':
        main_book = (main_resp.json()['asks'])
        alternative_book = (alternative_resp.json()['asks'])
    else:
        main_book = (main_resp.json()['bids'])
        alternative_book = (alternative_resp.json()['bids'])

    volume = accept_decision(main_book, alternative_book, tender_info)
    decision = {
        'main_ticker':main_ticker,
        'main_volume': volume[0],
        'alternative_ticker':alternative_ticker,
        'alternative_volume':volume[1],
        'tender_action': tender_action,
        'tender_id':tender_info['tender_id']}
    return decision

# Function 3-2. Taking main_book and alternative_book from function 3-1 as the input. 
# This function will start form the first item in both books, choose the one with favorable price until: 1. reach the volume 2. the price is no longer favorable comparing to 1.2* given price
# The function will return 2 integers representing how much we should purchase from each of the markets.
# If the function returns [0,0], means the current market condition is not favorable and we should not accept the tender. We can hold the tender and wait
def accept_decision(main_book,alternative_book,tender_info):
    m = 0
    a = 0
    negative_factor = 1
    given_price = tender_info['price']*SAFE_BUFFER
    given_quantity = tender_info['quantity']
    at_main = 0
    at_alternative = 0
    total_price = 0

    if tender_info['action'] == 'SELL': negative_factor = -1
    while m < len(main_book) and a < len(alternative_book) and at_main + at_alternative < given_quantity:
        main = main_book[m]
        alternative = alternative_book[a]
        if main['price']*negative_factor <= alternative['price']*negative_factor:
            quantity = min(main['quantity'],(given_quantity-at_main-at_alternative))
            current_price = main['price']
            new_vwap = (current_price*quantity+total_price)/(quantity+at_main+at_alternative)
            if new_vwap*negative_factor > given_price*negative_factor: 
                return([0,0])
            else:
                at_main += quantity
                total_price += quantity*current_price
                m += 1
        else:
            quantity = min(alternative['quantity'],(given_quantity-at_main-at_alternative))
            current_price = alternative['price']
            new_vwap = (current_price*quantity+total_price)/(quantity+at_main+at_alternative)
            if new_vwap*negative_factor > given_price*negative_factor: 
                return([0,0])
            else:
                at_alternative += quantity
                total_price += quantity*current_price
                a += 1
    if at_main+at_alternative == given_quantity: return [at_main,at_alternative]
    else: return [0,0]
    
# Function 4. This function will accpet the tender and send out market order based on the decision returned by the function 3
def order_sender(decision,session):
    if decision['main_volume'] + decision['alternative_volume'] == 0: return
    tender_id = decision['tender_id']
    session.post(f'http://localhost:9999/v1/tenders/{tender_id}')
    session.post(f'http://localhost:9999/v1/orders', 
        params = {
            'ticker':(decision['main_ticker']), 
            'type':'MARKET', 
            'quantity':(decision['main_volume']),
            'action':(decision['tender_action'])
        })
    session.post(f'http://localhost:9999/v1/orders', 
        params = {
            'ticker':(decision['alternative_ticker']), 
            'type':'MARKET', 
            'quantity':(decision['alternative_volume']),
            'action':(decision['tender_action'])
        })

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
                decision = get_book_order(s, tender_info)
                order_sender(decision, s)

            # refresh the case time. THIS IS IMPORTANT FOR THE WHILE LOOP
            tick = get_tick(s)

# this calls the main() method when you type 'python lt3.py' into the command prompt
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()

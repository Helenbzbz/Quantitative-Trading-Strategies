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
TRANSACTION_FEE = {
    'main_buy': 0.02,
    'alternative_buy': 0.01,
    'alternative_sell':0.005,
    'main_sell':0.00
}
TOTAL_TIME= 300
shutdown = False

# Function 1. This helper method returns the current 'tick' of the running case
# TESTED
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    case = resp.json()
    return case['tick']

# Function 2. This function gets all the active tender information from the API
# We assume all the tender will be either accepted or waited until decline and there should only be one active tender at one time
# TESTED
def get_tender(session):
    try:
        resp = session.get('http://localhost:9999/v1/tenders')
        return (resp.json()[0])
    except: return []

# Function 3-1. Get current book order quantity and price form both markets (We will experiment with taking the first 20 orders from the book, this limit can definitely be adjsuted after testing)
# The function takes session and tender info returned from function 2 as the input
# The function will proces the tender info and get the frist 20 book orders from both main market and alternative market in either 'bids' or 'asks' side match the tender request
    # If the tender request is BUY, we will look at 'asks' on the book orders and vice versa
# The function will call function 3-2 accept_decision within.
# TESTED
def get_book_order(session, tender_info):
    ticker = (tender_info['ticker'])
    main_ticker = ticker[0:4]+MARKET_TICKER['main']
    alternative_ticker = ticker[0:4]+MARKET_TICKER['alternative1']
    main_resp = session.get(f'http://localhost:9999/v1/securities/book?ticker={main_ticker}')
    alternative_resp = session.get(f'http://localhost:9999/v1/securities/book?ticker={alternative_ticker}')
    tender_action = tender_info['action']
    if tender_action == 'SELL':
        main_book = (main_resp.json()['asks'])
        alternative_book = (alternative_resp.json()['asks'])
    else:
        main_book = (main_resp.json()['bids'])
        alternative_book = (alternative_resp.json()['bids'])

    volume = accept_decision(main_book, alternative_book, tender_info)
    if tender_action == 'BUY': tender_action = 'SELL'
    else: tender_action = 'BUY'
    decision = {
        'main_ticker':main_ticker,
        'main_volume': volume[0],
        'alternative_ticker':alternative_ticker,
        'alternative_volume':volume[1],
        'tender_action': tender_action,
        'tender_id':tender_info['tender_id']}
    return decision

# Function 3-2. Taking main_book, alternative_book, and tender_info from function 3-1 as the input. 
# This function will start form the first item in both books, choose the one with favorable price until: 1. reach the volume 2. the new vwap price is no longer favorable comparing to 1.2* tender price
# The function will return 2 integers representing how much we should purchase from each of the markets: main and alternative
# If the function returns [0,0], means the current market condition is not favorable and we should not accept the tender. We can hold the tender and wait
# The output will be formated as a dictionary back in Function 3-1 which includes all the necessary information to hold the tender/ accept the tender & execute two market orders in alternative and main markets
def accept_decision(main_book,alternative_book,tender_info):

    # This part will return the appropriate transaction fee based on order type
    if tender_info['action'] == 'BUY':
        main_fee = TRANSACTION_FEE['main_sell']
        alternative_fee = TRANSACTION_FEE['alternative_sell']
    else:
        main_fee = TRANSACTION_FEE['main_buy']
        alternative_fee = TRANSACTION_FEE['alternative_buy']

    # This part define the price and quantity requested in tender, initialize the quantity we purchase from two markets and total price paid for vwap calculation
    given_price = tender_info['price']*SAFE_BUFFER
    given_quantity = tender_info['quantity']
    at_main = 0
    at_alternative = 0
    total_price = 0

    # This part define a negative factor.
    # When order type is BUY, negative factor is 1: we want: price_on_market_asks < offered in tender
    # When order type is SELL, negative factor is -1: we want: price_on_market_bids > offered in tender => price_on_market_bids *-1 < offered in tender*-1
    # Through using negative factor we can use one comparision for both buy and sell
    negative_factor = 1
    if tender_info['action'] == 'BUY': negative_factor = -1

    # Initialize index to read main_book and alternative_book orders
    m = 0
    a = 0

    while m < len(main_book) and a < len(alternative_book) and at_main + at_alternative < given_quantity:
        
        # This part read the order by indexs and their price after negative factor and transction fee
        main = main_book[m]
        alternative = alternative_book[a]
        main_price_book = main['price']*negative_factor-main_fee
        alternative_price_book = alternative['price']*negative_factor-alternative_fee

        # Compare main price and alternative price
        if  main_price_book <= alternative_price_book:
            # Get quantity and calculate vwap after add this volume and price
            quantity = min(main['quantity'],(given_quantity-at_main-at_alternative))
            new_vwap = (main_price_book*quantity+total_price)/(quantity+at_main+at_alternative)
            # If price is no longer favorable
            if new_vwap > given_price*negative_factor: 
                return([0,0])
            # If price is favorable
            else:
                at_main += quantity
                total_price += quantity*main_price_book
                m += 1
        # Same logic as the logic for main maket
        else:
            quantity = min(alternative['quantity'],(given_quantity-at_main-at_alternative))
            new_vwap = (alternative_price_book*quantity+total_price)/(quantity+at_main+at_alternative)
            if new_vwap > given_price*negative_factor: 
                return([0,0])
            else:
                at_alternative += quantity
                total_price += quantity*alternative_price_book
                a += 1
    # See if we have enough volume to cover the tender
    if at_main+at_alternative == given_quantity: return [at_main,at_alternative]
    else: return [0,0]
    
# Function 4. This function takes the input from Function 3 which is a dictionary with all the needed information
# This function will accpet the tender and send out market order based on the decision
# TO-DO: For Some reason, tender command works while the order commands does not
def order_sender(decision,session):
    if decision['main_volume'] + decision['alternative_volume'] == 0: return
    tender_id = decision['tender_id']
    # Accept the tender
    session.post(f'http://localhost:9999/v1/tenders/{tender_id}')

    # Execute the main market orders
    main_params = {'ticker':(decision['main_ticker']), 
            'type':'MARKET', 
            'quantity':(decision['main_volume']),
            'action':(decision['tender_action'])}
    session.post('http://localhost:9999/v1/orders', params=main_params)

    # Execute alternative market orders
    alter_params = {
            'ticker':(decision['alternative_ticker']), 
            'type':'MARKET', 
            'quantity':(decision['alternative_volume']),
            'action':(decision['tender_action'])}
    session.post('http://localhost:9999/v1/orders', params=alter_params)
    
# This is the main method containing the actual order routing logic
# TO-DO: OVERALL PERFORMANCE NOT TESTED due to server issue
# TO-DO: TEST NEED when we have multiple human traders
# TO-DO: NEED to adjuste maximum book order request limits + price safer buffer based on real performance
def main():
    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)

        # while the time is <= total_time
        while tick <= TOTAL_TIME:
            # get current tender
            tender_info = get_tender(s)
            
            #if there is a valid tender, get the book_order and run order_sender
            if tender_info != []:
                decision = get_book_order(s, tender_info)
                order_sender(decision, s)

            # refresh the case time. THIS IS IMPORTANT FOR THE WHILE LOOP
            tick = get_tick(s)

# this calls the main() method when you type 'python lt3.py' into the command prompt
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
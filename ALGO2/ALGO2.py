# Hello this is ALGO2

import signal
import requests
from time import sleep
from time import time

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '837E5K0H'}
TICKERS = []
shutdown = False
TRADING_FEES = {
    'CNR':-0.005,
    'ALGO': -0.005,
    'RY':-0.005,
    'AC':-0.005
}
# RY is more liquid and give up the other markets
MAXIMUM_VOLUME = 3000
TIMETOCANCEL = 5 # It was 5 for ALGO2e
SPREAD = 0.05
SLEEP_TIME = 0.3
LONGER_MA = 15
SHORTER_MA = 8

## VARIABLES FOR POSITION BALANCE
LIMIT = 25000
# When the volume approaches 60% of the volume limit, we submit one market order on the opposite side
PERCENTAGE_TO_MKT = 0.6
VOLUME_TO_MKT = 3000
# When the volume approaches 30% of the volume limit, we submit one limit order on the opposite side
PERCENTAGE_TO_LIMIT = 0.3
VOLUME_TO_LIMIT = 2000


# Different liquidity

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
    pass

# This function will use the security history function to tell if there is a market trend or not
# Moving average crosses -> 5-MA with 10-MA
# ANON orders -> More on one side, total quantity; last 5 orders where are they placed
# Use the normal code as default and add the trend if it's very strong

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
    return book['bids'][0], book['asks'][0]

def algo_judgement(session,ticker):
    bids, asks = ticker_bid_ask(session,ticker)
    # if bids['price']>asks['price']-SPREAD-2*TRADING_FEES[ticker]:
    # We can add if statement here to filter out non-ANON trader
    quantity_a = asks['quantity']
    quantity_b = bids['quantity']
    best_bid = bids['price']
    best_ask = asks['price']
    return [ticker,best_bid,best_ask,min(quantity_a,quantity_b,MAXIMUM_VOLUME)]
    # return False
    
#Obtaining orders  
def orders(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/orders', params = payload)
    order = resp.json()
    return order

#Cancelation
def cancelation(session, ticker,tick):
    order = orders(session,ticker)
    if order != []:
        for item in order:
            time_order = item["tick"]
            order_id = item['order_id']
            if tick - TIMETOCANCEL > time_order:
                session.delete('http://localhost:9999/v1/orders/{}'.format(order_id))

# Get Position
def get_position(session, ticker):
    resp = session.get('http://localhost:9999/v1/securities')
    positions = resp.json()
    for position in positions:
        if position['ticker'] == ticker:
            return position['position']
    return False

# Balance Book
def book_balance(session, ticker):
    current_position = get_position(session, ticker)
    print(current_position)
    resp = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":ticker})
    prices = resp.json()
    last_price = prices[0]['close']
    print(last_price)
    if current_position > LIMIT*PERCENTAGE_TO_MKT:
        session.post('http://localhost:9999/v1/orders', params={'ticker': {ticker}, 'type': 'MARKET', 
        'quantity': VOLUME_TO_MKT, 'action': 'SELL'})
        print('Blanace')
    if current_position < -LIMIT*PERCENTAGE_TO_MKT:
        session.post('http://localhost:9999/v1/orders', params={'ticker': {ticker}, 'type': 'MARKET', 
        'quantity': VOLUME_TO_MKT, 'action': 'BUY'})
        print('Blanace')
    if current_position > LIMIT*PERCENTAGE_TO_LIMIT:
        session.post('http://localhost:9999/v1/orders', params={'ticker': {ticker}, 'type': 'MARKET', 
        'quantity': VOLUME_TO_LIMIT, 'action': 'SELL'})
    if current_position < -LIMIT*PERCENTAGE_TO_LIMIT:
        session.post('http://localhost:9999/v1/orders', params={'ticker': {ticker}, 'type': 'MARKET', 
        'quantity': VOLUME_TO_LIMIT, 'action': 'BUY'})

def market_trend(session,ticker,tick):
    if tick < LONGER_MA: return False
    resp1 = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":ticker,"limit":LONGER_MA})
    resp2 = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":ticker,"limit":SHORTER_MA})
    prices1 = resp1.json()
    prices2 = resp2.json()
    total_price1 = 0
    total_price2 = 0
    for price in prices1:
        total_price1+= price['close']
    for price in prices2:
        total_price2+= price['close']
    LONGMA = total_price1/LONGER_MA
    SHORTMA = total_price2/SHORTER_MA
    if LONGMA > SHORTMA: return 'LONG'
    elif LONGMA < SHORTMA: return 'SHORT'
    else: return 'EQUAL'

def trading_function_ALGO(ticker):
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)
        pre_market_direction = False
        positive_spread = 0
        negative_spread = 0
        while tick > 0 and tick < 300 and not shutdown:
            # curr_market_direction = market_trend(s, ticker,tick)
            # if pre_market_direction:
            #     if curr_market_direction == 'SHORT':
            #         positive_spread = 0.02
            #         print(positive_spread)
            #     elif curr_market_direction == 'LONG':
            #         negative_spread = -0.02
            #         print(negative_spread)
            # pre_market_direction = curr_market_direction

            decision = algo_judgement(s,ticker)
            if decision:
                quantity = decision[3]
                ask_price = decision[2]
                bid_price = decision[1]
                spread = (ask_price-bid_price)/3
                mid_point = (ask_price+bid_price)/2
                s.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'BUY','price':bid_price})
                s.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'SELL','price':ask_price})
            sleep(SLEEP_TIME)
            tick = get_tick(s)
            cancelation(s,ticker,tick)
            book_balance(s,ticker)
            book_balance(s,ticker)

            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            tick = get_tick(s)


def main():
    trading_function_ALGO('AC')

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()

# Algo2 be as aggressive as possible, the ALGO 2 might be a little bit too conservative
# For Algo2 we can make the spread small or trade with our selves
# -> Trade with oneself
# Get securities, position => 80% market order instead; if it's 50% limit order

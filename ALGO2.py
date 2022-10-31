# Hello this is ALGO2

import signal
import requests
from time import sleep
from time import time

from Arbitrage_Trading_Model import VOLUME_COUNT

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '837E5K0H'}
TICKERS = []
shutdown = False
POSITION_LIMIT = 0.5
TRADING_FEES = {'CNR':-0.005}
SPREAD = 0.1
SLEEP_TIME = 0.3
NUM_MA = 3
MA = 4

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
    pass

# This function will use the security history function to tell if there is a market trend or not
# Moving average crosses -> 5-MA with 10-MA
# ANON orders -> More on one side, total quantity; last 5 orders where are they placed
# Use the normal code as default and add the trend if it's very strong
def market_trend(session, tick, ticker):
    if tick < MA+NUM_MA: return False
    last_prices = []
    resp = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":ticker,"limit":MA+NUM_MA})
    prices = resp.json()
    for price in prices:
        last_prices.append(price['close'])
    moving_average1 = []
    for i in range (0,NUM_MA):
        moving_average1.append(sum(last_prices[i:i+MA])/MA)
    moving_avg_change = []
    for i in range (1,NUM_MA):
        change = moving_average1[i]-moving_average1[i-1]
        moving_avg_change.append(change)
    print(moving_avg_change)
    pre = 0
    for change in moving_avg_change:
        if pre == 0:
            pre = change
        else:
            if change != 0 and pre/change < 0: return 'False'
            else:
                pre = change
    if pre > 0: return 'Pos'
    else: return 'neg'

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
    if bids['price']>asks['price']-SPREAD-2*TRADING_FEES[ticker]:
        # We can add if statement here to filter out non-ANON trader
        quantity_a = asks['quantity']
        quantity_b = bids['quantity']
        best_bid = bids['price']
        best_ask = asks['price']
        return [ticker,best_bid,best_ask,min(quantity_a,quantity_b,5000)]
    return False
    
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
            if tick - 10 > time_order:
                # session.delete('http://localhost:9999/v1/commands/cancel', params = {'order_id':order_id})
                session.delete('http://localhost:9999/v1/orders/{}'.format(order_id))

# Position function -> True, unwind, False
def position(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities')
    if resp.ok:
        position = resp.json
    return position


def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        while tick > 0 and tick < 300 and not shutdown:
            # trend = market_trend(s,tick,"ALGO")
            # print(tick,trend)
            decision = algo_judgement(s,"CNR")
            if decision:
                quantity = decision[3]
                ask_price = decision[2]
                bid_price = decision[1]
                mid_point = (ask_price+bid_price)/2
                s.post('http://localhost:9999/v1/orders', params={'ticker': "CNR", 'type': 'LIMIT', 'quantity': quantity, 'action': 'BUY','price':mid_point-SPREAD/2})
                s.post('http://localhost:9999/v1/orders', params={'ticker': "CNR", 'type': 'LIMIT', 'quantity': quantity, 'action': 'SELL','price':mid_point+SPREAD/2})
                
            cancelation(s,'CNR',tick)
            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            sleep(0.5)
            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()

# Algo2 be as aggressive as possible, the ALGO 2 might be a little bit too conservative
# For Algo2 we can make the spread small or trade with our selves
# -> Trade with oneself
# Get securities, position => 80% market order instead; if it's 50% limit order
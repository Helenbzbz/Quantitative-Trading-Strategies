# Hello this is ALGO2
from hashlib import new
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
NUM_MA = 8
MA = 10

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
<<<<<<< Updated upstream
def ticker_bid_ask(session, ticker):
    payload = {'ticker': ticker} 
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload) 
    if resp.ok: 
        book = resp.json() 
    return book

# This function will count each and make sure we have a favorable price => return a quantity => return where buy and sell

#Obtaining orders  
def orders(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/orders', params = payload)
    order = resp.json()
    return order

#Cancelation
def cancelation(session, ticker,tick):
    order = orders(session,tick)
    if order != []:
        for item in order:
            time_order = item["tick"]
            order_id = item['order_id']
            if tick - 10 > time_order:
                session.post('http://localhost:9999/v1/commands/cancel/', params = {'order_id':order_id})
                print(order_id)
# Price + moving avg

# This function process moving avg -> give True/False + where should we buy or sell

=======
# def ticker_bid_ask(session, ticker):

# This function will count each and make sure we have a favorable price => return a quantity => return where buy and sell

# This function will use the security history function to tell if there is a market trend or not
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
    print(moving_average1)
    pre_change = moving_average1[1]-moving_average1[0]
    for i in range (2,NUM_MA-MA):
        new_change = moving_average1[i]-moving_average1[i-1]
        if pre_change >0 and new_change < 0:  return False
        elif pre_change <0 and new_change > 0:  return False
        pre_change = new_change
    if pre_change > 0:
        return 'Positive'
    else: return 'Negative'
            
    
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            ticker_bid_ask(s,"CNR")
            position(s, "CNR")
            cancelation(s, "CNR",tick)
            # moving_avg => True, buy
            # count function
            # Position

=======
            trend = market_trend(s,tick,"ALGO")
            print(tick,trend)
            if trend == 'Positive': 
                s.post('http://localhost:9999/v1/orders', params={'ticker': "ALGO", 'type': 'MARKET', 'quantity': 1000, 'action': 'BUY'})
                sleep(1)
                s.post('http://localhost:9999/v1/orders', params={'ticker': "ALGO", 'type': 'MARKET', 'quantity': 1000, 'action': 'SELL'})
            elif trend == 'Negative': 
                s.post('http://localhost:9999/v1/orders', params={'ticker': "ALGO", 'type': 'MARKET', 'quantity': 1000, 'action': 'SELL'})
                sleep(1)
                s.post('http://localhost:9999/v1/orders', params={'ticker': "ALGO", 'type': 'MARKET', 'quantity': 1000, 'action': 'BUY'})
            else:
                sleep(1)
            
>>>>>>> Stashed changes
            # IMPORTANT to update the tick at the end of the loop to check that the algorithm should still run or not
            sleep(1)
            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()
    
    
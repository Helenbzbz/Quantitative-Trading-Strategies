# Hello this is Community 5

import signal
import requests
from time import sleep
from time import time

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '837E5K0H'}
shutdown = False

# Definition for the future contract section
VOLUME_TRADE_FOR_FUTURE = 150
TICK_FOR_PRICE_CHANGE = 25
TICK_TO_KEEP_FUTURE = 50
PRICE_THRESHOLD_TO_REACT = 0.4
# As soon as the following opposite price change achieve this percentage of the previous, we will exit
PERCENTAGE_TO_EXIT = 0.7 

# Definition for the fundamental news trade
VOLUME_TRADE_FOR_NEWS = 100
TICK_TO_KEEP_NEWS = 8
TICKER_FOR_NEWS = "CL-2F"

# Definition for the Transportation section
UNIT_TRADE_FOR_TRANS = 7
THRESHOLD_TO_TRADE = 5000

# Definition for the Refinery
THRESHOLD_TO_REFINE = 30000

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


## These are two very fundamental helper to get the price or cost of commodities or equipments
def get_asset_cost(session,ticker):
    asset = session.get('http://localhost:9999/v1/assets',params = {"ticker":ticker}).json()
    return asset[0]['lease_price']

def get_latest_price(session,ticker):
    product = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":ticker}).json()
    return product[0]['close']


## This section contains fundamental news profit estimation, pipeline news avoidance, and soft news alert
## This function is all good and tested
def fundamental_news(session, tick):
    newsj = session.get('http://localhost:9999/v1/news').json()
    most_recent_news = newsj[0]
    news_title = most_recent_news["headline"].split(' ')
    tick_published = most_recent_news["tick"]
    
    ## Here, we start to categorize the news into 3 categories: Fundamental News, Pipeline News, and Soft News.abs
    # For this fundamental news, we want to ensure it's stil time effective. Once detect its profit, we will return the profit
    if news_title[0] == "WEEK" and tick-tick_published<tick: 
        actual_direction = 1
        estimate_direction = 1
        if news_title[4] == "DRAW": actual_direction = -1
        if news_title[10] == "DRAW": estimate_direction = -1
        total_surprise_volume = float(news_title[5])*actual_direction - float(news_title[11])*estimate_direction
        price_change = total_surprise_volume*-0.1
        # We proportionate the profit to take consideration on how much time have passed
        profit = VOLUME_TRADE_FOR_NEWS*price_change*1000
        return profit
    return 0

## This section is responsible for fundamental news execute
def fundamental_news_execute(session, profit):
    if profit != 0:
        if profit >0 :
            direction_first, direction_second = "BUY","SELL"
        elif profit <0: 
            direction_first, direction_second = "SELL", "BUY"

        volume_to_submit = VOLUME_TRADE_FOR_NEWS
        while volume_to_submit > 30:
            session.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_FOR_NEWS, 'type': 'MARKET', 'quantity': 30, 'action': direction_first})
            volume_to_submit -= 30
        session.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_FOR_NEWS, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': direction_first})

        sleep(TICK_TO_KEEP_FUTURE)

        volume_to_submit = VOLUME_TRADE_FOR_NEWS
        while volume_to_submit > 30:
            session.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_FOR_NEWS, 'type': 'MARKET', 'quantity': 30, 'action': direction_second})
            volume_to_submit -= 30
        session.post('http://localhost:9999/v1/orders', params={'ticker': TICKER_FOR_NEWS, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': direction_second})


## This section estimate the profit from future arbitrage => This is the Moving average of CL2-CL1-1's change
def future_contract(session):
    CL1 = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":"CL-1F"}).json()
    if CL1 == []:
        return 0
    else:
        first_ticker = "CL-1F"
        second_ticker = "CL-2F"
 
    CL1_prices = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":first_ticker, "limit":TICK_FOR_PRICE_CHANGE}).json()
    CL2_prices = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":second_ticker, "limit":TICK_FOR_PRICE_CHANGE}).json()
    
    CL1_price_new = CL1_prices[0]['close']
    CL2_price_new = CL2_prices[0]['close']
    CL1_price_old = CL1_prices[TICK_FOR_PRICE_CHANGE-1]['close']
    CL2_price_old = CL2_prices[TICK_FOR_PRICE_CHANGE-1]['close']
    
    New_formula_result = CL2_price_new-CL1_price_new-1
    Old_formula_result = CL2_price_old-CL1_price_old-1
    Price_Change = New_formula_result-Old_formula_result
    
    return Price_Change

# This section act on the future arbitrage opportunity
def future_contract_execute(session, profit, tick):
    if profit > 0:
        ticker_sell = "CL-2F"
        ticker_buy = "CL-1F"
    else:
        ticker_buy = "CL-1F"
        ticker_sell = "CL-2F"

    volume_to_submit = VOLUME_TRADE_FOR_FUTURE
    while volume_to_submit > 30:
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_buy, 'type': 'MARKET', 'quantity': 30, 'action': "BUY"})
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_sell, 'type': 'MARKET', 'quantity': 30, 'action': "SELL"})
        volume_to_submit -= 30
    session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_buy, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': "BUY"})
    session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_sell, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': "SELL"})
    
    current_tick = get_tick(session)
    new_profit = future_contract(session)
    while current_tick - tick > TICK_TO_KEEP_FUTURE or abs(new_profit) > abs(profit*PERCENTAGE_TO_EXIT):
        current_tick = get_tick(session)
        new_profit = future_contract(session)

    volume_to_submit = VOLUME_TRADE_FOR_FUTURE
    while volume_to_submit > 30:
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_buy, 'type': 'MARKET', 'quantity': 30, 'action': "SELL"})
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_sell, 'type': 'MARKET', 'quantity': 30, 'action': "BUY"})
        volume_to_submit -= 30
    session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_buy, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': "SELL"})
    session.post('http://localhost:9999/v1/orders', params={'ticker': ticker_sell, 'type': 'MARKET', 'quantity': volume_to_submit, 'action': "BUY"})


## This section looks at the profitability of refinary
def refinary(session):
    CL_price = get_latest_price(session, "CL")
    Refinary_cost = get_asset_cost(session, "CL-REFINERY")
    Storage_cost = get_asset_cost(session, "CL-STORAGE")
    HO_price = get_latest_price(session, "HO")
    RB_price = get_latest_price(session, "RB")
    
    estimated_profit = 10*42000*HO_price + 20*RB_price*42000 - Refinary_cost - 30*CL_price*1000 - 3*Storage_cost
    return estimated_profit
   
def refinary_execute(session):
    # Lease the storage
    store1 = session.post('http://localhost:9999/v1/leases', params={'ticker': "CL-STORAGE"}).json()
    store2 = session.post('http://localhost:9999/v1/leases', params={'ticker': "CL-STORAGE"}).json()
    store3 = session.post('http://localhost:9999/v1/leases', params={'ticker': "CL-STORAGE"}).json()
    store_list = [store1['id'],store2['id'],store3['id']]
    print(store_list)

    # # Buy the CL
    session.post('http://localhost:9999/v1/orders', params={'ticker': "CL", 'type': 'MARKET', 'quantity': 30, 'action': "BUY"})
    # # Hedge the Position
    session.post('http://localhost:9999/v1/orders', params={'ticker': "CL-2F", 'type': 'MARKET', 'quantity': 30, 'action': "SELL"})

    # # Lease & Use the Refinery
    session.post('http://localhost:9999/v1/leases', params={'ticker': "CL-REFINERY"})
    sleep(1)
    leased_assets = session.get('http://localhost:9999/v1/leases').json()
    for asset in leased_assets:
        if asset['ticker'] == "CL-REFINERY": 
            refinary_id = asset['id']
            print(refinary_id)
    session.post('http://localhost:9999/v1/leases/{}'.format(refinary_id), params={'from1': 'CL', 'quantity1': 30})
    sleep(1) # To make sure the server is up to date

    # We keep checking once the oil is in the refinery, we cancel the storage immediately
    leased_assets = session.get('http://localhost:9999/v1/leases').json()
    refinary_in_use = 0
    while refinary_in_use == 0:
        for asset in leased_assets:
            if asset['ticker'] == 'CL-REFINERY' and asset['convert_finish_period'] != []:
                refinary_in_use = 1
  
    for asset in leased_assets:
        if asset['ticker'] == 'CL-STORAGE' and asset['containment_usage'] == 0  and asset['id'] in store_list:
            asset_id = asset['id']
            resp = session.delete(f'http://localhost:9999/v1/leases/{asset_id}')

    # We start to check if the refineary is finished. As soon as it is, we will buy the future, sell HO and RB
    # We can leave the asset here for a bit and come back to revist when we have the next investment decision available
    while refinary_in_use == 1:
        leased_assets = session.get('http://localhost:9999/v1/leases').json()
        print(refinary_in_use)
        for asset in leased_assets:
            if asset['ticker'] == 'CL-REFINERY' and asset['convert_finish_period'] == None:
                refinary_in_use = 0
    
    session.post('http://localhost:9999/v1/orders', params={'ticker': "CL-2F", 'type': 'MARKET', 'quantity': 30, 'action': "BUY"})
    session.post('http://localhost:9999/v1/orders', params={'ticker': "HO", 'type': 'MARKET', 'quantity': 10, 'action': "SELL"})
    session.post('http://localhost:9999/v1/orders', params={'ticker': "RB", 'type': 'MARKET', 'quantity': 20, 'action': "SELL"})
    session.delete(f'http://localhost:9999/v1/leases/{refinary_id}')

## This section will work on the transportation
def transportation(session):
    AK_pipeline_cost = get_asset_cost(session, "AK-CS-PIPE")
    NY_pipeline_cost = get_asset_cost(session, "CS-NYC-PIPE")
    
    AK_price = get_latest_price(session, "CL-AK")
    NYC_price = get_latest_price(session, "CL-NYC")
    CL_price = get_latest_price(session, "CL")

    AK_Pipeline_Profit = (CL_price-AK_price)*10*1000-AK_pipeline_cost-6*150
    NYC_Pipeline_Profit = (NYC_price-CL_price)*10*1000-NY_pipeline_cost-6*150
    estimated_profit_AK = AK_Pipeline_Profit*3
    estimated_profit_NYC = NYC_Pipeline_Profit*3

    return estimated_profit_AK,estimated_profit_NYC

def transportation_exacute(session, pipeline_tick, storage1, storage2, ticker1, ticker2, hedge1, hedge2):
    #We only lease one storage and that will be enough :)
    resp = session.post('http://localhost:9999/v1/leases', params={'ticker': storage1}).json()
    trans_storage_id = resp['id']
    for i in range (0, UNIT_TRADE_FOR_TRANS):
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker1, 'type': 'MARKET', 'quantity': 10, 'action': "BUY"})
        session.post('http://localhost:9999/v1/leases', params={'ticker': pipeline_tick, 'from1': ticker1, 'quantity1': 10})
        session.post('http://localhost:9999/v1/orders', params={'ticker': "CL-2F", 'type': 'MARKET', 'quantity': 10, 'action': hedge1})
        sleep(0.5)
    resp = session.delete(f'http://localhost:9999/v1/leases/{trans_storage_id}')

    sleep(12)
    storage_id = []
    for i in range (0, UNIT_TRADE_FOR_TRANS):  
        resp = session.post('http://localhost:9999/v1/leases', params={'ticker': storage2}).json()
        trans_storage_id = resp['id']
        storage_id.append(trans_storage_id)

    current_arrived = 0
    while current_arrived < UNIT_TRADE_FOR_TRANS:
        for store_id in storage_id:
            storage_status = session.get('http://localhost:9999/v1/leases',params = {'id':trans_storage_id}).json()
            if storage_status[0]['containment_usage'] != 0 and storage_status[0]['containment_usage'] != None:
                session.post('http://localhost:9999/v1/orders', params={'ticker': ticker2, 'type': 'MARKET', 'quantity': 10, 'action': "SELL"})
                session.post('http://localhost:9999/v1/orders', params={'ticker': "CL-2F", 'type': 'MARKET', 'quantity': 10, 'action': hedge2})
                current_arrived += 1
    for store_id in storage_id:
        resp = session.delete(f'http://localhost:9999/v1/leases/{store_id}')


def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)
        
        while tick > 0 and tick < 550 and not shutdown:
            tick = get_tick(s)
            
            # profit = fundamental_news(s, tick)
            # fundamental_news_execute(s, profit)
            
            # profit = future_contract(s)
            # print(profit)
            # if abs(profit) > PRICE_THRESHOLD_TO_REACT:
            #     future_contract_execute(s, profit, tick)
            
            profit = refinary(s)
            print(profit)
            if profit > THRESHOLD_TO_REFINE:
                refinary_execute(s)

            AK_profit, NY_profit = transportation(s)
            print(AK_profit,NY_profit)
            if AK_profit > THRESHOLD_TO_TRADE:
                transportation_exacute(s, "AK-CS-PIPE", "AK-STORAGE", "CL-STORAGE", "CL-AK", "CL", "SELL","BUY")
            AK_profit, NY_profit = transportation(s)
            if NY_profit > THRESHOLD_TO_TRADE:
                transportation_exacute(s, "CS-NYC-PIPE", "CL-STORAGE", "NYC-STORAGE", "CL", "CL-NYC", "BUY","SELL")
            sleep(1)
        
if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()
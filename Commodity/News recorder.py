# Hello this is ALGO2

import signal
import requests
from time import sleep
from time import time

# GLOBAL VARIABLE
API_KEY = {'X-API-Key': '837E5K0H'}
shutdown = False

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

def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)
        
        while tick > 0 and tick < 600 and not shutdown:
            tick = get_tick(s)
            newsj = s.get('http://localhost:9999/v1/news').json()
            price = s.get('http://localhost:9999/v1/securities/history',params = {"ticker":"CL"}).json()
            record = open("Commodity/info2.txt", "a")
            record.write(f'{tick}, {newsj[0]["headline"]}-{newsj[0]["body"]}, {price[0]["close"]} \n')
            sleep(1.5)
    
if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()

# Algo2 be as aggressive as possible, the ALGO 2 might be a little bit too conservative
# For Algo2 we can make the spread small or trade with our selves
# -> Trade with oneself
# Get securities, position => 80% market order instead; if it's 50% limit order
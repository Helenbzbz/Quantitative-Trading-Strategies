
    first_prices_current = 0
    second_prices_current = 0
    for price in first_current:
        first_prices_current+= price['close']
    for price in second_current:
        second_prices_current+= price['close']
    New_MA = second_prices_current/TICK_FOR_MA-first_prices_current/TICK_FOR_MA-1

    first_old = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":first_ticker,"limit":TICK_FOR_MA+TICK_FOR_MA}).json()
    second_old = session.get('http://localhost:9999/v1/securities/history',params = {"ticker":second_ticker,"limit":TICK_FOR_MA+TICK_FOR_MA}).json()
    first_prices_old = 0
    second_prices_old = 0
    for i in range(TICK_FOR_MA,TICK_FOR_MA+TICK_FOR_MA):
        first_prices_old+= first_old[i]['close']
    for i in range(TICK_FOR_MA,TICK_FOR_MA+TICK_FOR_MA):
        second_prices_old+= second_old[i]['close']
    
    Old_MA = second_prices_old/TICK_FOR_MA-first_prices_old/TICK_FOR_MA-1
    Price_change = New_MA - Old_MA
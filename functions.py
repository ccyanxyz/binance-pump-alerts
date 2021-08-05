import requests
import time
from params import TOP_DUMP_ENABLED, VIEW_NUMBER, outlier_param, intervals, watchlist, pairs_of_interest, token, chat_id, tpdpa_chat_id,\
     FUTURE_ENABLED, DUMP_ENABLED, RESET_INTERVAL, PRINT_DEBUG, EXTRACT_INTERVAL, GET_PRICE_FAIL_INTERVAL,\
     SEND_TELEGRAM_FAIL_INTERVAL, TOP_PUMP_ENABLED, TOP_DUMP_ENABLED, TDPA_INTERVALS, HARD_ALERT_INTERVAL_ENABLED, MIN_ALERT_INTERVAL,\
     PUMP_EMOJI, DUMP_EMOJI, TDPA_EMOJI
from time import sleep
import telegram as telegram

# Initialize telegram bot
try:
    bot = telegram.Bot(token=token)
except Exception as e:
    print("Error initializing telegram bot")
    print(e)
    quit()

def durationToSeconds(str_dur):
    unit = str_dur[-1]
    if unit == 's': unit = 1
    elif unit == 'm': unit = 60
    elif unit == 'h': unit = 3600

    return  int(str_dur[:-1]) * unit

def send_message(message,isTPDA=False):
    if isTPDA: 
        if tpdpa_chat_id == 0: c_id = chat_id
        else: c_id = tpdpa_chat_id
    else: c_id = chat_id

    while True:
        try:
            bot.send_message(chat_id=c_id,text=message)
            break
        except:
            print("Retrying to send tele message in",SEND_TELEGRAM_FAIL_INTERVAL,"s")
            sleep(SEND_TELEGRAM_FAIL_INTERVAL)

EXTRACT_INTERVAL = durationToSeconds((EXTRACT_INTERVAL))
GET_PRICE_FAIL_INTERVAL = durationToSeconds(GET_PRICE_FAIL_INTERVAL)
SEND_TELEGRAM_FAIL_INTERVAL = durationToSeconds(SEND_TELEGRAM_FAIL_INTERVAL)
MIN_ALERT_INTERVAL = durationToSeconds(MIN_ALERT_INTERVAL)

# Choose whether we look at spot prices or future prices
if FUTURE_ENABLED: url = 'https://fapi.binance.com/fapi/v1/ticker/price'
else: url = 'https://api.binance.com/api/v3/ticker/price'

def getPrices():
    while True:
        try:
            data = requests.get(url).json()
            return data
        except Exception as e:
            print("Error:",e)
            print("Retrying in",GET_PRICE_FAIL_INTERVAL,"s")
            sleep(GET_PRICE_FAIL_INTERVAL) # Keeps trying every 0.5s 

def searchSymbol(symbol_name, data):
    for asset in data:
        if asset['symbol'] == symbol_name: return asset

def getPercentageChange(asset_dict):

    data_length = len(asset_dict['price'])

    for inter in intervals:
        data_points = int(durationToSeconds(inter) / EXTRACT_INTERVAL)

        if data_points+1 > data_length: break
        elif not HARD_ALERT_INTERVAL_ENABLED and (time.time() - asset_dict['last_triggered'] < MIN_ALERT_INTERVAL):  break # Skip checking for period since last triggered
        elif HARD_ALERT_INTERVAL_ENABLED and (time.time() - asset_dict['lt_dict'][inter] < durationToSeconds(inter)): # Check for HARD_ALERT_INTERVAL
            print("Duration insufficient",asset_dict['symbol'],inter)
            break # Skip checking for period since last triggered
        else: 
            change = round((asset_dict['price'][-1] - asset_dict['price'][-1-data_points]) / asset_dict['price'][-1],5)
            asset_dict[inter] = change # Stores change for the interval into asset dict (Used for top pump/dumps)

            if change >= outlier_param[inter]:
                asset_dict['last_triggered'] = time.time() # Updates last triggered time for MIN_ALERT_INTERVAL
                asset_dict['lt_dict'][inter] = time.time() # Updates last triggered time for HARD_ALERT_INTERVAL
                if PRINT_DEBUG: print("PUMP:",asset_dict['symbol'],'/ Change:',round(change*100,2),'/% Price:',asset_dict['price'][-1],'Interval:',inter) 
                send_message(PUMP_EMOJI+" Interval: " +str(inter) + " - " +asset_dict['symbol']+' / Change: '+str(round(change*100,2))+'% / Price: '+str(asset_dict['price'][-1])) 
                # Note that we don't need to break as we have updated 'lt_dict' parameter which will skip the remaining intervals
                return asset_dict # Prevents continuation of checking other intervals
            
            elif DUMP_ENABLED and -change >= outlier_param[inter]:
                asset_dict['last_triggered'] = time.time() # Updates last triggered time for MIN_ALERT_INTERVAL
                asset_dict['lt_dict'][inter] = time.time() # Updates last triggered time for HARD_ALERT_INTERVAL
                if PRINT_DEBUG: print("DUMP:",asset_dict['symbol'],'/ Change:',round(change*100,2),'% / Price:',asset_dict['price'][-1],'Interval:',inter) 
                send_message(DUMP_EMOJI+" Interval: " +str(inter) + " - " +asset_dict['symbol']+' / Change: '+str(round(change*100,2))+'% / Price: '+str(asset_dict['price'][-1])) 
                return asset_dict # Prevents continuation of checking other intervals
            
    return asset_dict

def topPumpDump(last_trigger_pd,full_asset):
    for inter in last_trigger_pd:
        if time.time() > last_trigger_pd[inter] + durationToSeconds(inter) + 8:
            msg = TDPA_EMOJI
            msg += ' Interval: ' + inter + '\n\n'
            if TOP_PUMP_ENABLED:
                pump_sorted_list = sorted(full_asset, key = lambda i: i[inter],reverse=True)[0:VIEW_NUMBER]
                msg += 'Top ' + str(VIEW_NUMBER) + ' PUMP\n'
                print("Top",VIEW_NUMBER,"PUMP")
                for asset in pump_sorted_list: 
                    print(asset['symbol'],':',asset[inter])
                    msg += str(asset['symbol']) + ': ' + str(round(asset[inter]*100,2)) + '%\n'

                msg += '\n'

            if TOP_DUMP_ENABLED:
                dump_sorted_list = sorted(full_asset, key = lambda i: i[inter])[0:VIEW_NUMBER]
                print("Top",VIEW_NUMBER,"DUMP")
                msg += 'Top ' + str(VIEW_NUMBER) + ' DUMP\n'
                for asset in dump_sorted_list: 
                    print(asset['symbol'],':',asset[inter])
                    msg += str(asset['symbol']) + ': ' + str(round(asset[inter]*100,2)) + '%\n'

            send_message(msg,isTPDA=True)
            
            last_trigger_pd[inter] = time.time() # Update time for trigger
    else: return last_trigger_pd




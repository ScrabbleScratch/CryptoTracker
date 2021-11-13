import errno,ubinascii,json,network,urequests as rq
from machine import unique_id,Pin,SoftI2C
from mqtt_modded import MQTTClient
from time import sleep,sleep_ms
from rotary_irq_esp import RotaryIRQ
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

# create file for broker url if not exists
try:
    with open("mqtt.txt", "x"):
        print("mqtt.txt created")
    with open("mqtt.txt", "w") as f:
        f.write("mq.makeblock.com")
except:pass

# load broker url from file
with open("mqtt.txt", "r") as f:
    brokerUrl = f.read()
    print("Broker: "+brokerUrl)

# mqtt broker url
clientId = ubinascii.hexlify(unique_id())
#brokerUrl = "mq.makeblock.com"
requestTopic = "/cryptotracker/binance/price/request"
dataTopic = "/cryptotracker/binance/price/data/"+clientId.decode()
validationKey = "symbol"

# api base url
apiBase = "https://api.binance.com/api/v3"

# I2C Lcd parameters
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 4
I2C_NUM_COLS = 20
# I2C Lcd initialization
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
del I2C_ADDR,I2C_NUM_ROWS,I2C_NUM_COLS

lcd.display_on()

# create custom characters
# right arrow character
lcd.custom_char(0, bytearray([0x10,0x18,0x1C,0x1E,0x1E,0x1C,0x18,0x10]))
lcd.custom_char(1, bytearray([0x01,0x03,0x07,0x0F,0x0F,0x07,0x03,0x01]))
lcd.custom_char(2, bytearray([0x04,0x0E,0x1F,0x04,0x04,0x04,0x04,0x04]))
lcd.custom_char(3, bytearray([0x04,0x04,0x04,0x04,0x04,0x1F,0x0E,0x04]))
lcd.custom_char(4, bytearray([0x00,0x01,0x01,0x01,0x01,0x01,0x01,0x00]))
lcd.custom_char(5, bytearray([0x00,0x10,0x10,0x10,0x10,0x10,0x10,0x00]))

# display welcome message
lcd.putstr("""\
********************
*      CRYPTO      *
*     TRACKER!     *
********************\
""")
lcd.backlight_off()
sleep(0.5)
lcd.backlight_on()
sleep(1)

# initialize rotary encoder instance
clkPin = 15
dtPin = 4
r = RotaryIRQ(pin_num_clk=clkPin,
              pin_num_dt=dtPin,
              min_val=0,
              max_val=0,
              reverse=False,
              range_mode=RotaryIRQ.RANGE_WRAP)
rbt = Pin(34, Pin.IN)

# initialize wlan connection
wlan = network.WLAN(network.STA_IF); wlan.active(True)

# slice a list in chunks of specific size
def genChunks(tlist, titems):
    print("genChunks()")
    tindex = list(range(0, len(tlist), titems))
    for i in tindex:
        if not i == tindex[-1]:
            yield tlist[i:i+titems]
        else:
            yield tlist[i:]

# create a menu string to display on the LCD
def menuString(toptions, tpage=0, tcursor=0, ttitle=""):
    print("menuString()")
    lcd.clear()
    if len(ttitle):
        trow = 1
        lcd.putstr(ttitle)
    else: trow = 0
    tmenu = ""
    for i in toptions[tpage]:
        lcd.move_to(0, trow)
        if i is toptions[tpage][tcursor]:
            if type(i) is list:
                top = f"{chr(0)}{i[0].upper()}/{i[1].upper()}\n"
            else:
                top = f"{chr(0)}{i}\n"
        else:
            if type(i) is list:
                top = f" {i[0].upper()}/{i[1].upper()}\n"
            else:
                top = f" {i}\n"
        lcd.putstr(top[:20])
        trow += 1
    return

# select a menu option using rotary encoder
def menuSel(topts, ttitle=""):
    print("menuSel()")
    if len(ttitle):
        print(ttitle)
        trows = 3
    else: trows = 4
    tchunks = list(genChunks(topts, trows))
    menuString(tchunks, ttitle=ttitle)
    r.set(min_val=0, max_val=len(topts)-1, value=0)
    val_old = r.value()
    while True:
        val_new = r.value()
        btn = rbt.value()
        if val_old != val_new:
            val_old = val_new
            print('result =', val_new)
            page = int(val_new/trows)
            item = val_new-page*trows
            menuString(tchunks, page, item, ttitle)
        if btn:
            print("Button = Pressed")
            selection = topts[val_new]
            while rbt.value(): pass
            break
        sleep_ms(50)
    print("Selected: ", selection)
    return selection

def userIn(tmessage="Input:", space=True, upperCase=True, lowerCase=True, numbers=True, symbols=True, delete=True, enter=True):
    print("userIn()")
    characters = []
    # add (SPACE) option to characters
    if space:
        characters += ["(SPACE)"]
    # add uppercase letters to characters
    if upperCase:
        characters += [chr(c) for c in range(65,91)]
    # add lowercase letters to characters
    if lowerCase:
        characters += [chr(c) for c in range(97,123)]
    # add numbers to characters
    if numbers:
        characters += [chr(c) for c in range(48,58)]
    # add symbols to characters
    if symbols:
        # create a list of symbols ascii codes
        symList = [s for s in range(47,32,-1)]+[s for s in range(64,57,-1)]+[s for s in range(91,97)]+[s for s in range(123,127)]
        # if a string is parsed add only the symbols to characters
        if type(symbols) is str:
            symbols = list(symbols)
            for s in symbols:
                if ord(s) in symList:
                    characters += s
        else:
            for s in symList:
                characters += chr(s)
    # add (DELETE) option to characters
    if delete:
        characters += ["(DELETE)"]
    # add (ENTER) option to characters
    if enter:
        characters += ["(ENTER)"]
    # print input menu
    lcd.clear()
    lcd.putstr(tmessage)
    tinput = ""
    lcd.move_to(0,1)
    lcd.putstr(str(chr(0)+tinput))
    lcd.move_to(0,3)
    lcd.putstr("> ")
    r.set(min_val=0, max_val=len(characters)-1, value=0)
    val_old = r.value()
    lcd.putstr(characters[val_old])
    while True:
        val_new = r.value()
        btn = rbt.value()
        if val_old != val_new:
            val_old = val_new
            lcd.move_to(2,3)
            lcd.putstr(" "*18)
            lcd.move_to(2,3)
            print('result =', characters[val_new])
            lcd.putstr(characters[val_new])
        if btn:
            print("Button pressed!")
            selection = characters[val_new]
            if not selection == "(ENTER)":
                lcd.clear()
                lcd.putstr(tmessage)
                if selection == "(DELETE)":
                    tinput = tinput[:-1]
                elif len(tinput) <= 39:
                    if selection == "(SPACE)":
                        tinput += " "
                    else:
                        tinput += selection
                lcd.move_to(0,1)
                lcd.putstr(str(chr(0)+tinput))
                lcd.move_to(0,3)
                print("Input = "+selection)
                lcd.putstr("> "+selection)
            else:
                break
            while rbt.value(): pass
        sleep_ms(50)
    return tinput

def connectMQTT(clientId, mqttServer, subTopic, callback=None):
    print("connectMQTT()")
    lcd.clear()
    lcd.putstr("Connecting to broker...")
    while True:
        try:
            client = MQTTClient(clientId, mqttServer)
            if not callback is None:
                print("Setting callback")
                client.set_callback(callback)
            print("Connecting to broker...")
            client.connect()
            print(f"Subscribing to {subTopic}...")
            client.subscribe(subTopic)
            print(f"Connected to {brokerUrl} MQTT broker, subscribed to {subTopic} topic")
            break
        except:
            print("Error while connecting to broker! Retrying...")
            lcd.clear()
            lcd.putstr("Error while connecting to broker! Retrying...")
            sleep(2.5)
    return client

def connect():
    print("connect()")
    lcd.clear()
    lcd.putstr("Wait...")
    wlan.active(True)
    if not wlan.isconnected():
        lcd.clear()
        lcd.putstr("""\
********************
*     LOADING      *
*      CONFIG      *
********************\
        """)
        # look for saved networks
        while True:
            try:
                with open("networks.json", "r") as f:
                    net = json.loads(f.read())
                    ssid = list(net.keys())
                    print("Saved networks: "+str(ssid))
                del f
                break
            except OSError as e:
                if e.errno == errno.ENOENT:
                    print("networks.json not found!")
                    with open("networks.json", "w") as f:
                        f.write("{}")
                    del f
                else:
                    print("Unknown error! (connect)")
                    raise Exception
        lcd.clear()
        lcd.putstr("Scanning networks...")
        ap = wlan.scan()
        for i in range(len(ap)):
            ap[i] = ap[i][0].decode()
        for i in ap:
            if i in ssid:
                wlan.connect(i, net[i])
                sleep(2.5)
                while not wlan.isconnected(): pass
                print(f"Connected to {i} network!")
                lcd.clear()
                lcd.putstr(f"Connected to {i} network!")
                sleep(1)
                break
        else:
            print("Networks not recognized!\n")
            while True:
                print(ap)
                Id = menuSel(ap, "Select network:")
                print("Password!")
                pwd = userIn("Insert password:")
                lcd.clear()
                lcd.putstr("Connecting...")
                wlan.connect(Id, pwd)
                sleep(2.5)
                count = 0
                while not wlan.isconnected() and count < 5:
                    count += 1
                    sleep(1)
                if wlan.isconnected():
                    print(f"Connected to {Id} network!")
                    lcd.clear()
                    lcd.putstr(f"Connected to {Id} network!")
                    sleep(1)
                    net[Id] = pwd
                    with open("networks.json", "w") as f:
                        f.write(json.dumps(net))
                    del f
                    print("Network saved!")
                    sleep(0.5)
                    break
                else:
                    wlan.active(False)
                    print("Something happened. Try again!")
                    lcd.clear()
                    lcd.putstr("Something happened. Try again!")
                    sleep(1)
                    wlan.active(True)
    else:
        print("Connected!")
        lcd.clear()
        lcd.putstr("Connected!")
    return

def saveState(option=False, symbol=False):
    print("writeState()")
    # look for saved coin pairs
    while True:
        try:
            state = {"option":option, "symbol":symbol}
            with open("state.json", "w") as f:
                f.write(json.dumps(state))
                print("Saved state: "+str(state))
            del f,state
            break
        except OSError as e:
            print("Something happened while saving state! (saveState)")
            lcd.clear()
            lcd.putstr("Something happened!")
            sleep(1)
    return

def loadState():
    print("loadState()")
    lcd.clear()
    lcd.putstr("Loading state...")
    # look for saved coin pairs
    while True:
        try:
            with open("state.json", "r") as f:
                state = json.loads(f.read())
                print("Loaded state: "+str(state))
            del f
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("State not found!")
                saveState()
            else:
                print("Unknown error! (loadState)")
                raise Exception
    return state

def symbolsList():
    print("symbolsList()")
    # look for saved symbols
    while True:
        try:
            with open("symbols.json", "r") as f:
                symbols = json.loads(f.read())
                print("Loaded symbols: "+str(list(symbols.keys())))
            del f
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("symbols.json not found!")
                with open("symbols.json", "w") as f:
                    f.write("{}")
                del f
            else:
                print("Unknown error! (symbolsList)")
                raise Exception
    return symbols

def addSymbol():
    print("addSymbol()")
    # look for saved symbols
    symbols = symbolsList()
    # add new symbol to the system
    while wlan.isconnected():
        baseAsset = userIn("Select base coin:", space=False, lowerCase=False, symbols="-_.")
        if not len(baseAsset) == 0:
            quoteAsset = userIn("Select quote coin:", space=False, lowerCase=False, symbols="-_.")
            symbol = baseAsset+quoteAsset
            print(f"Requesting: {symbol}")
            lcd.clear()
            lcd.putstr("Requesting symbol...")
            symbolInfo = rq.get(apiBase + f"/exchangeInfo?symbol={symbol}")
            if symbolInfo.status_code == 200 and len(symbolInfo.json()):
                symbolInfo = symbolInfo.json()
                symbolInfo = {"baseAsset":symbolInfo["symbols"][0]["baseAsset"],"quoteAsset":symbolInfo["symbols"][0]["quoteAsset"]}
                if not symbol in list(symbols.keys()):
                    symbols[symbol] = symbolInfo
                    with open("symbols.json", "w") as f:
                        f.write(json.dumps(symbols))
                    del f
                    print("Symbol saved: "+symbol)
                    lcd.clear()
                    lcd.putstr("Symbol saved!")
                else:
                    print("Symbol exists!")
                    lcd.clear()
                    lcd.putstr("Symbol exists!")
                del symbol,symbolInfo,baseAsset,quoteAsset
                break
            else:
                print("Symbol not found!")
                lcd.clear()
                lcd.putstr("Symbol not found!")
                sleep(1)
                if menuSel(["Yes","No"], "Try again?") == "No": break
                else:
                    del symbol,symbolInfo,baseAsset,quoteAsset
                    continue
        else:
            del baseAsset
            break
    else:
        print("Not connected!")
        lcd.clear()
        lcd.putstr("Not connected!")
    del symbols
    sleep(1)
    return

def removeSymbol():
    print("removeSymbol()")
    # look for saved symbols
    symbols = symbolsList()
    # remove symbol from the system
    symbols_opts = list(symbols.keys()) + ["(RETURN)"]
    while True:
        sel_symbol = menuSel(symbols_opts, "Select pair:")
        lcd.clear()
        lcd.putstr("Wait...")
        if not sel_symbol == "(RETURN)":
            print("Selected ", sel_symbol)
            symbols.pop(sel_symbol)
            if not sel_symbol in symbols.keys():
                try:
                    with open("symbols.json", "w") as f:
                        f.write(json.dumps(symbols))
                        print("Updated symbols list: "+str(symbols))
                    del f
                    lcd.clear()
                    lcd.putstr("Succesfully removed!")
                    del sel_symbol
                    sleep(1)
                    break
                except OSError as e:
                    print("Unknown error! (removeSymbol)")
                    raise Exception
        else: break
    del symbols,symbols_opts
    return

def showPrice(data, symbolInfo):
    print("showPrice()")
    print(f"{symbolInfo['baseAsset']}: {float(data['lastPrice'])} {symbolInfo['quoteAsset']}, 24hr: {float(data['priceChangePercent'])}%, High: {float(data['highPrice'])}, Low: {float(data['lowPrice'])}")
    lcd.clear()
    lcd.putstr(f"{symbolInfo['baseAsset']}/{symbolInfo['quoteAsset']}".center(20))
    lcd.move_to(0,1)
    lcd.putstr(f"{chr(0)} {float(data['lastPrice'])} {chr(1)}".center(20))
    lcd.move_to(0,2)
    lcd.putstr(f"{chr(2)}{float(data['highPrice'])}")
    lcd.move_to(9,2)
    lcd.putstr(chr(4)+chr(5))
    lcd.move_to(11,2)
    lcd.putstr(f"24hr".center(9))
    lcd.move_to(0,3)
    lcd.putstr(f"{chr(3)}{float(data['lowPrice'])}")
    lcd.move_to(9,3)
    lcd.putstr(chr(4)+chr(5))
    lcd.move_to(11,3)
    lcd.putstr(f"{float(data['priceChangePercent'])}%".center(9))
    del data,symbolInfo
    return

def requestPrice(client, symbol, option):
    print("requestPrice()")
    data = False
    # request symbol price to api by mqtt
    counter = 0
    while counter < 3:
        try:
            print("Requesting: "+symbol, end=" ")
            client.publish(requestTopic, f"{clientId.decode()}/{symbol}")
            data = json.loads(client.wait_msg().decode())
            #print(data)
            # if validation key exists in data, break
            if type(data) is dict:
                if validationKey in data.keys():
                    if data[validationKey] == symbol:
                        print("(SUCCESS)")
                        break
                    else:
                        print(f"(FAILED)(KEY CONTENT)")
                else:
                    print(f"(FAILED)(KEY EXIST)")
            else:
                print(f"(FAILED)(DATA TYPE)")
        #try: pass
        except:
            print(f"An error happened while requesting price! (requestPrice: {option})")
            #raise Exception("Error requesting single price!")
        print("Failed to request: "+symbol)
        sleep(2.5)
        counter += 1
    return data

def trackSingle(symbol=False):
    print("trackSingle()")
    # save state
    saveState(option="Track single")
    # look for saved symbols
    symbolsInfo = symbolsList()
    # select symbol if not selected
    if not symbol:
        # if no symbol is saved create one
        if not len(list(symbolsInfo.keys())):
            print("No symbols found!")
            lcd.clear()
            lcd.putstr("No symbols found!")
            sleep(1)
            addSymbol()
            #trackSingle()
            return
        # select symbol to track
        symbol = menuSel(list(symbolsInfo.keys()) + ["(RETURN)"], "Select symbol:")
    if not symbol == "(RETURN)":
        # save state
        saveState(option="Track single", symbol=symbol)
        # track symbol price
        client = connectMQTT(clientId, brokerUrl, dataTopic)
        timer = 0
        lcd.clear()
        lcd.putstr("Loading symbol...")
        r.set(min_val=0, max_val=50, value=0)
        val_old = r.value()
        while wlan.isconnected():
            val_new = r.value()
            # if rotary encoder is moved call the maiMenu
            if val_old != val_new:
                # save default state to return to mainMenu
                saveState()
                break
            if timer >= 5000:
                timer = 0
                # show selected symbol current price
                data = requestPrice(client, symbol, "trackSingle")
                if data: showPrice(data, symbolsInfo[symbol])
            sleep_ms(50)
            timer += 50
        else:
            print("Not connected!")
            lcd.clear()
            lcd.putstr("Not connected!")
            del timer,val_old
            sleep(1)
        client.disconnect()
    del symbolsInfo
    return

def trackMultiple():
    print("trackMultiple()")
    # save state
    saveState(option="Track multiple")
    # load symbols
    lcd.clear()
    lcd.putstr("Loading symbols...")
    # look for saved symbols
    symbolsInfo = symbolsList()
    symbols = list(symbolsInfo.keys())
    # if no symbol is saved create one
    if not len(symbols):
        print("No symbols found!")
        lcd.clear()
        lcd.putstr("No symbols found!")
        sleep(1)
        addSymbol()
        # save default state to return to mainMenu
        saveState()
        return
    # track symbols price
    client = connectMQTT(clientId, brokerUrl, dataTopic)
    timer = 0
    index = 0
    r.set(min_val=0, max_val=50, value=0)
    val_old = r.value()
    while wlan.isconnected():
        val_new = r.value()
        # if rotary encoder is moved call mainMenu
        if val_old != val_new:
            # save default state to return to mainMenu
            saveState()
            break
        if timer >= 5000:
            timer = 0
            # show each saved symbol current data
            data = requestPrice(client, symbols[index], "trackMultiple")
            if data: showPrice(data, symbolsInfo[symbols[index]])
            if index == len(symbols)-1: index = 0
            else: index += 1
        sleep_ms(50)
        timer += 50
    else:
        print("Not connected!")
        lcd.clear()
        lcd.putstr("Not connected!")
        sleep(1)
    client.disconnect()
    del symbolsInfo,symbols,timer,index,val_old
    return

def mainMenu():
    print("mainMenu()")
    # save default state to return to mainMenu
    saveState()
    while True:
        selection = menuSel(["Symbols", "Track", "Screen", "Reverse knob"], "Select an option:")
        if selection == "Symbols":
            del selection
            while True:
                print("Symbols options")
                selection = menuSel(["Add symbol", "Remove symbol", "(RETURN)"], "Symbols options:")
                if selection == "Add symbol":
                    del selection
                    print("Selected Add symbol")
                    addSymbol()
                elif selection == "Remove symbol":
                    del selection
                    print("Selected Remove symbol")
                    removeSymbol()
                else: break
        elif selection == "Track":
            del selection
            while True:
                print("Track options")
                selection = menuSel(["Single symbol", "Multiple symbols", "(RETURN)"], "Screen options:")
                if selection == "Single symbol":
                    del selection
                    print("Selected Single symbol")
                    trackSingle()
                    break
                elif selection == "Multiple symbols":
                    del selection
                    print("Selected Multiple symbols")
                    trackMultiple()
                    break
                else: break
        elif selection == "Screen":
            del selection
            while True:
                print("Screen options")
                selection = menuSel(["Turn ON light", "Turn OFF light", "(RETURN)"], "Screen options:")
                if selection == "Turn ON light":
                    del selection
                    print("LCD light ON")
                    lcd.backlight_on()
                elif selection == "Turn OFF light":
                    del selection
                    print("LCD light OFF")
                    lcd.backlight_off()
                else: break
        elif selection == "Reverse knob":
            print("Reverse knob")
            global clkPin,dtPin,r
            tclk = clkPin
            tdt = dtPin
            clkPin = tdt
            dtPin = tclk
            del tclk,tdt
            r = RotaryIRQ(pin_num_clk=clkPin, pin_num_dt=dtPin, min_val=0, max_val=0, reverse=False, range_mode=RotaryIRQ.RANGE_WRAP)
        else:
            break
    return

#####################################################################################################################

while True:
    try:
        while wlan.isconnected():
            print("Main loop!")
            state = loadState()
            if state["option"] == "Track single":
                if state["symbol"]:
                    trackSingle(state["symbol"])
                else:
                    trackSingle()
            elif state["option"] == "Track multiple":
                trackMultiple()
            else:
                mainMenu()
        else:
            print("Couldn't connect to the internet!")
            lcd.clear()
            lcd.putstr("Couldn't connect to the internet!")
            connect()
    #try: pass
    except Exception as e:
        print(f"Unknown error! ({e.errno}) Please reset the system.")
        print(e)
        lcd.clear()
        lcd.putstr("Unknown error!")
        lcd.move_to(0,1)
        lcd.putstr(str(e.errno))
        lcd.move_to(0,3)
        lcd.putstr("Please reset system!")
        lcd.backlight_off()
        sleep(1)
        lcd.backlight_on()
        sleep(5)

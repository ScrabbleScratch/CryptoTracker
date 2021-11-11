import errno, json, network, urequests as rq
from machine import Pin, SoftI2C
from time import sleep, sleep_ms
from rotary_irq_esp import RotaryIRQ
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

# I2C Lcd parameters
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 4
I2C_NUM_COLS = 20
# I2C Lcd initialization
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
del I2C_ADDR,I2C_NUM_ROWS,I2C_NUM_COLS

lcd.display_on()

# create custom arrow char
arrowChar = [0x00, 0x04, 0x06, 0x1F, 0x1F, 0x06, 0x04, 0x00]
lcd.custom_char(0, bytearray(arrowChar))
del(arrowChar)

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
r = RotaryIRQ(pin_num_clk=15,
              pin_num_dt=4,
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
    if space:
        characters += ["(DELETE)"]
    # add (ENTER) option to characters
    if space:
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
                    print("Saved: "+str(ssid))
                del f
                break
            except OSError as e:
                if e.errno == errno.ENOENT:
                    print("networks.json not found!")
                    with open("networks.json", "w") as f:
                        f.write("{}")
                    del f
                else:
                    print("Unknown error!")
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
                return True
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
                    return True
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
        return True
    return

def getVsCoins():
    print("getVsCoins()")
    lcd.clear()
    lcd.putstr("Getting coin list...")
    # get vs coin list from api
    try:
        vs_coin_list = rq.get("https://api.coingecko.com/api/v3/simple/supported_vs_currencies").json()
        with open("coins.json", "w") as f:
            f.write(json.dumps(vs_coin_list))
            print("Saved vs coins list!")
        lcd.clear()
        lcd.putstr("Coin list saved!")
        del vs_coin_list,f
        sleep(1)
    except:
        print("Something happened while getting vs coins list!")
        lcd.clear()
        lcd.putstr("Something happened!")
        sleep(1)
    return

def coinsList():
    print("coinsList()")
    lcd.clear()
    lcd.putstr("Loading coins...")
    # look for saved coin pairs
    while True:
        try:
            with open("coins.json", "r") as f:
                coins = json.loads(f.read())
                print("Saved: "+str(coins))
            del f
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                print(" Coins list not found!")
                getVsCoins()
            else:
                print("Unknown error!")
                raise Exception
    return coins

def saveState(option=False, pair=False):
    print("writeState()")
    # look for saved coin pairs
    while True:
        try:
            state = {"option":option, "pair":pair}
            with open("state.json", "w") as f:
                f.write(json.dumps(state))
                print("Saved: "+str(state))
            del f,state
            break
        except OSError as e:
            print("Something happened while saving state!")
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
                print("Saved: "+str(state))
            del f
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("State not found!")
                saveState()
            else:
                print("Unknown error!")
                raise Exception
    return state

def pairsList():
    # look for saved coin pairs
    while True:
        try:
            with open("pairs.json", "r") as f:
                pairs = json.loads(f.read())
                print("Saved: "+str(pairs))
            del f
            break
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("pairs.json not found!")
                with open("pairs.json", "w") as f:
                    f.write("[]")
                del f
            else:
                print("Unknown error!")
                raise Exception
    return pairs

def addPair():
    print("addPair()")
    # look for saved coin pairs
    pairs = pairsList()
    # get vs coin list from api
    vs_coin_list = coinsList()
    # add new coin pair to the system
    #while True:
    while wlan.isconnected():
        sel_coin = userIn("Select coin:", symbols="-").lower().replace(" ","")
        if not len(sel_coin) == 0:
            vs_coin = menuSel(vs_coin_list, "Select vs coin:")
            lcd.clear()
            lcd.putstr("Looking for pair...")
            price = rq.get(f"https://api.coingecko.com/api/v3/simple/price?ids={sel_coin}&vs_currencies={vs_coin}")
            if price.status_code == 200 and len(price.json()):
                pair = [sel_coin,vs_coin]
                if not pair in pairs:
                    pairs.append(pair)
                    with open("pairs.json", "w") as f:
                        f.write(json.dumps(pairs))
                    del f
                    print("Pair saved!")
                    lcd.clear()
                    lcd.putstr("Pair saved!")
                else:
                    print("Pair exists!")
                    lcd.clear()
                    lcd.putstr("Pair exists!")
                del sel_coin,vs_coin,price,pair
                break
            else:
                print("Pair not found!")
                lcd.clear()
                lcd.putstr("Pair not found!")
                sleep(1)
                if menuSel(["Yes","No"], "Try again?") == "No": break
                else: continue
        else:
            del sel_coin
            break
    else:
        print("Not connected!")
        lcd.clear()
        lcd.putstr("Not connected!")
        sleep(1)
        return
    del pairs,vs_coin_list
    sleep(1)
    return

def removePair():
    print("removePair()")
    # look for saved coin pairs
    pairs = pairsList()
    # remove coin pair from the system
    pairs_opts = pairs[:] + ["(RETURN)"]
    while True:
        sel_pair = menuSel(pairs_opts, "Select pair:")
        lcd.clear()
        lcd.putstr("Wait...")
        if not sel_pair == "(RETURN)":
            print("Selected ", sel_pair)
            pair_index = pairs.index(sel_pair)
            pairs.pop(pair_index)
            if not sel_pair in pairs:
                try:
                    with open("pairs.json", "w") as f:
                        f.write(json.dumps(pairs))
                        print("Updated: "+str(pairs))
                    del f
                    lcd.clear()
                    lcd.putstr("Succesfully removed!")
                    del sel_pair,pair_index
                    sleep(1)
                    break
                except OSError as e:
                    print("removePair unknown error!")
                    raise Exception
        else: break
    del pairs,pairs_opts
    return

def trackSingle(pair=False):
    print("trackSingle()")
    # save state
    saveState(option="Track single")
    # select pair if not selected
    if not pair:
        # look for saved coin pairs
        pairs = pairsList()
        # if no pair is saved create one
        if not len(pairs):
            print("No pairs found!")
            lcd.clear()
            lcd.putstr("No pairs found!")
            sleep(1)
            addPair()
            trackSingle()
        # select pair to track
        pairs_opts = pairs[:] + ["(RETURN)"]
        pair = menuSel(pairs_opts, "Select pair:")
        del pairs_opts
    if not pair == "(RETURN)":
        # save state
        saveState(option="Track single", pair=pair)
        # track coins price
        timer = 0
        lcd.clear()
        lcd.putstr(f"{pair[0].upper()}:".center(20))
        lcd.move_to(0,2)
        lcd.putstr("Tracking...".center(20))
        r.set(min_val=0, max_val=50, value=0)
        val_old = r.value()
        #while True:
        while wlan.isconnected():
            val_new = r.value()
            # if rotary encoder is moved call the main menu
            if val_old != val_new:
                mainMenu()
                trackSingle(pair)
                return
            if timer >= 5000:
                timer = 0
                # show each saved coin pair current price
                while True:
                    try:
                        price = rq.get(f"https://api.coingecko.com/api/v3/simple/price?ids={pair[0]}&vs_currencies={pair[1]}").json()
                        break
                    except:
                        print("An error happende while requesting price! (Single)")
                        raise Exception("Error requesting single price!")
                print(f"{pair[0].upper()}: {price[pair[0]][pair[1]]} {pair[1].upper()}")
                lcd.move_to(0,2)
                lcd.putstr(f"{price[pair[0]][pair[1]]} {pair[1].upper()}".center(20))
            sleep_ms(50)
            timer += 50
        else:
            print("Not connected!")
            lcd.clear()
            lcd.putstr("Not connected!")
            sleep(1)
            return
    return

def trackMultiple():
    print("trackMultiple()")
    lcd.clear()
    lcd.putstr("Loading coins...")
    # look for saved coin pairs
    pairs = pairsList()
    # if no pair is saved create one
    if not len(pairs):
        print("No pairs found!")
        lcd.clear()
        lcd.putstr("No pairs found!")
        sleep(1)
        addPair()
        trackMultiple()
    # save state
    saveState(option="Track multiple")
    # track coins price
    timer = 0
    index = 0
    r.set(min_val=0, max_val=50, value=0)
    val_old = r.value()
    #while True:
    while wlan.isconnected():
        val_new = r.value()
        # if rotary encoder is moved call the main menu
        if val_old != val_new:
            mainMenu()
            trackMultiple()
            return
        if timer >= 5000:
            timer = 0
            # show each saved coin pair current price
            p = pairs[index]
            while True:
                try:
                    price = rq.get(f"https://api.coingecko.com/api/v3/simple/price?ids={p[0]}&vs_currencies={p[1]}").json()
                    break
                except:
                    print("An error happened while requesting price! (Multiple)")
                    raise Exception("Error requesting multiple price!")
            print(f"{p[0].upper()}: {price[p[0]][p[1]]} {p[1].upper()}")
            lcd.clear()
            lcd.putstr(f"{p[0].upper()}:".center(20))
            lcd.move_to(0,2)
            lcd.putstr(f"{price[p[0]][p[1]]} {p[1].upper()}".center(20))
            if index == len(pairs)-1: index = 0
            else: index += 1
        sleep_ms(50)
        timer += 50
    else:
        print("Not connected!")
        lcd.clear()
        lcd.putstr("Not connected!")
        sleep(1)
        return
    return

def mainMenu():
    print("mainMenu()")
    while True:
        selection = menuSel(["Pairs", "Track", "Screen", "Update coin list", "(RETURN)"], "Select an option:")
        if selection == "Pairs":
            del selection
            while True:
                print("Pair options")
                selection = menuSel(["Add pair", "Remove pair", "(RETURN)"], "Screen options:")
                if selection == "Add pair":
                    del selection
                    print("Selected Add pair")
                    addPair()
                elif selection == "Remove pair":
                    del selection
                    print("Selected Remove pairs")
                    removePair()
                else: break
        elif selection == "Track":
            del selection
            while True:
                print("Track options")
                selection = menuSel(["Single pair", "Multiple pairs", "(RETURN)"], "Screen options:")
                if selection == "Single pair":
                    del selection
                    print("Selected Single pair")
                    trackSingle()
                elif selection == "Multiple pairs":
                    del selection
                    print("Selected Multiple pairs")
                    trackMultiple()
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
        elif selection == "Update coin list":
            print("Update coin list")
            getVsCoins()
        else:
            return
    return

#####################################################################################################################

while True:
    try:
        while wlan.isconnected():
            print("Main loop!")
            coins = coinsList()
            del coins
            state = loadState()
            if state["option"] == "Track single":
                if state["pair"]:
                    trackSingle(state["pair"])
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
    except Exception as e:
        print(f"Unknown error! ({e.errno}) Please reset the system.")
        #print(e)
        print("Resetting system!")
        lcd.clear()
        lcd.putstr("Unknown error!")
        lcd.move_to(0,1)
        lcd.putstr(str(e.errno))
        lcd.move_to(0,3)
        lcd.putstr("Resetting system!")
        lcd.backlight_off()
        sleep(1)
        lcd.backlight_on()
        sleep(5)



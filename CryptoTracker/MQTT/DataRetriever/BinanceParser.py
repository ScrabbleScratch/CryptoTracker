import requests as rq
from paho.mqtt import publish, subscribe
from time import sleep

try:
    with open("mqtt.txt", "x"):
        print("mqtt.txt created")
    with open("mqtt.txt", "w") as f:
        f.write("DEFAULT.MQTT.BROKER.URL")
except:pass

with open("mqtt.txt", "r") as f:
    brokerUrl = f.read()
    print("Broker: "+brokerUrl)

def subscribe_on_message(client, userdata, message):
    while True:
        try:
            req = message.payload.decode().split("/")
            print("Got: "+str(req))
            data = rq.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={req[1]}").text
            pubTopic = "/TOPIC/TO/SEND/PRICE/DATA/"+req[0]
            print("Publishing to: "+pubTopic)
            publish.single(pubTopic, data, 2, hostname=brokerUrl)
            break
        #try: pass
        except:
            print("An error occurred while getting price!")
        sleep(2.5)

subscribe.callback(subscribe_on_message, "/TOPIC/TO/REQUEST/PRICE/DATA", hostname=brokerUrl)

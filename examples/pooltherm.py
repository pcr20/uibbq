import uasyncio as asyncio
from uibbq import iBBQ
import aioble

import time
import ntptime
import network
import sys

from umqtt.robust import MQTTClient

import ubinascii
import json

def handle_data(d):
    print("Result:", d)


async def run(server="10.9.8.1",topic="esp32"):
    ibbq = iBBQ(handle_data)

    await ibbq.connect()
    macsensor=ibbq.get_addr_hex()
    temperature = await ibbq.read_temperature()
    print("Temperature: {}".format(temperature))
    await asyncio.sleep(1)
    print("Disconnecting")
    await ibbq.disconnect()
    
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    ip=network.WLAN().ifconfig()[0]
    ntptime.settime()
    t = time.gmtime()
    tstr = "{:04d}-{:02d}-{:02d}_{:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
    topic="{}/{}/{}".format(topic,mac,macsensor)
    msg=json.dumps({"temperature":temperature, "sampletime":tstr, "hostip":ip, "hostmac":mac, "sensormac":macsensor})
    print("publish: {} to {}".format(msg,topic))
    c = MQTTClient("umqtt_client", server)
    try:
        c.connect()    
        c.publish(topic,msg)
        c.disconnect()
    except Exception as e:
        print("Error publishing MQTT")
        sys.print_exception(e)
        return None        

asyncio.run(run())




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

device_macs=[b'\x49\x22\x01\x23\x07\x1c',b'\x49\x22\x01\x06\x01\xf8']
#device_macs=[]

async def find_sensors():
    ibbq = iBBQ(handle_data)
    s= await ibbq.find_ibbq(device_name_in="tps")
    if s:
        print("Found tps: {} {}".format(ibbq.get_addr_hex(),ibbq._device.addr))
        device_macs.append(ibbq._device.addr)
    s= await ibbq.find_ibbq(device_name_in="sps")
    if s:    
        print("Found sps: {} {}".format(ibbq.get_addr_hex(),ibbq._device.addr))
        device_macs.append(ibbq._device.addr)
        
async def run(server="10.9.8.1",topic="esp32"):
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    ip=network.WLAN().ifconfig()[0]
    ntptime.settime()
    
    if not device_macs:
        await find_sensors()
    
    ibbq = iBBQ(handle_data)
        
    for device_mac in device_macs:
        await ibbq.connect(device_mac=device_mac)
        #await ibbq.connect()
        macsensor=ibbq.get_addr_hex()
        temperature,rh,data = await ibbq.read_temperature_rh()
        print("Temperature: {} RH: {}% data: {}".format(temperature,rh,'_'.join('{:02X}'.format(d) for d in data)))
        await asyncio.sleep(1)
        print("Disconnecting")
        await ibbq.disconnect()
        

        t = time.gmtime()
        tstr = "{:04d}-{:02d}-{:02d}_{:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        topic="{}/{}/{}".format(topic,mac,macsensor)
        msg=json.dumps({"temperature":temperature, "rh":rh,"data":'_'.join('{:02X}'.format(d) for d in data), "sampletime":tstr, "hostip":ip, "hostmac":mac, "sensormac":macsensor})
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




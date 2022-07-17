import uasyncio as asyncio
from uibbq import iBBQ
import aioble

import time
import ntptime
import network
import sys
import io
from machine import ADC
from machine import Pin

from umqtt.robust import MQTTClient

import ubinascii
import json

device_macs=[b'\x49\x22\x01\x23\x07\x1c',b'\x49\x22\x01\x06\x01\xf8']
#device_macs=[b'\x49\x22\x01\x23\x07\x1c']
#device_macs=[]
topicprefix="esp32"
mqttserver="10.9.8.1"

def handle_exception(e):
    fio = io.StringIO()
    sys.print_exception(e, fio)
    print(fio.read())
    fio.seek(0)
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    topic="{}/{}/error".format(topicprefix,mac)
    c = MQTTClient("umqtt_client", mqttserver)
    try:
       c.connect()    
       c.publish(topic,fio.read())
       c.disconnect()
    except Exception as e:
       print("Error publishing MQTT")
       sys.print_exception(e)
 
def read_battery_voltage():
    p35 = ADC(Pin(35))
    p35.atten(ADC.ATTN_11DB)
    p35.width(ADC.WIDTH_12BIT)
    val = p35.read()
    return val



def handle_data(d):
    print("Result:", d)



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
        
async def run():
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    ip=network.WLAN().ifconfig()[0]
    try: 
        ntptime.settime()
    except OSError as e:
        handle_exception(e)
    
    if not device_macs:
        await find_sensors()
    
        
    for device_mac in device_macs:
        ibbq = iBBQ(handle_data)
        try:
            await ibbq.connect(device_mac=device_mac)
        except Exception as e:
            handle_exception(e)
            continue
        
        macsensor=ibbq.get_addr_hex()
        for n in range(0,2):
            temperature,rh,data = await ibbq.read_temperature_rh()
            if temperature:
                break
        if isinstance(data,type(None)):
            data=[]
            handle_exception(Exception('Error retrieving temperature'))
            
        print("Temperature: {} RH: {}% data: {}".format(temperature,rh,' '.join('{:02X}'.format(d) for d in data)))
        await asyncio.sleep(1)
        
       
        current_voltage, max_voltage = await ibbq.battery_level()
        print("current_voltage: {}, max_voltage, {}".format(current_voltage,max_voltage))
        if isinstance(current_voltage,type(None)):
            handle_exception(Exception('Error retrieving battery voltage'))
        
        print("Disconnecting")
        await ibbq.disconnect()
        

        t = time.gmtime()
        tstr = "{:04d}-{:02d}-{:02d}_{:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        #(time.time()+946684800)
        topic="{}/{}/{}".format(topicprefix,mac,macsensor)
        msg=json.dumps({"fields":{"temperature":temperature, "rh":rh,"voltage":current_voltage,"maxvoltage":max_voltage,"sourcedata":'\\ '.join('{:02X}'.format(d) for d in data),"srctime":tstr,"battvolt":read_battery_voltage()},"tags":{"hostip":ip, "hostmac":mac, "sensormac":macsensor},"time":(time.time()+946684800)})
        print("publish: {} to {}".format(msg,topic))
        c = MQTTClient("umqtt_client", mqttserver)
        try:
            c.connect()    
            c.publish(topic,msg)
            c.disconnect()
        except Exception as e:
            print("Error publishing MQTT")
            sys.print_exception(e)
            return None        

asyncio.run(run())




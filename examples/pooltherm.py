import uasyncio as asyncio
from uibbq import iBBQ
import aioble
from struct import unpack_from  


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

device_macs=[b'\x49\x22\x01\x23\x0f\x90',b'\x49\x22\x01\x23\x07\x1c',b'\x49\x22\x01\x06\x01\xf8']
#device_macs=[b'\x49\x22\x01\x23\x07\x1c']
#device_macs=[]
topicprefix="esp32"
mqttserver="10.9.8.1"
erno=0

def handle_exception(e):
    global erno
    erno=erno+1
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

def decode_result(result_in):
    print("data {}".format(ubinascii.hexlify(result_in.resp_data," ").decode()))
    temperature = unpack_from("<h", result_in.resp_data[7 : 9])[0] / 100.0
    rh = unpack_from("<h", result_in.resp_data[9 : 11])[0] / 100.0
    batt = result_in.resp_data[14]
    return (temperature,rh,batt,result_in.device.addr_hex(),result_in.resp_data,result_in)
    
#inkbird IBS-TH2 data
#0000   04 09 73 70 73 0a ff 82 0a d2 24 00 e4 ff 64 08    26.90   94.26 100%
#0000   04 09 73 70 73 0a ff 3b 0b 53 25 00 29 60 64 08    28.75   95.55 100%
#0000   04 09 73 70 73 0a ff b1 0b 79 25 00 91 77 64 08    29.93   95.93 100%
#0000   04 09 73 70 73 0a ff c0 0a 11 14 00 78 cc 63 08    27.52   51.37 99%
#0000   04 09 73 70 73 0a ff 1b 0b 7e 13 00 2f 0e 62 08    28.43   49.90 98%



async def read_sensor_scan(result_list_in_out,device_name_in=["sps"]):
    # Scan for 5 seconds, in active mode, with very low interval/window (to
    # maximise detection rate).
    assert isinstance(result_list_in_out, list)
    mac_seen=[]
    async with aioble.scan(
        5000, interval_us=30000, window_us=30000, active=True
    ) as scanner:
        async for result in scanner:
            #print(result.name())
            if result.name() in device_name_in and not result.device.addr_hex() in mac_seen:
                print("Found {}".format(result.name()))
                result_list_in_out.append(decode_result(result))
                mac_seen.append(result_list_in_out[-1][3])
            
          

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


async def run_scan():
    global erno
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    ip=network.WLAN().ifconfig()[0]
    try: 
        ntptime.settime()
    except OSError as e:
        handle_exception(e)
    
    scan_results_list_in_out=[]
    devices_list=["tps","sps"]
    print("Starting scan for {}".format(devices_list))
    await read_sensor_scan(scan_results_list_in_out,devices_list)  
    print("Completed scan")    
    for scan_result in scan_results_list_in_out:
        temperature=scan_result[0]
        rh=scan_result[1]
        batt=scan_result[2]
        data=scan_result[4]
        macsensor=scan_result[3]
        print("Temperature: {} RH: {}%  Batt: {}% data: {}".format(temperature,rh,batt,' '.join('{:02X}'.format(d) for d in data)))
        t = time.gmtime()
        tstr = "{:04d}-{:02d}-{:02d}_{:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        #(time.time()+946684800)
        topic="{}/{}/{}".format(topicprefix,mac,macsensor)
        msg=json.dumps({"fields":{"temperature":temperature, "rh":rh,"batt":batt,"sourcedata":'\\ '.join('{:02X}'.format(d) for d in data),"srctime":tstr},"tags":{"hostip":ip, "hostmac":mac, "sensormac":macsensor},"time":(time.time()+946684800)})
        print("publish: {} to {}".format(msg,topic))
        c = MQTTClient("umqtt_client", mqttserver)
        try:
            c.connect()    
            c.publish(topic,msg)
            c.disconnect()
        except Exception as e:
            print("Error publishing MQTT")
            sys.print_exception(e)
            erno=erno+1
    return erno


async def run():
    global erno
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
            erno=erno+1
    return erno







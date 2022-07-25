# This file is executed on every boot (including wake-boot from deepsleep) Paul
#import esp
import webrepl
import machine
import time
from machine import WDT
import uasyncio as asyncio
import inkbird
from umqtt.robust import MQTTClient
import ubinascii
import network
import sys

WEBREPL_PASS=""
SLEEPTIME_S=1800
#SLEEPTIME_S=20
wdt = WDT(timeout=(SLEEPTIME_S+100)*1000)
#esp.osdebug(None)
def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        available=[i[0] for i in wlan.scan()]
        if b'hurstpark' in available:
            wlan.connect('hurstpark', 'impasse-cambridge-gestas')
        elif b'papeterie' in available:
            wlan.connect('papeterie', 'impasse-cambridge-gestas')
        else:
            assert False
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

do_connect()

def mqtt_sub_cb(topic, msg):
    global WEBREPL_PASS
    WEBREPL_PASS=msg
    print((topic,msg))

c = MQTTClient("umqtt_client", "10.9.8.1")
c.set_callback(mqtt_sub_cb)
c.connect(clean_session=True)
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
c.subscribe("esp32/{}/enablewebrepl".format(mac))
time.sleep(1)
c.check_msg()
c.disconnect()

c.connect()    
if WEBREPL_PASS:
    c.publish("esp32/{}/enablewebreplstatus".format(mac),"starting webrepl: {}".format(WEBREPL_PASS))
    webrepl.start(password=WEBREPL_PASS)
else:
    c.publish("esp32/{}/enablewebreplstatus".format(mac),"not starting webrepl")
c.disconnect()

# check if the device woke from a deep sleep
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')
    
if WEBREPL_PASS:
    sys.exit()

ret_status = asyncio.run(inkbird.run())

if ret_status:
    print("Errorcode {} - resetting:".format(ret_status))
    time.sleep(0.2)
    machine.reset()

for n in range(30,0,-1):
    print("waiting for keyboard interrupt... {}".format(n))
    time.sleep(1)
    
wdt.feed()

print("entering deepsleep")
# put the device to sleep for 10 seconds
machine.deepsleep(SLEEPTIME_S*1000)



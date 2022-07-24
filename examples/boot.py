# This file is executed on every boot (including wake-boot from deepsleep) Paul
#import esp
import webrepl
import machine
import time
from machine import WDT
import uasyncio as asyncio
import inkbird

SLEEPTIME_S=1800
#SLEEPTIME_S=20
wdt = WDT(timeout=(SLEEPTIME_S+100)*1000)
#esp.osdebug(None)
def do_connect():
    import network
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
webrepl.start()

# check if the device woke from a deep sleep
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print('woke from a deep sleep')
    

ret_status = asyncio.run(inkbird.run())

wdt.feed()

if ret_status:
    print("Errorcode {} - resetting:".format(ret_status))
    time.sleep(0.2)
    machine.reset()

for n in range(30,0,-1):
    print("waiting for keyboard interrupt... {}".format(n))
    time.sleep(1)
print("entering deepsleep")
# put the device to sleep for 10 seconds
machine.deepsleep(SLEEPTIME_S*1000)


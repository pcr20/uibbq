# This file is executed on every boot (including wake-boot from deepsleep) Paul
#import esp
import machine

import uasyncio as asyncio
import pooltherm
from machine import WDT
SLEEPTIME_S=1800
#SLEEPTIME_S=20
wdt = WDT(timeout=(SLEEPTIME_S+100)*1000)

ret_status = asyncio.run(pooltherm.run_scan())

for n in range(30,0,-1):
    print("waiting for keyboard interrupt... {}".format(n))
    time.sleep(1)
wdt.feed()

print("entering deepsleep")
# put the device to sleep for 10 seconds
machine.deepsleep(SLEEPTIME_S*1000)



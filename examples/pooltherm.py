import uasyncio as asyncio
from uibbq import iBBQ
import aioble

def handle_data(d):
    print("Result:", d)


async def run():
    ibbq = iBBQ(handle_data)
    await ibbq.connect()
    print("Battery:", await ibbq.read_temperature())
    await asyncio.sleep(1)
    print("Disconnecting")
    await ibbq.disconnect()

asyncio.run(run())




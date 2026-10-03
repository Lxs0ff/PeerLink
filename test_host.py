import signaling
import certificates as certif
import stun
import asyncio

async def main():
    room = signaling.createRoom()
    connected = await room.connect()
    if connected:
        conf, cert, key , fp = certif.createHostConfig()
        print("Connection successfull")
        print("Room ID:", room.code)
        print("Owner Token:", room.token)
        addr = await room.exchangeAddr(fp)
        print("Peer Address:", addr)
        print("Hole Punching ...")
        await stun.holePunching(stun.getInfo(),addr)
        print("Hole Punched !")
    else:
        print("An error happened while connecting to the room")
    

asyncio.run(main())
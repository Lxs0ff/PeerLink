import signaling
import certificates as certif
import stun
import asyncio

async def main():
    code = input("Room Id: ")
    room = signaling.joinRoom(code=code)
    connected = await room.connect()
    if connected:
        conf = certif.createConfig()
        print("Connection successfull")
        addr = await room.exchangeAddr()
        fp = addr[2]
        addr = addr[0:2]
        print("Peer Address:", addr[0:2])
        print("Host Fingerprint:",fp)
        print("Hole Punching ...")
        await stun.holePunching(stun.getInfo(),addr)
        print("Hole Punched !")
    else:
        print("An error happened while connecting to the room")

asyncio.run(main())
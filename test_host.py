import signaling
import certificates as certif
import stun
import asyncio
import quic

async def main():
    TEST = False
    room = signaling.createRoom()
    connected = await room.connect()
    if connected:
        conf, cert, key , fp = certif.createHostConfig(room.code)
        print("Connection successfull")
        print("Room ID:", room.code)
        print("Owner Token:", room.token)
        addr,localport = await room.exchangeAddr(fp)
        print("Peer Address:", addr)
        print("Hole Punching ...")
        await stun.holePunching(localport,addr)
        print("Hole Punched !")
        Server = quic.QuicNetworking()
        await Server.createServer(conf,localport)
        while True:
            await asyncio.sleep(1)
    else:
        print("An error happened while connecting to the room")
    

asyncio.run(main())
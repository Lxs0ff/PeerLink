import signaling
import certificates as certif
import stun
import asyncio
import quic

async def main():
    TEST = False
    code = input("Room Id: ")
    room = signaling.joinRoom(code=code)
    connected = await room.connect()
    if connected:
        conf = certif.createConfig(code)
        print("Connection successfull")
        addr,localport = await room.exchangeAddr()
        fp = addr[2]
        addr = addr[0:2]
        print("Peer Address:", addr[0:2])
        print("Host Fingerprint:",fp)
        print("Hole Punching ...")
        await stun.holePunching(localport,addr)
        print("Hole Punched !")
        Client = quic.QuicNetworking()
        if addr[0] == stun.getLocalInfo(False)[0]: 
            addr = ("127.0.0.1",addr[1])
        print("Connecting to addr:",addr)
        success = await Client.connectClient(conf,addr,localport,fp)
        if not success:
            print("Could not connect to server, invalid fingerprint...")
        else:
            print("Sucessfully connected to server!")
        while True:
            await asyncio.sleep(1)
    else:
        print("An error happened while connecting to the room")

asyncio.run(main())
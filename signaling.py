import websockets as ws
import asyncio
import requests
import json
import stun

SERVER = "0x1.lxsdev.net"

class Room:
    def __init__(self,code,token = None):
        self.code = code
        self.token = token
        self.webs = None
        self.recv_task = None
        self.queue = asyncio.Queue()

    async def send(self,data):
        await self.webs.send(data)

    async def recvData(self):
        try:
            while True:
                data = await self.webs.recv()
                data = json.loads(data)
                await self.queue.put(data)
        except asyncio.CancelledError:
            pass

    async def waitFor(self,type):
        while True:
            data = await self.nextTask()
            if data["type"] == type:
                return data

    async def nextTask(self):
        data = await self.queue.get()
        self.queue.task_done()
        if data["type"] == "expired":
            print("Room expired")
            await self.close()
            return None
        return data

    async def exchangeAddr(self,fp=None):
        if self.token and fp:
            print("Waiting for a connection")
            await self.waitFor("user_joined")
            addr = stun.getInfo()
            addr = {"Ip":addr[0],"Port":addr[1],"Fingerprint":fp}
            print("Sending address ...")
            await self.send(json.dumps(addr))
            print("Waiting for address ...")
            data = await self.waitFor("relay")
            data = json.loads(data["data"])
            return (data["Ip"],data["Port"])
        else:
            print("Waiting for address ...")
            data = await self.waitFor("relay")
            addr = stun.getInfo()
            addr = {"Ip":addr[0],"Port":addr[1]}
            print("Sending address ...")
            await self.send(json.dumps(addr))
            data = json.loads(data["data"])
            return (data["Ip"],data["Port"],data["Fingerprint"])

    async def connect(self):
        if self.token:
            self.webs = await ws.connect("wss://"+SERVER+"/ws?id="+self.code+"&token="+self.token)
        else:
            self.webs = await ws.connect("wss://"+SERVER+"/ws?id="+self.code)
        data = json.loads(await self.webs.recv())
        if data["type"] == "successful_connection":
            self.recv_task = asyncio.create_task(self.recvData())
            return True
        else:
            await self.webs.close()
            self.webs = None
            return False

    async def close(self):
        if self.webs:
            self.recv_task.cancel()
            await self.webs.close()

def createRoom():
    code = requests.get("https://"+SERVER+"/create",timeout=3)
    if code.status_code == 200:
        return Room(code.json()["RoomID"],code.json()["OwnerToken"])
    return None

def joinRoom(code,token = None):
    return Room(code,token)



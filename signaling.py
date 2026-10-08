import websockets as ws
import asyncio,aioice
from aioice.candidate import Candidate
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

    async def gatherICE(self,fp = None):
        self.ice_connection = aioice.Connection(
            ice_controlling=True if self.token else False,
            stun_server=("stun.l.google.com", 19302)
        )

        await self.ice_connection.gather_candidates()

        iceData = {
            "ufrag": self.ice_connection.local_username,
            "pwd": self.ice_connection.local_password,
            "candidates": [c.to_sdp() for c in self.ice_connection.local_candidates],
            "fingerprint": fp
        }

        if self.token and fp:
            print("Waiting for a connection")
            await self.waitFor("user_joined")
            print("Sending ice data ...")
            await self.send(json.dumps(iceData))
            print("Waiting for ice data ...")
            data = await self.waitFor("relay")
            data = json.loads(data["data"])
        else:
            print("Waiting for ice data ...")
            data = await self.waitFor("relay")
            print("Sending address ...")
            await self.send(json.dumps(iceData))
            data = json.loads(data["data"])
            fp = data["fingerprint"]
        
        self.ice_connection.remote_username = data["ufrag"]
        self.ice_connection.remote_password = data["pwd"]

        for c_str in data["candidates"]:
            remote_candidate = Candidate.from_sdp(c_str) 
            await self.ice_connection.add_remote_candidate(remote_candidate)

        print("Punching through firewalls via aioice...")
        try:
            await asyncio.wait_for(self.ice_connection.connect(), timeout=15.0)
            print("Hole punched successfully! Direct P2P tunnel established.")
        except asyncio.TimeoutError:
            print("Connection Timeout: Strict firewalls blocked direct P2P connectivity.")
            return False,0,None,None,None
        
        return True,self.ice_connection,fp

    async def exchangeAddr(self,fp=None):
        if self.token and fp:
            print("Waiting for a connection")
            await self.waitFor("user_joined")
            addr = None
            while addr == None:
                addr = stun.getInfo()
                if addr != None:
                    localport = addr[2]
                    addr = addr[0:2]
            addr = {"Ip":addr[0],"Port":addr[1],"Fingerprint":fp}
            print("Sending address ...")
            await self.send(json.dumps(addr))
            print("Waiting for address ...")
            data = await self.waitFor("relay")
            data = json.loads(data["data"])
            if data["Ip"] == addr["Ip"]:
                print("Matching public ip, exchanching local ips...")
                addr = stun.getLocalInfo(True)
                localport = addr[1]
                addr = {"Ip":addr[0],"Port":addr[1]}
                print("Waiting for confirmation...")
                await self.waitFor("relay")
                print("Sending address ...")
                await self.send(json.dumps(addr))
                print("Waiting for address ...")
                data = await self.waitFor("relay")
                data = json.loads(data["data"])
            return (data["Ip"],data["Port"]),localport
        else:
            print("Waiting for address ...")
            data = await self.waitFor("relay")
            addr = None
            while addr == None:
                addr = stun.getInfo()
                if addr != None:
                    localport = addr[2]
                    addr = addr[0:2]
            addr = {"Ip":addr[0],"Port":addr[1]}
            print("Sending address ...")
            await self.send(json.dumps(addr))
            data = json.loads(data["data"])
            fp = data["Fingerprint"]
            if data["Ip"] == addr["Ip"]:
                print("Matching public ip, exchanching local ips...")
                addr = stun.getLocalInfo(False)
                localport = addr[1]
                addr = {"Ip":addr[0],"Port":addr[1]}
                print("Sending confirmation ...")
                await self.send("Exchange Local IPs")
                print("Waiting for address ...")
                data = await self.waitFor("relay")
                print("Sending address ...")
                await self.send(json.dumps(addr))
                data = json.loads(data["data"])
                return (data["Ip"],data["Port"],fp),localport
            else:
                return (data["Ip"],data["Port"],data["Fingerprint"]),localport

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



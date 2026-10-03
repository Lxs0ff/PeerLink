import websockets as ws
import asyncio
import requests
import json

SERVER = "0x1.lxsdev.net"

class Room:
    def __init__(self,code,token = None):
        self.code = code
        self.token = token
        self.webs = None
        self.recv_task = None
        self.queue = asyncio.Queue()

    async def recvData(self):
        try:
            while True:
                data = await self.webs.recv()
                data = json.loads(data)
                await self.queue.put(data)
        except asyncio.CancelledError:
            pass

    async def nextTask(self):
        data = await self.queue.get()
        self.queue.task_done()
        if data["type"] == "expired":
            print("Room expired")
            await self.close()
            return None
        return data

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

def joinRoom(code,token):
    return Room(code,token)

async def main():
    room = createRoom()
    connected = await room.connect()
    if connected:
        print("Connection successfull")
        print("Room ID:", room.code)
        print("Owner Token:", room.token)
        while True:
            data = await room.nextTask()
            if data == None:
                break
            print(data)
    else:
        print("An error happened while connecting to the room")

if __name__ == "__main__":
    asyncio.run(main())


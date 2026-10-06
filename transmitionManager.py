import os,json,hashlib,asyncio,quic

class PacketManager:
    OP_TEXT = b'\x01'
    OP_FILE_CHUNK = b'\x03'
    OP_FILE_REQUEST = b'\x04'
    OP_REQUEST_ACCEPTED = b'\x05'
    OP_REQUEST_DENIED = b'\x06'
    OP_SYSTEM = b'\x09'

    def createMessagePacket(self,message:str):
        return self.OP_TEXT+message.encode("utf-8")

    def createFileRequest(self,pathToFile:str,filename:str):
        filesize = os.path.getsize(pathToFile)
        tid = os.urandom(16)
        info = {"FileName":filename,"FileSize":filesize}
        return self.OP_FILE_REQUEST+tid+json.dumps(info).encode("utf-8"),tid,info

    def createFilePacket(self, tid, data):
        return self.OP_FILE_CHUNK+tid+data

    def createRequestAccepted(self,tid):
        return self.OP_REQUEST_ACCEPTED+tid
    
    def createRequestDenied(self,tid):
        return self.OP_REQUEST_DENIED+tid

    def createHashConfirmation(self,hash,tid):
        info = {"Type":"HashConfirmation","Data":{"Hash":hash, "Tid":tid}}
        return self.OP_SYSTEM+json.dumps(info).encode("utf-8")
    
    def createFileConfirmation(self,status,tid):
        info = {"Type":"FileConfirmation","Data":{"Tid":tid, "Status":status}}
        return self.OP_SYSTEM+json.dumps(info).encode("utf-8")

class TransmitionManager:
    def __init__(self,conf,localport:int,addr=None,fp=None):
        self.downloads = {}
        self.uploads = {}
        self.pendingDownloads = {}
        self.pendingUploads = {}
        self.hashes = {}
        self.uploadStatus = {}
        self.systemPackets = asyncio.Queue()
        self.fileRequests = asyncio.Queue()
        self.conf = conf
        self.localport = localport
        self.addr = addr
        self.fp = fp
        self.networking = quic.QuicNetworking()
        self.packetManager = PacketManager()
        self.running = True

    async def connect(self):
        if self.addr and self.fp:
            success = await self.networking.connectClient(self.conf,self.addr,self.localport,self.fp)
            asyncio.create_task(self.handleData())
            asyncio.create_task(self.handleSystem())
            return success
        else:
            await self.networking.createServer(self.conf, self.localport)
            asyncio.create_task(self.handleData())
            asyncio.create_task(self.handleSystem())
            return True

    def sendMessage(self,message:str):
        self.networking.send(self.packetManager.createMessagePacket(message))

    def requestSendingFile(self,pathToFile:str,fileName:str):
        packet,tid,info = self.packetManager.createFileRequest(pathToFile,fileName)
        self.networking.send(packet)
        self.pendingUploads[tid] = info

    def denyDownload(self,tid):
        if tid in self.pendingDownloads:
            del self.pendingDownloads[tid]
            self.networking.send(self.packetManager.createRequestDenied(tid))

    def acceptDownload(self,tid,path):
        if tid in self.pendingDownloads:
            self.networking.send(self.packetManager.createRequestAccepted(tid))
            info = {
                "FileName":self.pendingDownloads[tid]["FileName"],
                "FileSize":self.pendingDownloads[tid]["FileSize"],
                "BytesWritten":0,
                "Hash":hashlib.sha256(),
                "FileWriter":open(os.path.join(path,self.pendingDownloads[tid]["FileName"]),"ab")
            }
            del self.pendingDownloads[tid]
            self.downloads[tid] = info

    async def handleUpload(self,tid):
        while True:
            chunk = self.uploads[tid]["FileReader"].read(1024)
            if not chunk:
                break
            self.uploads[tid]["Hash"].update(chunk)
            self.uploads[tid]["BytesSent"] += len(chunk)
            self.networking.send(self.packetManager.createFilePacket(tid,chunk))
            await asyncio.sleep(0)
        final_hash = self.uploads[tid]["Hash"].hexdigest()
        self.networking.send(self.packetManager.createHashConfirmation(final_hash, tid))
        self.pendingUploads[tid] = "Waiting Confirmation"
        self.uploads[tid]["FileReader"].close()
        del self.uploads[tid]

    async def handleSystem(self):
        while self.running:
            data = await self.systemPackets.get()
            data = json.loads(data.decode("utf-8"))
            if data["Type"] == "FileConfirmation": 
                self.uploadStatus[data["Data"]["Tid"]] = data["Data"]["Status"]
            elif data["Type"] == "HashConfirmation":
                tid = data["Data"]["Tid"].hex()
                hash = data["Data"]["Hash"]
                if hash == self.hashes[tid]:
                    self.networking.send(self.packetManager.createFileConfirmation("Success",tid))
                else:
                    self.networking.send(self.packetManager.createFileConfirmation("Fail",tid))
                del self.hashes[tid]
            self.systemPackets.task_done()

    async def handleData(self):
        while self.running:
            data = await self.networking.queue.get()
            if data[0:1] == PacketManager.OP_SYSTEM:
                await self.systemPackets.put(data[1:])
            elif data[0:1] == PacketManager.OP_TEXT:
                print(data[1:].decode("utf-8"))
            elif data[0:1] == PacketManager.OP_FILE_REQUEST:
                info = json.loads(data[17:].decode("utf-8"))
                self.pendingDownloads[data[1:17]] = info
                await self.fileRequests.put((data[1:17],info))
            elif data[0:1] == PacketManager.OP_REQUEST_ACCEPTED:
                tid = data[1:17]
                info = {
                    "FilePath":self.pendingUploads[tid]["FilePath"],
                    "FileSize":self.pendingUploads[tid]["FileSize"],
                    "Hash":hashlib.sha256(),
                    "FileReader":open(self.pendingUploads[tid]["FilePath"],"rb"),
                    "BytesSent":0
                }
                del self.pendingUploads[tid]
                self.uploads[tid] = info
                asyncio.create_task(self.handleUpload(tid))
            elif data[0:1] == PacketManager.OP_REQUEST_DENIED:
                tid = data[1:17]
                if tid in self.pendingUploads:
                    del self.pendingUploads[tid]
            elif data[0:1] == PacketManager.OP_FILE_CHUNK:
                tid = data[1:17]
                data = data[17:]
                self.downloads[tid]["Hash"].update(data)
                self.downloads[tid]["FileWriter"].write(data)
                self.downloads[tid]["BytesWritten"] += len(data)
                if self.downloads[tid]["BytesWritten"] == self.downloads[tid]["FileSize"]:
                    self.hashes[tid.hex()] = self.downloads[tid]["Hash"].hexdigest()
                    self.downloads[tid]["FileWriter"].close()
                    del self.downloads[tid]
            self.networking.queue.task_done()

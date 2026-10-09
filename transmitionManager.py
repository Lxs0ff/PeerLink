import os,json,hashlib,asyncio,quic
import aioquic,time

class PacketManager:

    # TODO: add ack N package for uploader backtracking 

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
        info = {"FileName":filename,"FileSize":filesize,"FilePath":pathToFile}
        return self.OP_FILE_REQUEST+tid+json.dumps(info).encode("utf-8"),tid,info

    def createFilePacket(self, tid, data):
        return self.OP_FILE_CHUNK+tid+data

    def createRequestAccepted(self,tid):
        return self.OP_REQUEST_ACCEPTED+tid
    
    def createRequestDenied(self,tid):
        return self.OP_REQUEST_DENIED+tid

    def createHashConfirmation(self,hash,tid):
        info = {"Type":"HashConfirmation","Data":{"Hash":hash, "Tid":tid.hex()}}
        return self.OP_SYSTEM+json.dumps(info).encode("utf-8")
    
    def createFileConfirmation(self,status,tid):
        info = {"Type":"FileConfirmation","Data":{"Tid":tid, "Status":status}}
        return self.OP_SYSTEM+json.dumps(info).encode("utf-8")

class TransmitionManager:
    def __init__(self,conf,conn,fp=None):

        # TODO : ADD go back N, with ack packets for making sure files get send whole, prevent packet dropping and prevent corruption
        # TODO: add N to uploads and downloads dict

        self.downloads = {}
        self.uploads = {}
        self.pendingDownloads = {}
        self.pendingUploads = {}
        self.hashes = {}
        self.uploadStatus = {}
        #self.messageQueue = asyncio.Queue()
        self.systemPackets = asyncio.Queue()
        #self.fileRequests = asyncio.Queue()
        self.conf = conf
        self.conn = conn
        self.fp = fp
        self.networking = quic.QuicNetworking()
        self.packetManager = PacketManager()

        self.messageCallback = None
        self.requestCallback = None
        self.requestDeniedCallback = None
        self.requestAcceptedCallback = None
        self.statusCallback = None
        self.closeCallback = None

        self.running = True

    async def connect(self):
        if self.conf.is_client:
            success = await self.networking.connectClient(self.conf, self.conn, self.fp)
            asyncio.create_task(self.handleData())
            asyncio.create_task(self.handleSystem())
            return success
        await self.networking.createServer(self.conf, self.conn)
        asyncio.create_task(self.handleData())
        asyncio.create_task(self.handleSystem())
        
    def sendMessage(self,message:str):
        self.networking.send(self.packetManager.createMessagePacket(message))

    def requestSendingFile(self,pathToFile:str,fileName:str):
        packet,tid,info = self.packetManager.createFileRequest(pathToFile,fileName)
        self.pendingUploads[tid] = info
        self.networking.send(packet)
        return tid

    def denyDownload(self,tid):
        if tid in self.pendingDownloads:
            del self.pendingDownloads[tid]
            self.networking.send(self.packetManager.createRequestDenied(tid))

    def acceptDownload(self,tid,path):
        if tid in self.pendingDownloads:
            info = {
                "FileName":self.pendingDownloads[tid]["FileName"],
                "FileSize":self.pendingDownloads[tid]["FileSize"],
                "BytesWritten":0,
                "Hash":hashlib.sha256(),
                "FileWriter":open(os.path.join(path,self.pendingDownloads[tid]["FileName"]),"ab")
            }
            self.downloads[tid] = info
            self.networking.send(self.packetManager.createRequestAccepted(tid))
            del self.pendingDownloads[tid]

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

    async def handleSystem(self):
        while self.running:
            data = await self.systemPackets.get()
            data = json.loads(data.decode("utf-8"))
            if data["Type"] == "FileConfirmation": 
                self.uploadStatus[data["Data"]["Tid"]] = data["Data"]["Status"]
                if self.statusCallback:
                    asyncio.create_task(self.statusCallback(data["Data"]["Tid"],data["Data"]["Status"]))
            elif data["Type"] == "HashConfirmation":
                tid = data["Data"]["Tid"]
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
            if data == None:
                break
            elif data[0:1] == PacketManager.OP_SYSTEM:
                await self.systemPackets.put(data[1:])
            elif data[0:1] == PacketManager.OP_TEXT:
                if self.messageCallback:
                    asyncio.create_task(self.messageCallback("Peer > "+data[1:].decode("utf-8")))
                #await self.messagesQueue.put(data[1:].decode("utf-8"))
                pass
            elif data[0:1] == PacketManager.OP_FILE_REQUEST:
                info = json.loads(data[17:].decode("utf-8"))
                self.pendingDownloads[data[1:17]] = info
                if self.requestCallback:
                    asyncio.create_task(self.requestCallback(data[1:17],info["FileName"],info["FileSize"]))
                #await self.fileRequests.put((data[1:17],info))
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
                if self.requestAcceptedCallback:
                    asyncio.create_task(self.requestAcceptedCallback(tid))
            elif data[0:1] == PacketManager.OP_REQUEST_DENIED:
                tid = data[1:17]
                if tid in self.pendingUploads:
                    del self.pendingUploads[tid]
                    if self.requestDeniedCallback:
                        asyncio.create_task(self.requestDeniedCallback(tid))
            elif data[0:1] == PacketManager.OP_FILE_CHUNK:
                tid = data[1:17]
                chunk = data[17:]
                self.downloads[tid]["Hash"].update(chunk)
                self.downloads[tid]["FileWriter"].write(chunk)
                self.downloads[tid]["BytesWritten"] += len(chunk)
                if self.downloads[tid]["BytesWritten"] >= self.downloads[tid]["FileSize"]:
                    self.hashes[tid.hex()] = self.downloads[tid]["Hash"].hexdigest()
                    self.downloads[tid]["FileWriter"].close()
            # TODO: add ack N backtracking OP_ACK_N
            self.networking.queue.task_done()
        if self.closeCallback:
            asyncio.create_task(self.closeCallback("Connection closed"))

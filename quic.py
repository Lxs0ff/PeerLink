import asyncio
import certificates as certif
from aioquic.asyncio import serve
from aioquic.asyncio import connect
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.quic.events import DatagramFrameReceived

class ConnectionProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        self.networking = kwargs.pop("networking", None)
        super().__init__(*args, **kwargs)

    def quic_event_received(self, event):
            if isinstance(event, DatagramFrameReceived):
                if self.networking:
                    asyncio.create_task(self.networking.queue.put(event.data))
    
    def send(self,data):
        self._quic.send_datagram_frame(data)
        self.transmit()

class QuicNetworking():
    def __init__(self):
        self.conn = None
        self.connCtx = None
        self.queue = asyncio.Queue()

    def newConn(self,*args,**kwargs):
        self.conn = ConnectionProtocol(*args, **kwargs, networking=self)
        return self.conn

    def send(self,data):
        self.conn.send(data)

    async def createServer(self,cfg,localport):
        await serve("127.0.0.1", localport, configuration=cfg,create_protocol=lambda *args, **kwargs: self.newConn(*args, **kwargs))

    async def connectClient(self,cfg,addr,localport,fp):
        self.connCtx = connect(
            addr[0], 
            addr[1], 
            configuration=cfg,
            local_port=localport,
            create_protocol=lambda *args, **kwargs: ConnectionProtocol(*args, **kwargs, networking=self)
        )
        self.conn = await self.connCtx.__aenter__()
        if not certif.peer_matches(self.conn, fp):
            self.connCtx.close(error_code=1, reason_phrase="fingerprint mismatch")
            return False
        return True

    async def close(self):
        if self.networking.conn:
            self.networking.conn.close()

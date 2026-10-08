import asyncio
import certificates as certif
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.events import DatagramFrameReceived,ConnectionTerminated
from aioquic.asyncio.server import QuicServer
from aioquic.quic.connection import QuicConnection
from ice_transport import IceTransport, pump, DUMMY_ADDR

class ConnectionProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        self.networking = kwargs.pop("networking", None)
        super().__init__(*args, **kwargs)

    def quic_event_received(self, event):
            if isinstance(event, DatagramFrameReceived):
                if self.networking:
                    asyncio.create_task(self.networking.queue.put(event.data))
            elif isinstance(event, ConnectionTerminated):
                if self.networking:
                    asyncio.create_task(self.networking.queue.put(None))

    
    def send(self,data):
        self._quic.send_datagram_frame(data)
        self.transmit()

class QuicNetworking:
    def __init__(self):
        self.conn = None
        self.queue = asyncio.Queue()
        self._pump = None

    async def createServer(self, cfg, ice):
        server = QuicServer(
            configuration=cfg,
            create_protocol=lambda *a, **kw: self._newConn(*a, **kw),
        )
        server.connection_made(IceTransport(ice))
        self._pump = asyncio.create_task(pump(ice, server))

    async def connectClient(self, cfg, ice, fp):
        proto = ConnectionProtocol(QuicConnection(configuration=cfg), networking=self)
        proto.connection_made(IceTransport(ice))
        self._pump = asyncio.create_task(pump(ice, proto))
        self.conn = proto
        proto.connect(DUMMY_ADDR)
        await proto.wait_connected()
        return certif.peer_matches(proto, fp)

    def _newConn(self, *args, **kwargs):
        self.conn = ConnectionProtocol(*args, **kwargs, networking=self)
        return self.conn

    def send(self, data):
        self.conn.send(data)
        
    async def close(self):
        if self.conn:
            self.conn.close()
        if self._pump:
            self._pump.cancel()

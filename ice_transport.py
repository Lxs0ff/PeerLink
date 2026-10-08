import asyncio

DUMMY_ADDR = ("ice", 0)

class IceTransport(asyncio.DatagramTransport):
    def __init__(self, ice):
        super().__init__()
        self.ice = ice
        self._closing = False

    def sendto(self, data, addr=None):
        if not self._closing:
            asyncio.ensure_future(self.ice.send(bytes(data)))

    def get_extra_info(self, name, default=None):
        return ("0.0.0.0", 0) if name == "sockname" else default

    def close(self):
        self._closing = True

    def is_closing(self):
        return self._closing

async def pump(ice, target):
    try:
        while True:
            data = await ice.recv()
            target.datagram_received(data, DUMMY_ADDR)
    except (ConnectionError, asyncio.CancelledError):
        pass
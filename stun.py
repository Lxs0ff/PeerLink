import socket 
import struct
import os

STUN_SERVER = "stun.cloudflare.com"
STUN_PORT = 3478
MAGIC_COOKIE = 0x2112A442
DEFAULT_HEADER = struct.pack("!HHI",0x0001,0,MAGIC_COOKIE)

def getInfo():
    socket.gethostbyname(STUN_SERVER)
    tid = os.urandom(12)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    try:
        sock.sendto(DEFAULT_HEADER+tid,(STUN_SERVER,STUN_PORT))
        data,addr = sock.recvfrom(1024)
    except:
        return None
    finally:
        sock.close()
    msg_type, msg_len = struct.unpack("!HH", data[0:4])
    if msg_type != 0x0101 or data[8:20] != tid:
        return None
    offset = 20
    value = None
    while offset < len(data):
        type_data, len_data = struct.unpack("!HH", data[offset:offset+4])
        if type_data == 0x0020:
            value = data[offset+4:offset+4+len_data]
            break
        offset+=4+len_data+(-len_data%4)
    if value == None or value[1] != 0x01:
        return None
    ip = (int.from_bytes(value[4:8],"big")^MAGIC_COOKIE).to_bytes(4, "big")
    ip = socket.inet_ntoa(ip)
    port = int.from_bytes(value[2:4],"big")^(MAGIC_COOKIE>>16)
    return (ip,port)

if __name__ == "__main__":
    print(getInfo())
import flet as ft
import signaling
import certificates as certif
import stun
import asyncio
import quic

class App:
    def __init__(self):
        self.page = None

        # Page Elements Declared as None 
        self.create_button = None
        self.join_button = None
        self.console = None
        self.code_label = None
        self.room_code_field = None

        # Other usefull variables
        self.room_code = None

    async def __call__(self, page: ft.Page):
        self.page = page
        self.page.title = "Cutout"
        self.page.theme_mode = ft.ThemeMode.DARK
        
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        await self.showHomeScreen()

    async def log_message(self, text: str):
        if self.console != None:
            self.console.controls.append(ft.Text(text, font_family="monospace", size=12))
            self.page.update()

    async def showHomeScreen(self):
        self.page.clean()

        self.create_button = ft.FilledButton(content="Create Room", on_click=self.createRoom, expand=True)
        self.join_button = ft.FilledButton(content="Join Room", on_click=self.joinRoom)
        self.room_code_field = ft.TextField(label="Room Code", hint_text="example-code-1")
        
        connection_page = ft.SafeArea(
                    expand=True,
                    width=430,
                    content=ft.Container(
                        content= ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[self.create_button],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Divider(height=2, thickness=.5),
                                ft.Row(
                                    controls=[self.room_code_field, self.join_button],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.Alignment.CENTER,
                    ),
            )
        
        self.page.window.resizable = False
        self.page.window.maximizable = False
        self.page.window.width = 500
        self.page.window.height = 200
        self.page.title = "PeerLink"
        self.page.add(connection_page)

    async def showConnecting(self):
        self.page.clean()

        self.code_label = ft.Text(self.room_code,expand=True)
        copy_code_button = ft.FilledButton(
            content="Copy Room Code",
            icon=ft.Icons.CONTENT_COPY,
            action=ft.CopyToClipboard(self.room_code) 
        )
        self.console = ft.ListView(auto_scroll=True,expand=True)

        connection_page = ft.SafeArea(
                            expand=True,
                            width=430,
                            content=ft.Container(
                                content= ft.Column(
                                    controls=[
                                        ft.Row(
                                            controls=[self.code_label,copy_code_button],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                        ft.Divider(height=2, thickness=.5),
                                        ft.Container(
                                            height=200, 
                                            border=ft.Border.all(width=0.5, color="white24"),
                                            padding=10,
                                            content=self.console
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                alignment=ft.Alignment.CENTER,
                            ),
            )
        self.page.window.resizable = False
        self.page.window.maximizable = False
        self.page.window.width = 400
        self.page.window.height = 325
        self.page.add(connection_page)


    async def joinRoom(self,e):
        if self.room_code_field.value == "":return
        try:
            self.page.title = "PeerLink - Client"
            self.room_code = self.room_code_field.value
            await self.showConnecting()
            room = signaling.joinRoom(code=self.room_code)
            connected = await room.connect()
            if connected:
                conf = certif.createConfig(self.room_code)
                await self.log_message("Connection successfull")
                addr,localport = await room.exchangeAddr()
                fp = addr[2]
                addr = addr[0:2]
                await self.log_message("Peer Address: "+str(addr[0:2]))
                await self.log_message("Host Fingerprint:"+fp)
                await self.log_message("Hole Punching ...")
                await stun.holePunching(localport,addr)
                await self.log_message("Hole Punched !")
                Client = quic.QuicNetworking()
                if addr[0] == stun.getLocalInfo(False)[0]: 
                    addr = ("127.0.0.1",addr[1])
                await self.log_message("Connecting to addr: "+str(addr))
                success = await Client.connectClient(conf,addr,localport,fp)
                if not success:
                    await self.log_message("Could not connect to server, invalid fingerprint...")
                    await self.showHomeScreen()
                else:
                    await self.log_message("Sucessfully connected to server!")
                    #TODO: Make main gui for when connected
            else:
                await self.log_message("An error happened while connecting to the room")
                await self.showHomeScreen()
        except:
            await self.showHomeScreen()

    async def createRoom(self,e):
        self.page.title = "PeerLink - Host"
        room = signaling.createRoom()
        connected = await room.connect()
        self.room_code = room.code
        await self.showConnecting()
        if connected:
            conf, cert, key , fp = certif.createHostConfig(room.code)
            await self.log_message("Connection successfull")
            await self.log_message("Room ID: "+room.code)
            await self.log_message("Owner Token: "+room.token)
            addr,localport = await room.exchangeAddr(fp)
            await self.log_message("Peer Address: "+str(addr))
            await self.log_message("Hole Punching ...")
            await stun.holePunching(localport,addr)
            await self.log_message("Hole Punched !")
            Server = quic.QuicNetworking()
            await Server.createServer(conf,localport)
            #TODO: Make main gui for when connected
        else:
            await self.log_message("An error happened while connecting to the room")
            self.showHomeScreen()

async def main(page: ft.Page):
    app = App()
    await app(page)
    
ft.run(main)
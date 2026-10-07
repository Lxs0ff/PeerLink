import flet as ft
import certificates as certif
import quic,stun,signaling
import asyncio
from transmitionManager import TransmitionManager

class App:
    def __init__(self):

        # GLOBAL CLASS TODO
        # TODO: Make background loop for handeling uploads, downloads requests
        # TODO: Make background loop for handeling messages, notifications 
        # TODO: Make Download tab with accepting and denying requests in a list view and download progress in another
        # TODO: Make Upload tab with sending requests and file upload progress in a list view
        
        self.page = None
        maincolor = "#33ff66"
        seccolor = "#ffb000"
        outlinecolor = "#d8d8d8"
        self.mono = ft.TextStyle(font_family="Jersey25", color=maincolor, size=20)
        self.theme = ft.Theme(
        font_family="Jersey25",
        color_scheme=ft.ColorScheme(
            primary=maincolor,
            on_primary="#050805",
            secondary=seccolor,
            surface="#050805",
            on_surface=maincolor,
            outline=outlinecolor,
            error="#ff5555",
        ),
        text_theme=ft.TextTheme(
            body_large=self.mono, body_medium=self.mono, body_small=self.mono,
            title_large=self.mono, title_medium=self.mono, label_large=self.mono,
        ),
    )

        # Page Elements Declared as None 
        self.create_button = None
        self.join_button = None
        self.code_label = None
        self.room_code_field = None
        self.message_text_area = None

        self.console = ft.ListView(auto_scroll=True,expand=True)

        self.room_code = None
        self.transmitionManager = None

    async def __call__(self, page: ft.Page):
        self.page = page
        self.page.title = "Cutout"
        self.page.fonts = {"Jersey25": "fonts/Jersey25-Regular.ttf"}
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = self.theme
        self.page.dark_theme = self.theme
        
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        await self.showConnected()

        #await self.showHomeScreen()

        self.notification_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(""),
                    ft.Text(""),
                    ]
                ),
            padding=10,
            border_radius=5,
            visible=False,
            animate_opacity=300,
            opacity=0,
        )

        self.notification_layer = ft.Stack(
                controls=[
                    ft.Row(
                        controls=[self.notification_box],
                        alignment=ft.MainAxisAlignment.END,
                    )
                ],
                expand=True,
        )

        #self.setNotif("Sup","Test")
        #await self.showNotif(2)

    async def log_message(self, text: str):
        if self.console != None:
            self.console.controls.append(ft.Text(text, size=12))
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

    def sendMessage(self):
        if self.transmitionManager and self.message_text_area:
            self.transmitionManager.sendMessage(self.message_text_area.value)
            self.log_message("You > "+self.message_text_area.value)

    async def showNotif(self,time):
        self.page.overlay.append(self.notification_layer)
        self.notification_box.visible = True
        self.notification_box.opacity = 1
        self.page.update()

        await asyncio.sleep(time)

        self.notification_box.opacity = 0
        self.page.update()
        
        await asyncio.sleep(0.3) 
        self.notification_box.visible = False
        self.page.update()

    def setNotif(self, title:str, message:str):
        self.notification_box = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title),
                    ft.Text(message),
                    ]
                ),
            padding=10,
            border_radius=5,
            visible=False,
            animate_opacity=300,
            opacity=0,
        )

        self.notification_layer = ft.Stack(
                controls=[
                    ft.Row(
                        controls=[self.notification_box],
                        alignment=ft.MainAxisAlignment.START,
                    )
                ],
                expand=True,
        )

    async def showConnected(self):
            self.page.clean()
    
            self.message_text_area = ft.TextField(label="Chat Box", expand=True, hint_text="Hi !")
            send_message_button = ft.OutlinedButton(
                content="Send Message",
                icon=ft.Icons.SEND_SHARP,
                on_click=self.sendMessage,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=4),
                ),
                height=50
            )
            
            connection_page = ft.SafeArea(
                                expand=True,
                                content=ft.Tabs(
                                    length=3,
                                    expand=True,
                                    content=ft.Column(
                                        controls=[
                                            ft.TabBar(
                                                scrollable=False,
                                                tabs=[
                                                    ft.Tab(
                                                        label="Chat", 
                                                        icon=ft.Icons.CHAT_SHARP,
                                                        expand=True
                                                    ),
                                                    ft.Tab(
                                                        label="Uploads", 
                                                        icon=ft.Icons.FILE_UPLOAD,
                                                        expand=True
                                                    ),
                                                    ft.Tab(
                                                        label="Downloads", 
                                                        icon=ft.Icons.DOWNLOAD,
                                                        expand=True
                                                    ),
                                                ]
                                            ),
                                            ft.TabBarView(
                                                expand=True,
                                                controls=[
                                                    ft.Container(
                                                        alignment=ft.Alignment.CENTER,
                                                        content = ft.Column(
                                                            alignment=ft.MainAxisAlignment.CENTER,
                                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                            controls = [
                                                                ft.Container(
                                                                    expand = True,
                                                                    border=ft.Border.all(width=0.5, color="white24"),
                                                                    padding=10,
                                                                    content=self.console
                                                                ),
                                                                ft.Divider(height=2, thickness=.5),
                                                                ft.Row(
                                                                    controls=[self.message_text_area,send_message_button],
                                                                    alignment=ft.MainAxisAlignment.CENTER,
                                                                ),
                                                            ]
                                                        )
                                                    ),
                                                    ft.Container(
                                                        alignment=ft.Alignment.CENTER,
                                                        content=ft.Text("Uploads"),
                                                    ),
                                                    ft.Container(
                                                        alignment=ft.Alignment.CENTER,
                                                        content=ft.Text("Downloads"),
                                                    ),
                                                ],
                                            ),
                                            
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ),
                )
            self.page.window.resizable = False
            self.page.window.maximizable = False
            self.page.window.width = 800
            self.page.window.height = 650
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
                    self.transmitionManager = None
                else:
                    await self.log_message("Sucessfully connected to server!")
                    await self.showConnected()
                    self.transmitionManager = TransmitionManager(conf,localport,addr,fp)
                    await self.transmitionManager.connect()
            else:
                await self.log_message("An error happened while connecting to the room")
                await self.showHomeScreen()
                self.transmitionManager = None
        except:
            await self.showHomeScreen()
            self.transmitionManager = None

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
            await self.showConnected()
            self.transmitionManager = TransmitionManager(conf,localport,addr)
            await self.transmitionManager.connect()
        else:
            await self.log_message("An error happened while connecting to the room")
            self.showHomeScreen()
            self.transmitionManager = None

async def main(page: ft.Page):
    app = App()
    await app(page)
    
ft.run(main, assets_dir="assets")
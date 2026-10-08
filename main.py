import flet as ft
import certificates as certif
import quic,stun,signaling,os,asyncio
from transmitionManager import TransmitionManager

def format_bytes(size_in_bytes):
    if size_in_bytes == 0: return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024.0
        unit_index += 1
    return f"{size_in_bytes:.2f} {units[unit_index]}"

class App:
    def __init__(self):
        self.page = None
        maincolor = "#03e33b"
        seccolor = "#ffb000"
        outlinecolor = "#efebeb"
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

        self.uploadList = None
        self.uploadTIDS = []
        self.uploadCards = {}

        self.downloadList = None
        self.downloadTIDS = []
        self.downloadCards = {}

        self.console = ft.ListView(auto_scroll=True,expand=True)
        self.filePicker = ft.FilePicker()

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

        asyncio.create_task(self.updateDownloadCards())
        asyncio.create_task(self.updateUploadCards())

        #await self.showConnected()
        await self.showHomeScreen()

    async def updateDownloadCards(self):
        while True:
            for tid in self.downloadTIDS[:]:
                fileSize = self.transmitionManager.downloads[tid]["FileSize"]
                bytesWritten = self.transmitionManager.downloads[tid]["BytesWritten"]
                progress = bytesWritten/fileSize
                self.downloadCards[tid]["progress"]["text"].value = f"{format_bytes(bytesWritten)}/{format_bytes(fileSize)}"
                self.downloadCards[tid]["progress"]["ring"].value = progress
                if progress == 1:
                    self.downloadTIDS.remove(tid)
            self.page.update()
            await asyncio.sleep(0.03)

    async def updateUploadCards(self):
        while True:
            for tid in self.uploadTIDS[:]:
                fileSize = self.transmitionManager.uploads[tid]["FileSize"]
                bytesSent = self.transmitionManager.uploads[tid]["BytesSent"]
                progress = bytesSent/fileSize
                self.uploadCards[tid]["progress"]["text"].value = f"{format_bytes(bytesSent)}/{format_bytes(fileSize)}"
                self.uploadCards[tid]["progress"]["ring"].value = progress
                if progress == 1:
                    self.uploadTIDS.remove(tid)
            self.page.update()
            await asyncio.sleep(0.03)

    async def log_message(self, text: str):
        self.console.controls.append(ft.Text(text, size=12))
        self.page.update()

    def addUploadCard(self,tid,fileName,fileSize):
        status = ft.Text(value="Waiting for confirmation ...")
        progressRing = ft.ProgressRing()
        progressText = ft.Text(value="")
        card = ft.Card(
            content=ft.Container(
                padding=10,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls = [
                                ft.Text(value=fileName),
                                ft.Text(value=format_bytes(fileSize)),
                            ]
                        ),
                        ft.Row(
                            controls = [
                                status,
                                ft.VerticalDivider(width=20),
                                progressRing,
                                progressText
                            ]
                        ),
                    ]
                )
            )
        )
        self.uploadCards[tid] = {
            "card":card,
            "status":status,
            "progress":{
                "ring":progressRing,
                "text":progressText
            },
            "fileName":fileName,
            "fileSize":fileName,
        }
        self.uploadList.controls.append(card)
        self.page.update()

    def addDownloadCard(self,tid,fileName,fileSize):
        status = ft.Text(value="Waiting for confirmation ...")
        progressRing = ft.ProgressRing()
        progressText = ft.Text(value="")

        acceptButton = ft.OutlinedButton(
            content="Accept Download",
            icon=ft.Icons.CHECK,
            on_click=self.acceptDownload,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=4),
            ),
            height=50,
            data={"tid":tid}
        )

        denyButton = ft.OutlinedButton(
            content="Deny Download",
            icon=ft.Icons.DO_NOT_DISTURB,
            on_click=self.denyDownload,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=4),
            ),
            height=50,
            data={"tid":tid}
        )

        buttonRow = ft.Row(
            controls=[
                acceptButton,
                denyButton
            ]
        )
        col = ft.Column(
            controls=[
                ft.Row(
                    controls = [
                        ft.Text(value=fileName),
                        ft.Text(value=format_bytes(fileSize)),
                    ]
                ),
                ft.Row(
                    controls = [
                        status,
                        ft.VerticalDivider(width=20),
                        progressRing,
                        progressText
                    ]
                ),
                buttonRow
            ]
        )
        card = ft.Card(
            content=ft.Container(
                padding=10,
                content=col
            )
        )
        
        self.downloadCards[tid] = {
            "card":card,
            "status":status,
            "progress":{
                "ring":progressRing,
                "text":progressText
            },
            "buttons":buttonRow,
            "col":col
        }
        self.downloadList.controls.append(card)
        self.page.update()

    async def showHomeScreen(self):
        self.page.window.resizable = False
        self.page.window.maximizable = False
        self.page.window.width = 500
        self.page.window.height = 200
        self.page.title = "PeerLink"
        self.page.clean()
        
        self.create_button = ft.FilledButton(content="Create Room", on_click=self.createRoom, expand=True)
        self.join_button = ft.FilledButton(content="Join Room", on_click=self.joinRoom)
        self.room_code_field = ft.TextField(label="Room Code", hint_text="example-code-1")
        
        connection_page = ft.SafeArea(
            expand=True,
            width=430,
            content=ft.Container(
                alignment=ft.Alignment.CENTER, 
                content= ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                ),
            ),
        )
        self.page.add(connection_page)

    async def showConnecting(self):
        self.page.window.resizable = False
        self.page.window.maximizable = False
        self.page.window.width = 400
        self.page.window.height = 325
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
                alignment=ft.Alignment.CENTER,
                content= ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                ),
            ),
        )
        self.page.add(connection_page)

    def denyDownload(self,e):
        tid = e.control.data["tid"]
        self.downloadList.controls.remove(self.downloadCards[tid])
        del self.downloadCards[tid]
        self.transmitionManager.denyDownload(tid)
        self.page.update()

    async def acceptDownload(self,e):
        tid = e.control.data["tid"]
        path = await self.filePicker.get_directory_path()
        if not path:return
        self.downloadTIDS.append(tid)
        download_info = self.transmitionManager.downloads.get(tid)
        if download_info is None:
            bytes_written = 0
            file_size = 0
            text = "..."
        else:
            bytes_written = download_info.get("BytesWritten", 0)
            file_size = download_info.get("FileSize", 0)
            text = f"{format_bytes(bytes_written)}/{format_bytes(file_size)}"
        self.downloadCards[tid]["col"].controls.remove(self.downloadCards[tid]["buttons"])
        self.downloadCards[tid]["status"].value = "Downloading ..."
        self.downloadCards[tid]["progress"]["ring"].value = 0.01
        self.downloadCards[tid]["progress"]["text"].value = text
        self.transmitionManager.acceptDownload(tid,path)
        self.page.update()

    async def sendMessage(self, e):
        if self.transmitionManager:
            self.transmitionManager.sendMessage(self.message_text_area.value)
            await self.log_message("You > "+self.message_text_area.value)

    async def pickFile(self, e):
        files = await self.filePicker.pick_files()
        await self.log_message(f"Uploads > Request sent: {files[0].name} ({format_bytes(os.path.getsize(files[0].path))})")
        tid = self.transmitionManager.requestSendingFile(files[0].path,files[0].name)
        self.addUploadCard(tid,files[0].name,os.path.getsize(files[0].path))

    async def closeCall(self,reason):
        await self.showHomeScreen()
        self.transmitionManager = None
        self.console.controls.clear()

    async def requestCall(self,tid,fileName,fileSize):
        await self.log_message(f"Downloads > New file request: {fileName} ({format_bytes(fileSize)})")
        self.addDownloadCard(tid,fileName,fileSize)

    async def requestDeniedCall(self,tid):
        self.uploadCards[tid]["status"].value = "Request Denied"
        self.uploadCards[tid]["progress"]["ring"].value = 0
        self.page.update()

    async def requestAcceptedCall(self,tid):
        self.uploadTIDS.append(tid)
        self.uploadCards[tid]["status"].value = "Uploading ... "
        self.uploadCards[tid]["progress"]["ring"].value = 0.01
        self.uploadCards[tid]["progress"]["text"].value = f"{format_bytes(self.transmitionManager.uploads[tid]["BytesSent"])}/{format_bytes(self.transmitionManager.uploads[tid]["FileSize"])}"
        self.page.update()

    async def statusCall(self,tid,status):
        tid = bytes.fromhex(tid)
        await self.log_message(f"Uploads > New upload status: {self.uploadCards[tid]["fileName"]} -> {status}")
        self.uploadCards[tid]["status"].value = status
        if status == "Success":
            self.uploadCards[tid]["progress"]["ring"].value = 1
            self.uploadCards[tid]["progress"]["text"].value = f"{format_bytes(self.uploadCards[tid]["fileSize"])}/{format_bytes(self.uploadCards[tid]["fileSize"])}"
            self.uploadTIDS.remove(tid)
        elif status == "Failed":
            self.uploadCards[tid]["progress"]["ring"].value = None
            self.uploadCards[tid]["progress"]["text"].value = ""
            self.uploadTIDS.remove(tid)
        self.page.update()

    async def setupCallbacks(self):
        self.transmitionManager.messageCallback = self.log_message
        self.transmitionManager.closeCallback = self.closeCall
        self.transmitionManager.requestCallback = self.requestCall
        self.transmitionManager.requestAcceptedCallback = self.requestAcceptedCall
        self.transmitionManager.requestDeniedCallback = self.requestDeniedCall
        self.transmitionManager.statusCallback = self.statusCall

    async def showConnected(self):
            self.page.window.resizable = False
            self.page.window.maximizable = False
            self.page.window.width = 800
            self.page.window.height = 650
            self.page.clean()

            #Chat Tab
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

            #Uploads Tab

            self.uploadList = ft.ListView(auto_scroll=True,expand=True)

            uploadFileButton = ft.OutlinedButton(
                content="Upload File",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=self.pickFile,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=4),
                ),
                height=50,
                width=self.page.window.width
            )

            #Downloads Tab

            self.downloadList = ft.ListView(auto_scroll=True,expand=True)
            
            connection_page = ft.SafeArea(
                expand=True,
                content=ft.Tabs(
                    length=3,
                    expand=True,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.TabBar(
                                scrollable=False,
                                tabs=[
                                    ft.Tab(
                                        label="Chat", 
                                        icon=ft.Icons.CHAT_SHARP,
                                        expand=True,
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
                                                    expand=True,
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
                                        content=ft.Column(
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            controls = [
                                                ft.Container(
                                                    expand=True,
                                                    height=200, 
                                                    border=ft.Border.all(width=0.5, color="white24"),
                                                    padding=10,
                                                    content=self.uploadList,
                                                ),
                                                ft.Divider(height=2, thickness=.5),
                                                uploadFileButton
                                            ]
                                        )
                                    ),
                                    ft.Container(
                                        alignment=ft.Alignment.CENTER,
                                        content= ft.Container(
                                            expand=True,
                                            border=ft.Border.all(width=0.5, color="white24"),
                                            padding=10,
                                            content=self.downloadList,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            )
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
                await self.log_message("Trying to establish a p2p connection ...")
                success, conn, fp = await room.gatherICE()
                if not success:
                    await self.log_message("P2P Connection failed :()")
                    await self.showHomeScreen()
                    self.transmitionManager = None
                await self.log_message("P2P Connection successfully established !")
                self.transmitionManager = TransmitionManager(conf,conn,fp)
                success = await self.transmitionManager.connect()
                if not success:
                    await self.log_message("Could not connect to server, invalid fingerprint...")
                    await self.showHomeScreen()
                    self.transmitionManager = None
                else:
                    await self.log_message("Sucessfully connected to server!")
                    await self.setupCallbacks()
                    await self.showConnected()
            else:
                await self.log_message("An error happened while connecting to the room")
                await self.showHomeScreen()
                self.transmitionManager = None
        except Exception as e:
            print(e)
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
            success, conn, fp = await room.gatherICE(fp)
            if not success:
                await self.log_message("P2P Connection failed :()")
                await self.showHomeScreen()
                self.transmitionManager = None
            await self.log_message("P2P Connection successfully established !")
            self.transmitionManager = TransmitionManager(conf,conn)
            await self.transmitionManager.connect()
            await self.setupCallbacks()
            await self.showConnected()
        else:
            await self.log_message("An error happened while connecting to the room")
            self.showHomeScreen()
            self.transmitionManager = None

async def main(page: ft.Page):
    app = App()
    await app(page)
    
ft.run(main, assets_dir="assets")
import sys, datetime
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QDialog, QApplication, QTextEdit, QLineEdit
import socket, struct
from threading import Thread 
from PyQt5.QtCore import Qt
import PIL.Image as Image
import io
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

conn=None
class Window(QDialog):
    def __init__(self):
        super().__init__()
        self.flag=0
        self.private_key = ""
        self.client_public_key = ""
        self.setWindowTitle("SERVER")

        # conversation box
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("background-color: #E7E1D8; border-radius: 7px;")
        font=self.chat.font()
        font.setPointSize(10)
        self.chat.setFont(font)

        # edit line box
        self.editbox=QLineEdit(self)
        self.editbox.setStyleSheet("background-color: #E7E1D8; border-radius: 8px;")
        self.editbox.setFixedHeight(30)

        fonteditbox = self.editbox.font()
        fonteditbox.setPointSize(10)
        self.editbox.setFont(fonteditbox)

        # icons buttons
        self.send_icon = QtGui.QIcon('./src/envoyer.png')
        self.file_icon = QtGui.QIcon('./src/paperclip.png')
        self.micro_icon = QtGui.QIcon('./src/mic.png')

        self.send_button = QtWidgets.QPushButton()
        self.file_button = QtWidgets.QPushButton()
        self.micro_button = QtWidgets.QPushButton()
        
        self.send_button.setIcon(self.send_icon)
        self.file_button.setIcon(self.file_icon)
        self.micro_button.setIcon(self.micro_icon)

        # buttons parameters
        self.micro_button.setStyleSheet("background-color: #0A7F6A; color: white; border-radius : 10px; border : 2px solid black;")
        self.micro_button.clicked.connect(self.send)
        self.file_button.setStyleSheet("background-color: #0A7F6A; color: white; border-radius : 10px; border : 2px solid black;")
        self.file_button.clicked.connect(self.browse_image)
        self.send_button.setStyleSheet("background-color: #0A7F6A; color: white; border-radius : 10px; border : 2px solid black;")
        self.send_button.clicked.connect(self.send)



        # VBox (chat part)
        self.chatBody = QtWidgets.QVBoxLayout(self)
        self.chatBody.addWidget(self.chat)
        self.chatBody.addWidget(self.editbox)

        # HBox (buttons)
        self.bottom = QtWidgets.QHBoxLayout()
        
        self.bottom.addWidget(self.send_button)
        self.bottom.addWidget(self.file_button)
        self.bottom.addWidget(self.micro_button)
        
        
        #englobe HBox as the bottom of VBox
        self.chatBody.addLayout(self.bottom)

    def send(self):
        text=self.editbox.text().strip()
        global conn
        timestamp = datetime.datetime.now().strftime("%H:%M")
        text1 = "\n["+timestamp+"] - server\n" + text
        format = QtGui.QTextBlockFormat()
        cursor = window.chat.textCursor()
        format.setAlignment(Qt.AlignRight)
        cursor.insertBlock(format)
        cursor.insertText(text1)
        ciphertext = self.client_public_key.encrypt(text.encode('utf-8'), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        
        conn.send(ciphertext)
        self.editbox.clear()

    def browse_image(self):
            timestamp = datetime.datetime.now().strftime("%H:%M")
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.ReadOnly
            file_name, _ = QtWidgets.QFileDialog.getOpenFileName(None,"QFileDialog.getOpenFileName()", "","Images (*.png *.xpm *.jpg *.bmp);;All Files (*)", options=options)
            
            with open(file_name, 'rb') as f:
                data = f.read()
                ciphertext = self.client_public_key.encrypt("image incoming".encode('utf-8'), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        
                conn.send(ciphertext)
                file_size = len(data)
                # send the size of the file as a 4-byte integer
                conn.sendall(struct.pack("!I", file_size))
                conn.sendall(data)
                print("File sent successfully. ok")
                print("size sent :", file_size)
            if file_name:
                image = QtGui.QPixmap(file_name)
                image = image.scaled(125,125)
                self.chat.document().addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(file_name), image)
                format = QtGui.QTextBlockFormat()
                text = "\n[" + timestamp + "] - server\n"
                cursor = self.chat.textCursor()
                format.setAlignment(Qt.AlignRight)
                cursor.insertBlock(format)
                cursor.insertText(text)
                cursor.insertHtml("<img src='{}' width='125' height='125'/>".format(file_name))
                

    def receive_image(self):
        global conn
    
        # receive the size of the file as a 4-byte integer
        file_size = struct.unpack("!I", conn.recv(4))[0]
        file_path = "./received/{}.png".format(datetime.datetime.now().strftime("%H-%M-%S").replace(":", "-"))
        print(file_path)
        with open(file_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                data = conn.recv(4096)
                bytes_received += len(data)
                f.write(data)
            
        return file_path

class ServerThread(Thread):
    def __init__(self,window): 
        Thread.__init__(self)
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.window=window

 
    def run(self): 
        TCP_IP = '25.49.111.235' 
        TCP_PORT = 80
        BUFFER_SIZE = 1024
        tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        tcpServer.bind((TCP_IP, TCP_PORT)) 
        threads = [] 
        
        tcpServer.listen(4) 
        print("[#] Server is up! : waiting for clients...") 
        while True:
            
            global conn
            (conn, (ip,port)) = tcpServer.accept() 
            client_public_key = serialization.load_pem_public_key(conn.recv(BUFFER_SIZE), backend=default_backend())
            conn.send(self.public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))
            window.client_public_key = client_public_key
            newthread = ClientThread(ip,port,window,self.private_key,client_public_key) 
            newthread.start() 
            threads.append(newthread) 
        
        #if many connections
        for t in threads: 
            t.join() 


class ClientThread(Thread): 
 
    def __init__(self,ip,port,window, private_key, client_public_key): 
        Thread.__init__(self) 
        self.window=window
        self.ip = ip 
        self.port = port
        self.private_key = private_key
        self.client_public_key = client_public_key
        print("[+] New challenger detected!\n[+] ip: " + ip + "\n[+] port: " + str(port)) 
 
    def run(self): 
        
        while True :  
            global conn
            data = conn.recv(4096)
            try:
                plaintext = self.private_key.decrypt(data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))        
            except:
                pass
            timestamp = datetime.datetime.now().strftime("%H:%M")
            if plaintext.decode('utf-8') == "image incoming":
                file_name = window.receive_image()
                with open(file_name, "rb") as f:
                    print("size received : ", len(f.read()))
                    print("File received successfully.2")
                if file_name:
                    image = QtGui.QPixmap(file_name)
                    print("image pas resized")
                    image = image.scaled(125,125)
                    print("image resized")
                    window.chat.document().addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(file_name), image)
                    format = QtGui.QTextBlockFormat()
                    cursor = window.chat.textCursor()
                    format.setAlignment(Qt.AlignLeft)
                    cursor.insertBlock(format)
                    cursor.insertText("\n[" + timestamp + "] - client \n")
                    cursor.insertHtml("<img src='{}' width='125' height='125'/>".format(file_name))
            else:         
                text = "\n["+timestamp+"] - client\n" + plaintext.decode("utf-8")
                format = QtGui.QTextBlockFormat()
                cursor = window.chat.textCursor()
                format.setAlignment(Qt.AlignLeft)
                cursor.insertBlock(format)
                cursor.insertText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.resize(360,640)
    window.setStyleSheet("background-color: #0A7F6A;")
    serverThread=ServerThread(window)
    serverThread.start()
    window.exec()
    sys.exit(app.exec_())
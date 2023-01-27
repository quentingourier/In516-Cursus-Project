### !!! activate env : diffenv\Lib\Scripts\activate.bat !!! ###

# For communication
import sys, datetime
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QDialog, QApplication, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt
import socket, struct
from threading import Thread 
import threading
from pushbullet import PushBullet
import random
import string

import sqlite3, sys, socket
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton

# For speech recognition
import whisper
import queue
import speech_recognition as sr
import whisper
import queue
import numpy as np

# For encryption
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# For image generation
import torch
from diffusers import DiffusionPipeline

# Stable Diffusion
pipe = DiffusionPipeline.from_pretrained("./openjourney-v2", torch_dtype=torch.float16)
pipe.to("cuda")

# Whisper
audio_model = whisper.load_model("base.en")

tcpClientA=None


class ImageGenerator:
    def __init__(self):
        self.prompt = ""
        self.style = """, European fantasy buildings, professional (majestic) oil painting(((trending on ArtStation))), trending on CGSociety, dramatic lighting, (dawn), refraction, ((((Unreal Engine 5)))), rule of thirds"""
        self.negative_prompt = "amateur, poorly drawn, ugly, flat"
        self.image = None
    
    def generate(self, prompt, timestamp):
        self.prompt = prompt
        self.prompt = self.prompt + self.style
        self.image = pipe(self.prompt, num_inference_steps=60, negative_prompt=self.negative_prompt).images[0]
        pipe.enable_attention_slicing()
        self.image.save(".\outputs\{}.png".format(timestamp.replace(":", "-")))
        return self.image


class AudioRecorder(Thread):
    def __init__(self, audio_queue, energy=300, pause=0.8, dynamic_energy=False):
        super().__init__(name="Recorder")
        self.audio_queue = audio_queue
        self.r = sr.Recognizer()
        self.r.energy_threshold = energy
        self.r.pause_threshold = pause
        self.r.dynamic_energy_threshold = dynamic_energy
        self.event = threading.Event()

    def run(self):
        with sr.Microphone(sample_rate=16000) as source:
            if self.event.is_set():
                return
            self.r.adjust_for_ambient_noise(source, duration = 1)
            print("Say something!")
            i = 0
            while not self.event.is_set():
                audio = self.r.listen(source)
                torch_audio = torch.from_numpy(np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0)
                audio_data = torch_audio

                self.audio_queue.put_nowait(audio_data)
                i += 1

    def stop(self):
        self.event.set()


class AudioTranscriber(Thread):
    def __init__(self, audio_queue, result_queue, audio_model, english=True, verbose=False, save_file=False):
        super().__init__(name="Transcriber")
        self.audio_queue = audio_queue
        self.result_queue = result_queue
        self.audio_model = audio_model
        self.english = english
        self.verbose = verbose
        self.save_file = save_file
        self.event = threading.Event()
        
    def run(self):
        while not self.event.is_set():
            audio_data = self.audio_queue.get()
            try:
                result = audio_model.transcribe(audio_data, language='english')
                predicted_text = result["text"]
                self.result_queue.put_nowait(predicted_text)
            except Exception as e:
                self.result_queue.put_nowait("Error occured: " + str(e))

    def stop(self):
        self.event.set()


class Window(QDialog):
    def __init__(self):
        super().__init__()
        self.flag=0
        self.setWindowTitle("CLIENT")
        self.server_public_key = ""

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
        self.recording_icon = QtGui.QIcon('./src/recording.png')

        self.send_button = QtWidgets.QPushButton()
        self.file_button = QtWidgets.QPushButton()
        self.micro_button = QtWidgets.QPushButton()

        self.micro_button.setIcon(self.micro_icon)
        self.file_button.setIcon(self.file_icon)
        self.send_button.setIcon(self.send_icon)

        # buttons parameters
        self.micro_button.setStyleSheet("background-color: #0A7F6A; color: white; border-radius : 10px; border : 2px solid black;")
        self.micro_button.clicked.connect(self.transcribe)
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

        # progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.bottom.addWidget(self.progress_bar)

    def send(self):
        text=self.editbox.text().strip()

        if text.startswith("/imagine"):

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            prompt = text.split("/imagine ", 1)[1]
            image = ImageGenerator()
            self.progress_bar.setVisible(True)
            thread = Thread(name="ImgGen", target=image.generate, args=(prompt, timestamp))
            thread.start()

            while thread.is_alive():
                if self.progress_bar.value() < 100:
                    self.progress_bar.setValue(self.progress_bar.value() + 1)
                    QtWidgets.QApplication.processEvents()
                    QtCore.QThread.msleep(70)
                else:
                    self.progress_bar.setValue(99)
                
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
            file_name = ".\outputs\{}.png".format(timestamp.replace(":", "-"))
            self.send_image(file_name, timestamp)
            self.editbox.clear()
        
        else:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            text1 = "\n["+timestamp+"] - client\n" + text
            format = QtGui.QTextBlockFormat()
            cursor = window.chat.textCursor()
            format.setAlignment(Qt.AlignRight)
            cursor.insertBlock(format)
            cursor.insertText(text1)
            ciphertext = self.server_public_key.encrypt(text.encode('utf-8'), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
            tcpClientA.send(ciphertext)
            self.editbox.clear()

    def send_image(self, file_name, timestamp):
        with open(file_name, 'rb') as f:
            data = f.read()
            ciphertext = self.server_public_key.encrypt("image incoming".encode('utf-8'), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
            tcpClientA.send(ciphertext)
            file_size = len(data)
            # send the size of the file as a 4-byte integer
            tcpClientA.sendall(struct.pack("!I", file_size))
            tcpClientA.sendall(data)
            print("File sent successfully.")
            print("size sent :", file_size)
        if file_name:
            image = QtGui.QPixmap(file_name)
            # image = image.scaled(self.chat.size(), QtCore.Qt.KeepAspectRatio)
            image = image.scaled(125,125)
            self.chat.document().addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(file_name), image)
            format = QtGui.QTextBlockFormat()
            text = "\n[" + timestamp + "] - client\n"
            cursor = self.chat.textCursor()
            format.setAlignment(Qt.AlignRight)
            cursor.insertBlock(format)
            cursor.insertText(text)
            cursor.insertHtml("<img src='{}' width='125' height='125'/>".format(file_name))



    def browse_image(self):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(None,"QFileDialog.getOpenFileName()", "","Images (*.png *.xpm *.jpg *.bmp);;All Files (*)", options=options)
        
        if file_name:
            self.send_image(file_name, timestamp)

    def receive_image(self):
        global tcpClientA
    
        # receive the size of the file as a 4-byte integer
        file_size = struct.unpack("!I", tcpClientA.recv(4))[0]
        file_path = "./received/{}.png".format(datetime.datetime.now().strftime("%H-%M-%S").replace(":", "-"))
        print(file_path)
        with open(file_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                data = tcpClientA.recv(4096)
                bytes_received += len(data)
                f.write(data)
                # print("\nrecu : ", bytes_received)
                # print("fichier taille : ", file_size)
            
        return file_path
    
    def transcribe(self):
        audio_queue = queue.Queue()
        result_queue = queue.Queue()
        timestamp = datetime.datetime.now().strftime("%H:%M")
        recorder = AudioRecorder(audio_queue)
        transcriber = AudioTranscriber(audio_queue, result_queue, audio_model=audio_model)

        recorder.event.clear()
        transcriber.event.clear()

        recorder.start()
        transcriber.start()
        self.micro_button.setIcon(self.recording_icon)
        while True:
            result = result_queue.get()
            if result:
                text1 = "\n["+timestamp+"] - client\n" + result
                format = QtGui.QTextBlockFormat()
                cursor = window.chat.textCursor()
                format.setAlignment(Qt.AlignRight)
                cursor.insertBlock(format)
                cursor.insertText(text1)

                if result.startswith(" Imagine"):
                    prompt = result.split(" Imagine ", 1)[1]
                    image = ImageGenerator()
                    self.progress_bar.setVisible(True)
                    thread = Thread(name="ImgGen", target=image.generate, args=(prompt, timestamp))
                    thread.start()

                    while thread.is_alive():
                        if self.progress_bar.value() < 100:
                            self.progress_bar.setValue(self.progress_bar.value() + 1)
                            QtWidgets.QApplication.processEvents()
                            QtCore.QThread.msleep(70)
                        else:
                            self.progress_bar.setValue(99)
                        
                    self.progress_bar.setVisible(False)
                    self.progress_bar.setValue(0)
                    file_name = ".\outputs\{}.png".format(timestamp.replace(":", "-"))
                    self.send_image(file_name, timestamp)
                
                else:
                    ciphertext = self.server_public_key.encrypt(result.encode('utf-8'), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
                    tcpClientA.send(ciphertext)
                
                recorder.stop()
                transcriber.stop()
                break
            else:
                break
        


class ClientThread(Thread):
    def __init__(self,window): 
        Thread.__init__(self) 
        self.window=window
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
 
    def run(self): 
        host = socket.gethostname() 
        port = 80
        BUFFER_SIZE = 1024
        global tcpClientA
        tcpClientA = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        tcpClientA.connect((host, port))
        # Send the public key to the server
        tcpClientA.send(self.public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))

        # Receive the server's public key
        server_public_key = serialization.load_pem_public_key(tcpClientA.recv(BUFFER_SIZE), backend=default_backend())
        window.server_public_key = server_public_key

        while True :  
            data = tcpClientA.recv(4096) 
            plaintext = self.private_key.decrypt(data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    
            timestamp = datetime.datetime.now().strftime("%H:%M")
            if plaintext.decode('utf-8') == "image incoming":
                file_name = window.receive_image()
                with open(file_name, "rb") as f:
                    print("size received : ", len(f.read()))
                    print("File received successfully.")
                    format = QtGui.QTextBlockFormat()
                image = QtGui.QPixmap(file_name)
                # image = image.scaled(window.chat.size(), QtCore.Qt.KeepAspectRatio)
                image = image.scaled(125,125)
                window.chat.document().addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(file_name), image)
                cursor = window.chat.textCursor()
                format.setAlignment(Qt.AlignLeft)
                cursor.insertBlock(format)
                cursor.insertText("\n[" + timestamp + "] - server \n")
                cursor.insertHtml("<img src='{}' width='125' height='125'/>".format(file_name))
                # window.chat.append("\n[" + timestamp + "] - server")
                # window.chat.append("<img src='{}' width='125' height='125'/>".format(file_name))
            else:
                # window.chat.append("<p align='right'>okok<p>")
                # window.chat.append("\nsuite")
                # window.chat.append("\n<p align='left'>["+timestamp+"] - server\n" + data.decode("utf-8")+"</p>")
                text = "\n["+timestamp+"] - server\n" + plaintext.decode('utf-8')
                format = QtGui.QTextBlockFormat()
                cursor = window.chat.textCursor()
                format.setAlignment(Qt.AlignLeft)
                cursor.insertBlock(format)
                cursor.insertText(text)


class Login(QWidget):
    def __init__(self,app):
        super().__init__()
        
        self.API_KEY = "o.4jrhqL8PTtbprfW2n23zFNkz8PClbonX"
        self.pb = PushBullet(self.API_KEY)
        self.pwd = None
        self.tries = 3
        self.app = app

        self.setWindowTitle("Login")
        
        #labels
        self.username_label = QLabel("\n\nUsername:")
        self.username_label.setStyleSheet("color: white; font-size: 18px; font-style: italic;")
        self.pwd_label = QLabel("Password:")
        self.pwd_label.setStyleSheet("color: white; font-size: 18px; font-style: italic;")
    
        #entry box
        self.username_entry = QLineEdit()
        self.username_entry.setStyleSheet("background-color: #E7E1D8; border-radius: 7px; font-size: 22px;")
        self.username_entry.setFixedSize(330, 40)
        self.pwd_entry = QLineEdit()
        self.pwd_entry.setEchoMode(QLineEdit.Password)
        self.pwd_entry.setStyleSheet("background-color: #E7E1D8; border-radius: 7px; font-size: 22px;")
        self.pwd_entry.setFixedSize(330, 40)

        #buttons
        self.login_button = QPushButton("Verify")
        self.login_button.setStyleSheet("background-color: #06A684; border-radius: 3px;\
         color:white; font-size: 20px; border-style: solid; border-width: 2px; border-color: white;")
        self.login_button.setFixedSize(330,40)
        self.login_button.clicked.connect(self.check_credentials)

        #create logo layout
        self.logo_layout = QHBoxLayout()
        
        #create logo label
        self.logo_label = QLabel()
        self.logo_label.setPixmap(QtGui.QPixmap("./src/logo.png").scaled(320,265))
        #add logo label to logo layout
        self.logo_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)
        
        #layout managing
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10,10,10,10)
        self.layout.addLayout(self.logo_layout)
        self.layout.addWidget(self.username_label, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.username_entry, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.pwd_label, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.pwd_entry, alignment=Qt.AlignCenter)
        self.layout.setSpacing(10)
        self.layout.addWidget(self.login_button, alignment=Qt.AlignCenter)
        
        self.setLayout(self.layout)
        
        
        #initialization
        self.create_table()
        
    def create_table(self):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, ip TEXT)''')
        conn.commit()

    def generate_key(self):
        characters = string.ascii_letters + string.digits + string.punctuation
        self.pwd = ''.join(random.choice(characters) for i in range(8))
        print("Random password is:", 8*'*')
        self.pb.push_note("Your temporary key", self.pwd)
        
    def check_credentials(self):
        username = self.username_entry.text()
        password = self.pwd_entry.text()
    
        if self.pwd == None:
        
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            result = cursor.fetchone()
            if result: #user exists
                cursor.execute("SELECT * FROM users WHERE username=? and password=?", (username,password))
                result = cursor.fetchall()
                if len(result) > 0: #creds are good
                    
                    #create key_button and key_entry here
                    self.key_button = QPushButton("Generate Key", self)
                    # self.key_button.move(50, 150)
                    self.key_button.setStyleSheet("background-color: #223E3E; border-radius: 3px;\
                     color:white; font-size: 20px; border-style: solid; border-width: 2px; border-color: white;")
                    self.key_button.setFixedSize(330,40)


                    self.key_entry = QLineEdit(self)
                    self.key_entry.setStyleSheet("background-color: #E7E1D8; border-radius: 7px; font-size: 22px;")
                    self.key_entry.setFixedSize(330, 40)
                    # self.key_entry.move(150, 150)

                    self.layout.addWidget(self.key_button, alignment=Qt.AlignCenter)
                    self.layout.addWidget(self.key_entry, alignment=Qt.AlignCenter)
                    self.key_button.clicked.connect(self.generate_key)

                    current_ip = socket.gethostbyname(socket.gethostname())
                    cursor.execute("SELECT ip FROM users WHERE username=?", (username,))
                    result = cursor.fetchone()
                    if result and result[0] != current_ip:
                        cursor.execute("UPDATE users SET ip = ? WHERE username=? and password=?", (current_ip,username,password))
                        conn.commit()

                else: #creds are not good
                    self.tries -= 1
                    if self.tries == 0: #account deleted
                        try:
                            cursor.execute("DELETE FROM users WHERE username=?", (username,))
                            conn.commit()
                        except:
                            pass
                        QMessageBox.critical(self, "Error", "Account deleted after 3 tries")
                        self.app.close()
                    else: #another try
                        QMessageBox.warning(self, "Error", f"Incorrect credentials, try left : {self.tries}")
                        self.pwd_entry.clear()

            else: #user doesn't exist
                QMessageBox.information(self,"Warning", "This account doesn't exist, please create one.")
                self.pwd_entry.clear()
                self.signup = Signup()
                self.signup.setStyleSheet("background-color: #0A7F6A; border-radius: 7px;")
                self.signup.show()

        else: #key gen has been called
            print(self.pwd)
            print(self.key_entry)
            if str(self.pwd) == str(self.key_entry.text()): #key is good
                print("Welcome in the chat room, ",username)
                self.app.quit()
                
            else:
                QMessageBox.warning(self, "Warning", "Incorrect access key.\n\nPlease generate a new one and try again.")
                self.key_entry.clear()
       

class Signup(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sign Up")

        self.accountname_label = QLabel("\n\n\nUsername:")
        self.password_label = QLabel("Password:")
        self.accountname_entry = QLineEdit()
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)

        self.accountname_label.setStyleSheet("color: white; font-size: 18px; font-style: italic;")
        self.password_label.setStyleSheet("color: white; font-size: 18px; font-style: italic;")

        self.accountname_entry.setStyleSheet("background-color: #E7E1D8; border-radius: 7px; font-size: 22px;")
        self.accountname_entry.setFixedSize(330, 40)
        self.password_entry.setStyleSheet("background-color: #E7E1D8; border-radius: 7px; font-size: 22px;")
        self.password_entry.setFixedSize(330, 40)

        self.signup_button = QPushButton("Sign Up")
        self.signup_button.clicked.connect(self.register_user)

        self.signup_button.setStyleSheet("background-color: #06A684; border-radius: 3px;\
         color:white; font-size: 20px; border-style: solid; border-width: 2px; border-color: white;")
        self.signup_button.setFixedSize(330,40)

        #create logo layout
        self.logo_layout2 = QHBoxLayout()
        #create logo label
        self.logo_label2 = QLabel()
        self.logo_label2.setPixmap(QtGui.QPixmap("logo.png").scaled(320,265))
        #add logo label to logo layout
        self.logo_layout2.addWidget(self.logo_label2, alignment=Qt.AlignCenter)

        self.layout2 = QVBoxLayout()
        self.layout2.setContentsMargins(10,10,10,10)
        self.layout2.addLayout(self.logo_layout2)
        self.layout2.addWidget(self.accountname_label, alignment=Qt.AlignCenter)
        self.layout2.addWidget(self.accountname_entry, alignment=Qt.AlignCenter)
        self.layout2.addWidget(self.password_label, alignment=Qt.AlignCenter)
        self.layout2.addWidget(self.password_entry, alignment=Qt.AlignCenter)
        self.layout2.addWidget(self.signup_button, alignment=Qt.AlignCenter)
        self.setLayout(self.layout2)

    def register_user(self):
        username = self.accountname_entry.text()
        password = self.password_entry.text()

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
        conn.commit()

        QMessageBox.information(self, "Success", "Your password will only be used for restoring account purpose.\
 To log in, please download Pushbullet app.\n\nThanks for registering!")
        self.close()


if __name__ == '__main__':
    temoin = 2
    while temoin != 0:
        print(temoin)
        if temoin == 1:
            app = QApplication(sys.argv)
            login = Login(app)
            login.show()
            login.setStyleSheet("background-color: #0A7F6A; border-radius: 7px;")
            # login.resize(360,640)
            app.exec_()
            temoin = 2
        elif temoin == 2:
            app = QApplication(sys.argv)
            window = Window()
            window.resize(360,640)
            window.setStyleSheet("background-color: #0A7F6A;")
            clientThread=ClientThread(window)
            clientThread.start()
            window.exec()
            app.exec_()
            app.quit()
            break


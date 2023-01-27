import sqlite3, sys, socket
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton
from pushbullet import PushBullet
import random
import string

class Login(QWidget):
    def __init__(self):
        super().__init__()
        
        self.API_KEY = "o.4jrhqL8PTtbprfW2n23zFNkz8PClbonX"
        self.pb = PushBullet(self.API_KEY)
        self.pwd = None
        self.tries = 3

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
                        self.close()
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


if __name__ == "__main__":

    # # get current ipv4
    # hostname = socket.gethostname()
    # ip_address = socket.gethostbyname(hostname)

    app = QApplication(sys.argv)
    login = Login()
    login.show()
    login.setStyleSheet("background-color: #0A7F6A; border-radius: 7px;")
    # login.resize(360,640)
    sys.exit(app.exec_())
import socket
import sys

class Client:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5000
        self.size = 1024
        self.socket = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def run(self):
        if not self.connect():
            return

        print("Connected to server. Type 'quit' to exit.")
        while True:
            try:
                message = input("Enter message: ")
                if message.lower() == 'quit':
                    break
                
                self.socket.send(message.encode('utf-8'))
                response = self.socket.recv(self.size).decode('utf-8')
                print(f"Server response: {response}")

            except Exception as e:
                print(f"Error: {e}")
                break

        self.socket.close()

if __name__ == "__main__":
    client = Client()
    client.run()

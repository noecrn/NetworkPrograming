import socket
import threading
import sys
import time
import os

class SocketClient:
    def __init__(self, host='localhost', port=5008):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.receive_thread = None

    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def receive_messages(self):
        """Thread function to continuously receive messages"""
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    print("Connection to server lost")
                    self.running = False
                    break
                
                # Handle received data
                print(f"\nReceived: {data.decode('utf-8', errors='ignore')}")
                print("Enter message (or 'exit' to quit): ", end="", flush=True)
                
            except Exception as e:
                print(f"\nError receiving data: {e}")
                self.running = False
                break

    def send_message(self, message):
        """Send a message to the server"""
        try:
            self.socket.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def run(self):
        """Run the client"""
        if not self.connect():
            return
        
        self.running = True
        
        # Start the receive thread
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # Main loop for sending messages
        try:
            print("Connected to server. Type messages to send (or 'exit' to quit)")
            
            while self.running:
                message = input("Enter message (or 'exit' to quit): ")
                
                if message.lower() == 'exit':
                    self.running = False
                    break
                
                # Send the message
                if not self.send_message(message):
                    break
                
        except KeyboardInterrupt:
            print("\nClient interrupted.")
        finally:
            self.running = False
            if self.socket:
                self.socket.close()
            print("Client disconnected")

if __name__ == "__main__":
    client = SocketClient()
    client.run()
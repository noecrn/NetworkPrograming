import socket
import os
import threading
import time
import sys

class FileClient:
    def __init__(self, host='127.0.0.1', port=5555, max_retries=5):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (host, port)
        self.connect_with_retry(max_retries)
        self.client_id = input("Enter client ID: ")
        self.received_dir = "received"
        os.makedirs(self.received_dir, exist_ok=True)
        self.transfer_timeout = 15.0  # Match server timeout
        self.running = True

    def connect_with_retry(self, max_retries):
        retries = 0
        while retries < max_retries:
            try:
                print(f"Attempting to connect to server... (attempt {retries + 1}/{max_retries})")
                self.client_socket.connect(self.server_address)
                print("Connected to server successfully!")
                return
            except ConnectionRefusedError:
                retries += 1
                if retries == max_retries:
                    print("Could not connect to server. Make sure the server is running.")
                    sys.exit(1)
                print("Connection failed. Retrying in 2 seconds...")
                time.sleep(2)
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def register(self):
        self.client_socket.send(f"REGISTER:{self.client_id}".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)

    def send_file(self, filename):
        try:
            if not os.path.exists(filename):
                print(f"File {filename} not found")
                return

            filesize = os.path.getsize(filename)
            if filesize > 2_000_000:  # 2MB limit
                print("File too large (max 2MB)")
                return

            print(f"Sending file {filename} ({filesize} bytes)...")
            self.client_socket.send(f"SEND:{os.path.basename(filename)}:{filesize}:{self.client_id}".encode())
            time.sleep(0.1)

            with open(filename, 'rb') as f:
                data = f.read()
                total_sent = 0
                while total_sent < filesize:
                    chunk_size = min(4096, filesize - total_sent)
                    sent = self.client_socket.send(data[total_sent:total_sent + chunk_size])
                    if sent == 0:
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
                    print(f"Progress: {total_sent}/{filesize} bytes ({(total_sent/filesize)*100:.1f}%)", end='\r')

            print(f"\nFile {filename} sent successfully")

            # Set timeout for server responses
            self.client_socket.settimeout(self.transfer_timeout)
            try:
                response = self.client_socket.recv(1024).decode()
                if response.startswith("RECEIVED:"):
                    print("Server received the file successfully")
                
                response = self.client_socket.recv(1024).decode()
                if response.startswith("STATUS:"):
                    print(response[7:])
                elif response.startswith("ERROR:"):
                    print(f"Error: {response[6:]}")
            finally:
                self.client_socket.settimeout(None)

        except Exception as e:
            print(f"\nError sending file: {str(e)}")

    def receive_files(self):
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode()
                if not message:
                    print("\nDisconnected from server")
                    break

                if message.startswith("FILE:"):
                    _, filename, filesize, sender_id = message.split(":")
                    filesize = int(filesize)
                    print(f"\nReceiving file {filename} ({filesize} bytes) from {sender_id}...")
                    
                    file_data = bytearray()
                    total_received = 0
                    while total_received < filesize:
                        chunk = self.client_socket.recv(min(4096, filesize - total_received))
                        if not chunk:
                            raise RuntimeError("Connection broken during file transfer")
                        file_data.extend(chunk)
                        total_received += len(chunk)
                        print(f"Progress: {total_received}/{filesize} bytes ({(total_received/filesize)*100:.1f}%)", end='\r')

                    save_path = os.path.join(self.received_dir, filename)
                    with open(save_path, 'wb') as f:
                        f.write(file_data)

                    self.client_socket.send(f"ACK:{filename}:{self.client_id}".encode())
                    print(f"\nFile saved as {save_path}")

            except Exception as e:
                if not self.running:
                    break
                print(f"\nError receiving file: {str(e)}")

    def run(self):
        self.register()
        
        receive_thread = threading.Thread(target=self.receive_files)
        receive_thread.daemon = True
        receive_thread.start()

        try:
            while self.running:
                command = input("Enter command (SEND <filename> or EXIT): ")
                if command.lower() == 'exit':
                    break
                elif command.startswith('SEND '):
                    filename = command[5:]
                    self.send_file(filename)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.client_socket.close()

if __name__ == "__main__":
    client = FileClient()
    client.run()
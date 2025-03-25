import socket
import os
import threading

class FileClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.client_id = input("Enter client ID: ")
        self.received_dir = "received"
        os.makedirs(self.received_dir, exist_ok=True)
        self.running = True
        self.transfer_timeout = 15.0  # Match server timeout
        self.should_disconnect = False  # New flag to control disconnection
        self.max_retries = 3

    def register(self):
        self.client_socket.send(f"REGISTER:{self.client_id}".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)

    def send_file(self, filename):
        if not os.path.exists(filename):
            print(f"File {filename} not found")
            return

        filesize = os.path.getsize(filename)
        if filesize > 2_000_000:  # 2MB limit
            print("File too large (max 2MB)")
            return

        # Send file info
        self.client_socket.send(f"SEND:{filename}:{filesize}:{self.client_id}".encode())

        # Send file data
        with open(filename, 'rb') as f:
            self.client_socket.sendall(f.read())

        print(f"File {filename} sent successfully")

    def receive_files(self):
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode()
                if not message:
                    print("\nDisconnected from server")
                    self.running = False
                    break

                if message.startswith("FILE:"):
                    retry_count = self.max_retries
                    while retry_count > 0 and self.running:
                        try:
                            _, filename, filesize, sender_id = message.split(":")
                            filesize = int(filesize)
                            print(f"\nReceiving file {filename} ({filesize} bytes) from {sender_id}...")
                            
                            # Set timeout for the transfer
                            self.client_socket.settimeout(self.transfer_timeout)
                            
                            try:
                                file_data = bytearray()
                                total_received = 0
                                last_progress = 0
                                
                                while total_received < filesize and not self.should_disconnect:
                                    try:
                                        chunk = self.client_socket.recv(min(4096, filesize - total_received))
                                        if not chunk:
                                            if not self.should_disconnect:
                                                raise RuntimeError("Connection broken during file transfer")
                                            break
                                        file_data.extend(chunk)
                                        total_received += len(chunk)
                                        progress = (total_received / filesize) * 100
                                        if progress - last_progress >= 10:
                                            print(f"Progress: {total_received}/{filesize} bytes ({progress:.1f}%)", end='\r')
                                            last_progress = progress
                                    except socket.timeout:
                                        print("\nTimeout during file transfer, retrying...")
                                        continue

                                if total_received == filesize:
                                    print(f"\nReceived {filename} successfully, saving...")
                                    save_path = os.path.join(self.received_dir, filename)
                                    with open(save_path, 'wb') as f:
                                        f.write(file_data)
                                    
                                    # Send ACK with retry
                                    ack = f"ACK:{filename}:{self.client_id}"
                                    retry_count = 3
                                    while retry_count > 0:
                                        try:
                                            print(f"Sending ACK: {ack}")
                                            self.client_socket.send(ack.encode())
                                            print(f"File saved as {save_path}")
                                            break
                                        except socket.timeout:
                                            retry_count -= 1
                                            if retry_count > 0:
                                                print("ACK timeout, retrying...")
                                                continue
                                            raise
                                
                            finally:
                                self.client_socket.settimeout(None)
                                
                        except socket.timeout:
                            retry_count -= 1
                            if retry_count > 0:
                                print(f"\nRetrying transfer... ({retry_count} attempts left)")
                                continue
                            raise
                        except Exception as e:
                            print(f"\nError during file reception: {str(e)}")
                            if self.should_disconnect:
                                self.running = False
                                break

            except Exception as e:
                if self.running and not self.should_disconnect:
                    print(f"\nConnection error: {str(e)}")
                    if isinstance(e, socket.timeout):
                        continue
                    self.running = False
                break

    def run(self):
        self.register()
        
        # Start receive thread
        receive_thread = threading.Thread(target=self.receive_files)
        receive_thread.daemon = True
        receive_thread.start()

        # Main command loop
        try:
            while True:
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
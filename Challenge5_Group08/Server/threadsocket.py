import select
import socket
import sys
import threading
import os

class Server:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5008
        self.backlog = 5
        self.size = 1024
        self.server = None
        self.threads = []
        self.clients = {}  # Dictionary to track connected clients
        self.clients_lock = threading.Lock()  # Lock for thread-safe operations
        self.running = True  # Flag to control server operation

    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            print(f"Server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Error opening socket: {e}")
            sys.exit(1)
    
    def handle_user_input(self):
        """Thread function to handle user input for server shutdown"""
        print("Server running. Press Enter to stop.")
        while self.running:
            if input() == "":  # Wait for Enter key
                print("Server shutdown initiated...")
                self.running = False
                # Create a dummy connection to unblock the accept() call
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((self.host, self.port))
                    sock.close()
                except:
                    pass
                break

    def run(self):
        self.open_socket()
        
        # Start a separate thread for handling user input
        input_thread = threading.Thread(target=self.handle_user_input)
        input_thread.daemon = True
        input_thread.start()
        
        try:
            # Main server loop
            while self.running:
                try:
                    # Set a timeout so we can check the running flag periodically
                    self.server.settimeout(1.0)
                    try:
                        client_socket, client_address = self.server.accept()
                        print(f"New connection from {client_address}")
                        
                        # Create and start a new client thread
                        c = Client(client_socket, client_address, self)
                        c.start()
                        self.threads.append(c)
                    except socket.timeout:
                        # This is just a timeout to check the running flag
                        continue
                except OSError as e:
                    if not self.running:  # Ignore errors during shutdown
                        break
                    print(f"Socket error: {e}")
                    break
                        
        except KeyboardInterrupt:
            print("Server interrupted. Shutting down...")
        finally:
            self.running = False
            # Close server and all client threads
            self.server.close()
            
            # Notify all threads to stop
            with self.clients_lock:
                for client_thread in self.threads:
                    if client_thread.is_alive():
                        client_thread.running = False
            
            # Wait for all threads to complete
            for client_thread in self.threads:
                if client_thread.is_alive():
                    client_thread.join(1)  # Wait with timeout
                    
            print("Server shutdown complete")

    def broadcast(self, message, sender=None):
        """Broadcast a message to all connected clients except the sender"""
        with self.clients_lock:
            for client in self.threads:
                if client != sender and client.running:
                    try:
                        client.client.send(message)
                    except:
                        pass  # Handle failed send silently

    def remove_client(self, client):
        """Remove a client from the active threads list"""
        with self.clients_lock:
            if client in self.threads:
                self.threads.remove(client)

class Client(threading.Thread):
    def __init__(self, client, address, server):
        threading.Thread.__init__(self)
        self.client = client
        self.address = address
        self.size = 1024
        self.running = True
        self.server = server
        self.client_id = f"{address[0]}:{address[1]}"

    def run(self):
        try:
            while self.running:
                data = self.client.recv(self.size)
                if not data:
                    # Client disconnected
                    break
                
                # Process received data
                print(f'Received from {self.address}: {data.decode("utf-8", errors="ignore")}')
                
                # Echo the data back (you can modify this to handle different commands)
                self.client.send(data)
                
        except Exception as e:
            print(f"Error handling client {self.address}: {e}")
        finally:
            # Clean up when client disconnects
            print(f"Client {self.address} disconnected")
            self.client.close()
            self.running = False
            self.server.remove_client(self)

if __name__ == "__main__":
    s = Server()
    s.run()
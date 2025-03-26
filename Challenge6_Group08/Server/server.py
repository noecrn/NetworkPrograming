import socket
import threading
import select
import time
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server_log.txt"),
        logging.StreamHandler()
    ]
)

# Global variables
clients = {}  # {client_id: (socket, address)}
clients_lock = threading.Lock()
pending_acks = {}  # {filename+timestamp: {client_id: received_status}}
pending_acks_lock = threading.Lock()

def receive_file(client_socket, filesize):
    """Receive a file from a client"""
    data = b''
    bytes_received = 0
    
    while bytes_received < filesize:
        chunk = client_socket.recv(min(4096, filesize - bytes_received))
        if not chunk:
            raise Exception("Connection closed during file transfer")
        data += chunk
        bytes_received += len(chunk)
    
    return data

def check_acks(file_id, filename):
    """Check if all clients have acknowledged receipt of the file"""
    with pending_acks_lock:
        if file_id in pending_acks:
            for cid, status in pending_acks[file_id].items():
                if status is False:
                    logging.info(f"Timeout: No ACK from {cid} for {filename} ❌")
                    print(f"Timeout: No ACK from {cid} for {filename} ❌")
            
            # Clean up pending ACKs after timeout
            del pending_acks[file_id]

def forward_file(filename, file_data, sender_id, file_id):
    """Forward a file to all other registered clients"""
    with clients_lock:
        targets = [cid for cid in clients.keys() if cid != sender_id]
        
        if not targets:
            logging.info(f"No other clients to forward {filename} to")
            print(f"No other clients to forward {filename} to")
            return
        
        # Initialize pending ACKs for this file
        with pending_acks_lock:
            pending_acks[file_id] = {cid: False for cid in targets}
        
        # Log forwarding attempt
        targets_str = ", ".join(targets)
        logging.info(f"Forwarding {filename} to {targets_str}")
        print(f"Forwarding {filename} to {targets_str}")
        
        # Send file to all other clients
        for cid in targets:
            if cid not in clients:
                continue
                
            target_socket = clients[cid][0]
            try:
                # Send file metadata with the unique file_id
                header = f"SEND:{filename}:{len(file_data)}:{sender_id}:{file_id}"
                target_socket.send(header.encode('utf-8'))
                time.sleep(0.1)  # Small delay to ensure header is processed
                
                # Send file data
                target_socket.sendall(file_data)
            except Exception as e:
                logging.error(f"Error forwarding file to {cid}: {e}")
                print(f"Error forwarding file to {cid}: {e}")
                with pending_acks_lock:
                    pending_acks[file_id][cid] = "Failed"
        
        # Start a timer to check for ACKs
        ack_timer = threading.Timer(5.0, check_acks, args=[file_id, filename])
        ack_timer.daemon = True
        ack_timer.start()

def handle_client(client_socket, client_address):
    """Handle a client connection"""
    client_id = None
    
    try:
        while True:
            # Receive message from client
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            
            # Process the received message
            if data.startswith('REGISTER:'):
                # Handle registration
                client_id = data.split(':')[1]
                with clients_lock:
                    # Check if client_id is already taken
                    if client_id in clients:
                        client_socket.send(f"Registration failed: ID {client_id} already in use".encode('utf-8'))
                        logging.warning(f"Registration attempt with duplicate ID {client_id} from {client_address}")
                        continue
                        
                    clients[client_id] = (client_socket, client_address)
                
                logging.info(f"Client {client_id} registered from {client_address}")
                client_socket.send(f"Registration successful as {client_id}".encode('utf-8'))
            
            elif data.startswith('SEND:'):
                # Handle file sending request
                parts = data.split(':')
                if len(parts) < 4 or not client_id:
                    continue
                
                _, filename, filesize, sender_id = parts
                filesize = int(filesize)
                
                # Generate unique file identifier with timestamp
                timestamp = int(time.time())
                file_id = f"{filename}_{timestamp}"
                
                # Receive the file content
                file_data = receive_file(client_socket, filesize)
                
                logging.info(f"Client {sender_id} sent {filename} ({filesize} bytes)")
                print(f"Client {sender_id} sent {filename} ({filesize} bytes)")
                
                # Forward to other clients
                forward_file(filename, file_data, sender_id, file_id)
            
            elif data.startswith('ACK:'):
                # Handle acknowledgment
                parts = data.split(':')
                if len(parts) < 3:
                    continue
                
                _, file_id, ack_client_id = parts
                with pending_acks_lock:
                    if file_id in pending_acks and ack_client_id in pending_acks[file_id]:
                        pending_acks[file_id][ack_client_id] = True
                        logging.info(f"Received ACK from {ack_client_id} for {file_id} ✅")
                        print(f"Received ACK from {ack_client_id} for {file_id} ✅")
    
    except Exception as e:
        logging.error(f"Error handling client {client_id}: {e}")
    
    finally:
        # Clean up when client disconnects
        if client_id:
            with clients_lock:
                if client_id in clients:
                    del clients[client_id]
            logging.info(f"Client {client_id} disconnected")
            print(f"Client {client_id} disconnected")
        client_socket.close()

def main():
    """Main function to start the server"""
    host = '127.0.0.1'
    port = 5555
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    
    logging.info(f"Server started on {host}:{port}")
    print(f"Server running on {host}:{port}")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, 
                                           args=(client_socket, client_address))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        logging.info("Server shutting down")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
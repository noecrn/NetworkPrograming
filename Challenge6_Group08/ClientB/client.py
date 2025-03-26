import socket
import threading
import os
import sys
import time

# Global variables
client_id = None
running = False
server_host = '127.0.0.1'
server_port = 5555
client_socket = None

def receive_files():
    """Continuously listen for incoming files"""
    global running, client_socket, client_id
    
    # Utilisez un chemin absolu pour le dossier received
    client_dir = os.path.dirname(os.path.abspath(__file__))
    received_dir = os.path.join(client_dir, "received")
    
    # Assurez-vous que le dossier existe
    os.makedirs(received_dir, exist_ok=True)
    
    while running:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                print("Connection to server lost.")
                break
            
            if data.startswith('SEND:'):
                parts = data.split(':')
                if len(parts) < 5:
                    continue
                
                _, filename, filesize, sender_id, file_id = parts
                filesize = int(filesize)
                
                print(f"Receiving {filename} from {sender_id}...")
                
                # Receive file data
                file_data = b''
                bytes_received = 0
                
                while bytes_received < filesize:
                    chunk = client_socket.recv(min(4096, filesize - bytes_received))
                    if not chunk:
                        raise Exception("Connection closed during file transfer")
                    file_data += chunk
                    bytes_received += len(chunk)
                
                # Save file to received folder
                # Add a suffix if file already exists
                final_filename = filename
                counter = 0
                while os.path.exists(os.path.join(received_dir, final_filename)):
                    counter += 1
                    base_name, ext = os.path.splitext(filename)
                    final_filename = f"{base_name}_{counter}{ext}"
                
                filepath = os.path.join(received_dir, final_filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                
                print(f"Received {filename} from {sender_id}")
                print(f"Saved to {filepath}")
                
                # Send ACK to server with the file_id
                client_socket.send(f"ACK:{file_id}:{client_id}".encode('utf-8'))
                print(f"Sent acknowledgment for {filename}")
        
        except Exception as e:
            print(f"Error receiving file: {e}")
            running = False
def send_file(filename):
    """Send a file to the server for broadcasting"""
    global client_socket, client_id
    
    if not client_id:
        print("Not registered with server. Please register first.")
        return False
    
    try:
        # Get the directory where the client script is located
        client_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct full path to the file in the client's directory
        filepath = os.path.join(client_dir, filename)
        
        # Show paths for debugging
        print(f"Current working directory: {os.getcwd()}")
        print(f"Client directory: {client_dir}")
        print(f"Looking for file at: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"File {filename} not found.")
            return False
        
        # Get file size
        filesize = os.path.getsize(filepath)
        if filesize > 2 * 1024 * 1024:  # 2MB limit
            print("File size exceeds 2MB limit.")
            return False
        
        # Send file metadata
        client_socket.send(f"SEND:{os.path.basename(filename)}:{filesize}:{client_id}".encode('utf-8'))
        
        # Send file content
        with open(filepath, 'rb') as f:
            client_socket.sendall(f.read())
        
        print(f"Sent {filename} to server.")
        return True
    
    except Exception as e:
        print(f"Error sending file: {e}")
        return False
    
def register(entered_client_id):
    """Register with the server using the provided client_id"""
    global client_socket, client_id
    
    try:
        client_socket.send(f"REGISTER:{entered_client_id}".encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        print(response)
        if "successful" in response.lower():
            client_id = entered_client_id
            return True
        return False
    except Exception as e:
        print(f"Registration failed: {e}")
        return False

def main():
    """Main function to start the client"""
    global running, client_socket, server_host, server_port
    
    # Create received directory if it doesn't exist
    os.makedirs("received", exist_ok=True)
    
    # Connect to server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((server_host, server_port))
        print(f"Connected to server at {server_host}:{server_port}")
        
        # Register with server
        entered_client_id = input("Enter client ID: ")
        if not register(entered_client_id):
            print("Failed to register with server. Exiting...")
            client_socket.close()
            return
        
        # Start file receiving thread
        running = True
        receive_thread = threading.Thread(target=receive_files)
        receive_thread.daemon = True
        receive_thread.start()
        
        # Command loop
        print("\nCommands:")
        print("SEND <filename> - Send a file to all other clients")
        print("EXIT - Close the client")
        
        while True:
            cmd = input("\nEnter command: ").strip()
            
            if cmd.lower() == 'exit':
                break
            
            if cmd.lower().startswith('send '):
                filename = cmd[5:].strip()
                send_file(filename)
            else:
                print("Unknown command. Use 'SEND <filename>' or 'EXIT'")
    
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        running = False
        if client_socket:
            client_socket.close()

if __name__ == "__main__":
    main()
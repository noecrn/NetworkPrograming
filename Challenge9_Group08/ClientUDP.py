import socket
import os

server_address = ('192.168.1.2', 5000)  # Change to actual server IP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Get file path from user
file_path = input("Enter file path to send: ")

# Validate file exists and size >= 10MB
if not os.path.exists(file_path):
    print("File does not exist")
    exit()
if os.path.getsize(file_path) < 10_000_000:
    print("File must be at least 10MB")
    exit()

# Send filename and size
file_name = os.path.basename(file_path)
file_size = os.path.getsize(file_path)
info = f"{file_name}|{file_size}"
client_socket.sendto(info.encode(), server_address)

# Wait for server ready signal
_, _ = client_socket.recvfrom(1024)

# Send file content in 1KB blocks
sent_bytes = 0
with open(file_path, 'rb') as file:
    while True:
        chunk = file.read(1024)
        if not chunk:
            break
        
        client_socket.sendto(chunk, server_address)
        sent_bytes += len(chunk)
        progress = (sent_bytes / file_size) * 100
        print(f"\rProgress: {progress:.2f}%", end='')

# Send end marker
client_socket.sendto(b"END_OF_FILE", server_address)

# Get completion status
status, _ = client_socket.recvfrom(1024)
print(f"\nTransfer complete. {status.decode()}")
client_socket.close()
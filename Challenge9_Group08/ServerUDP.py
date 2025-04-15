import socket

server_address = ('0.0.0.0', 5000)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(server_address)
print("Server listening on port 5000...")

# Receive file info
info, client_address = server_socket.recvfrom(1024)
file_name, file_size = info.decode().split('|')
file_size = int(file_size)

# Send ready signal
server_socket.sendto(b"READY", client_address)

# Receive file content
received_data = bytearray()
received_bytes = 0

while True:
    chunk, _ = server_socket.recvfrom(1024)
    
    if chunk == b"END_OF_FILE":
        break
        
    received_data.extend(chunk)
    received_bytes += len(chunk)
    progress = (received_bytes / file_size) * 100
    print(f"\rProgress: {progress:.2f}%", end='')

# Save received file
output_path = f"received_{file_name}"
with open(output_path, 'wb') as file:
    file.write(received_data)

# Calculate and send statistics
success_rate = (received_bytes / file_size) * 100
status = f"Received {received_bytes}/{file_size} bytes ({success_rate:.2f}%)"
print(f"\n{status}")
server_socket.sendto(status.encode(), client_address)

server_socket.close()
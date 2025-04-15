import socket
import struct
import time  # Add this import at the top

server_address = ('127.0.0.1', 5000)
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
received_data = {}
expected_block_id = 0
received_bytes = 0

while True:
    try:
        chunk, _ = server_socket.recvfrom(1032)
        
        if chunk == b"END_OF_FILE":
            # Verify all blocks received
            if len(received_data) * 1024 >= file_size:
                server_socket.sendto(b"COMPLETE", client_address)
                break
            else:
                # Request missing blocks
                missing_blocks = []
                total_blocks = (file_size + 1023) // 1024
                for i in range(total_blocks):
                    if i not in received_data:
                        missing_blocks.append(i)
                server_socket.sendto(f"MISSING|{','.join(map(str, missing_blocks))}".encode(), client_address)
                continue
        
        block_id = struct.unpack('!Q', chunk[:8])[0]
        data = chunk[8:]
        
        # Store data and send acknowledgment
        if block_id not in received_data:
            received_data[block_id] = data
            received_bytes += len(data)
            
        # Send ACK
        server_socket.sendto(f"ACK|{block_id}".encode(), client_address)
        
        progress = (received_bytes / file_size) * 100
        print(f"\rProgress: {progress:.2f}%", end='')
    
    except socket.timeout:
        continue

# Combine all blocks in order
ordered_data = bytearray()
for i in range(len(received_data)):
    ordered_data.extend(received_data[i])

# Save received file
output_path = f"received_{file_name}"
with open(output_path, 'wb') as file:
    file.write(ordered_data[:file_size])

# Calculate and send statistics
success_rate = (received_bytes / file_size) * 100
status = f"Received {received_bytes}/{file_size} bytes ({success_rate:.2f}%)"
print(f"\n{status}")

# Send status multiple times to ensure delivery
time.sleep(0.1)  # Small delay before sending status
for _ in range(3):  # Send status 3 times
    server_socket.sendto(status.encode(), client_address)
    time.sleep(0.1)

server_socket.close()
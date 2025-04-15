import socket
import os
import struct
import time

server_address = ('127.0.0.1', 5000)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1.0)

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
block_id = 0
unacked_blocks = {}
max_retries = 5

with open(file_path, 'rb') as file:
    while True:
        # Handle retransmissions first
        current_time = time.time()
        for block_id, (data, send_time, retries) in list(unacked_blocks.items()):
            if current_time - send_time > 1.0:  # 1 second timeout
                if retries >= max_retries:
                    print(f"\nFailed to send block {block_id} after {max_retries} attempts")
                    client_socket.close()
                    exit(1)
                # Retransmit
                packet = struct.pack('!Q', block_id) + data
                client_socket.sendto(packet, server_address)
                unacked_blocks[block_id] = (data, current_time, retries + 1)
        
        # Read and send new data
        chunk = file.read(1024)
        if not chunk and not unacked_blocks:  # All data sent and acknowledged
            break
        
        if chunk:
            packet = struct.pack('!Q', block_id) + chunk
            client_socket.sendto(packet, server_address)
            unacked_blocks[block_id] = (chunk, current_time, 0)
            block_id += 1
        
        # Check for ACKs
        try:
            while True:
                ack, _ = client_socket.recvfrom(1024)
                ack_msg = ack.decode()
                if ack_msg.startswith("ACK|"):
                    acked_block = int(ack_msg.split("|")[1])
                    if acked_block in unacked_blocks:
                        sent_bytes += len(unacked_blocks[acked_block][0])
                        del unacked_blocks[acked_block]
                        progress = (sent_bytes / file_size) * 100
                        print(f"\rProgress: {progress:.2f}%", end='')
        except socket.timeout:
            continue

# Send end marker and wait for completion confirmation
while True:
    client_socket.sendto(b"END_OF_FILE", server_address)
    try:
        response, _ = client_socket.recvfrom(1024)
        if response == b"COMPLETE":
            break
        elif response.decode().startswith("MISSING|"):
            missing_blocks = list(map(int, response.decode().split("|")[1].split(",")))
            with open(file_path, 'rb') as file:
                for block_id in missing_blocks:
                    file.seek(block_id * 1024)
                    chunk = file.read(1024)
                    packet = struct.pack('!Q', block_id) + chunk
                    client_socket.sendto(packet, server_address)
    except socket.timeout:
        continue

# Get completion status
max_status_retries = 5
status_received = False
for _ in range(max_status_retries):
    try:
        status, _ = client_socket.recvfrom(1024)
        print(f"\nTransfer complete. {status.decode()}")
        status_received = True
        break
    except socket.timeout:
        continue

if not status_received:
    print("\nWarning: Final status not received, but file transfer might be complete")

client_socket.close()
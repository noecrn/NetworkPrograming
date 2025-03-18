import socket
import sys
import re

server_address = ('127.0.0.1', 5000)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(server_address)

print("Enter mathematical operations (e.g., 3*5, 7/2, 6-4)")
sys.stdout.write('>> ')

try:
    while True:
        message = str(input())
        # Validate input format using regex
        if not re.match(r'^\d+[\+\-\*\/]\d+$', message):
            print("Invalid format! Use format: number operator number (e.g., 3*5)")
            sys.stdout.write('>> ')
            continue
            
        client_socket.send(message.encode())
        response = client_socket.recv(1024).decode()
        print(response)
        sys.stdout.write('>> ')

except KeyboardInterrupt:
    client_socket.close()
    sys.exit(0)
import socket
import sys
import re

server_address = ('127.0.0.1', 5000)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(server_address)

print("Wich file do you want to check palindrome ?")
sys.stdout.write('>> ')


try:
    while True:
        message = str(input())
        with open(message, 'r') as file:
            data = file.read()            
        client_socket.send(data.encode())
        response = client_socket.recv(1024).decode()
        print(response)
        sys.stdout.write('>> ')

except KeyboardInterrupt:
    client_socket.close()
    sys.exit(0)
import socket
import select
import sys
import threading
import re

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
ip_address = '127.0.0.1'
port = 8081
server.bind((ip_address, port))
server.listen(100)
list_of_clients = []
client_letters = {}  # Dictionary to map connections to letters
next_letter = ord('A')  # Start with 'A'

def is_prime(n):
    try:
        num = int(n)
        if num < 2:
            return False
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                return False
        return True
    except ValueError:
        return False

def clientthread(conn, addr):
    client_letter = client_letters[conn]
    while True:
        try:
            message = conn.recv(2048).decode()
            if message:
                # Check for prime number command
                prime_match = re.match(r'prime\s+(\d+)', message.strip())
                if prime_match:
                    number = prime_match.group(1)
                    result = is_prime(number)
                    response = f"{number} is{' ' if result else ' not '}a prime number"
                    print(f"On Server: {response}")
                    message_to_send = f"Client {client_letter}: {response}\n"
                    broadcast(message_to_send, conn)
                else:
                    print(f"Client {client_letter}: {message}")
                    message_to_send = f"Client {client_letter}: {message}\n"
                    broadcast(message_to_send, conn)
            else:
                remove(conn)
                break
        except:
            remove(conn)
            break

def broadcast(message, connection):
    for clients in list_of_clients:
        if clients != connection:
            try:
                clients.send(message.encode())
            except:
                clients.close()
                remove(clients)

def remove(connection):
    if connection in list_of_clients:
        list_of_clients.remove(connection)
        if connection in client_letters:
            del client_letters[connection]

def assign_next_letter():
    global next_letter
    letter = chr(next_letter)
    next_letter = ord('A') if next_letter >= ord('Z') else next_letter + 1
    return letter

while True:
    conn, addr = server.accept()
    list_of_clients.append(conn)
    client_letters[conn] = assign_next_letter()
    print(f"Client {client_letters[conn]} connected")
    threading.Thread(target=clientthread, args=(conn, addr)).start()

conn.close()
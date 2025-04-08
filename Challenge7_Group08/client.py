import socket
import select
import sys
from threading import Thread

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ip_address = '127.0.0.1'
port = 8081
server.connect((ip_address, port))

def send_msg(sock):
    while True:
        sys.stdout.write(">> ")
        sys.stdout.flush()
        data = sys.stdin.readline().strip()
        if data:
            sock.send(data.encode())
            if not data.startswith('prime'):
                print(f"You: {data}")

def recv_msg(sock):
    while True:
        try:
            data = sock.recv(2048).decode()
            if data:
                sys.stdout.write(data)
                sys.stdout.write(">> ")
                sys.stdout.flush()
        except:
            print("Lost connection to server")
            sock.close()
            sys.exit()

Thread(target=send_msg, args=(server,)).start()
Thread(target=recv_msg, args=(server,)).start()

while True:
    sockets_list = [server]
    read_socket, write_socket, error_socket = select.select(sockets_list, [], [])
    for socks in read_socket:
        if socks == server:
            recv_msg(socks)
        else:
            send_msg(socks)

server.close()
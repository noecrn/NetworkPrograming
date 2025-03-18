import socket
import select
import sys
import re

def calculate(expression):
    try:
        if not re.match(r'^[\d\+\-\*\/\s]+$', expression):
            return "Error: Invalid characters in expression"
        result = eval(expression)
        return result
    except ZeroDivisionError:
        return "Error: Division by zero"
    except:
        return "Error: Invalid operation"

server_address = ('127.0.0.1', 5000)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(server_address)
server_socket.listen(5)
input_socket = [server_socket]

try:
    while True:
        read_ready, write_ready, exception = select.select(input_socket, [], [])
        for sock in read_ready:
            if sock == server_socket:
                client_socket, client_address = server_socket.accept()
                input_socket.append(client_socket)
            else:
                data = sock.recv(1024).decode()
                if str(data):
                    result = calculate(data)
                    response = f"{data} = {result}"
                    print(f"{sock.getpeername()} {response}")
                    sock.send(response.encode())
                else:
                    sock.close()
                    input_socket.remove(sock)
except KeyboardInterrupt:
    server_socket.close()
    sys.exit(0)
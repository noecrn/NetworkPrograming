import socket
import select
import sys

def check_palindrome(data):
    data = data.lower()
    data = data.replace(" ", "")
    return data == data[::-1]

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
                if data:
                    lines = data.splitlines()
                    responses = []
                    for line in lines:
                        result = check_palindrome(line)
                        response = f"{line}: Is palindrome: {result}"
                        responses.append(response)
                        with open("result.txt", "a") as f:
                            f.write(f"{line} - {'yes' if result else 'no'}\n")
                    sock.send("\n".join(responses).encode())
                else:
                    sock.close()
                    input_socket.remove(sock)
                
except KeyboardInterrupt:
    server_socket.close()
    sys.exit(0)
import socket
import select
import sys
import os
import mimetypes

server_address = ('127.0.0.1', 8080)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(server_address)
server_socket.listen(5)

input_socket = [server_socket]

def generate_directory_listing(base_path='.'):
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'index.html')
        with open(template_path, 'r') as f:
            template = f.read()
    
        # Get absolute path and make it relative to server root
        abs_path = os.path.abspath(base_path)
        rel_path = os.path.relpath(abs_path, start=os.getcwd())
        
        items = []
        # Add parent directory link if not in root
        if rel_path != '.':
            items.append({
                'name': '..',
                'is_dir': True,
                'size': 0,
                'mtime': 0
            })
        
        for f in os.listdir(base_path):
            full_path = os.path.join(base_path, f)
            item = {
                'name': f,
                'is_dir': os.path.isdir(full_path),
                'size': os.path.getsize(full_path) if os.path.isfile(full_path) else 0,
                'mtime': os.path.getmtime(full_path)
            }
            items.append(item)
        
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        content = ''
        for item in items:
            name = item['name']
            if item['is_dir']:
                link = f'<a href="/{os.path.join(rel_path, name)}" class="directory">📁 {name}/</a>'
            else:
                link = f'<a href="/{os.path.join(rel_path, name)}">📄 {name}</a>'
            
            content += f'''
            <li class="file-item">
                <div class="file-name">{link}</div>
            </li>
            '''

        return template.replace('%CONTENT%', content).replace('%PATH%', abs_path)
    except Exception as e:
        print(f"Error generating directory listing: {e}")
        return f"<html><body><h1>Error: {str(e)}</h1></body></html>"

try:
    while True:
        read_ready, write_ready, exception = select.select(input_socket, [], [])
        
        for sock in read_ready:
            if sock == server_socket:
                client_socket, client_address = server_socket.accept()
                input_socket.append(client_socket)                       
            else:                
                data = sock.recv(4096)
                
                if not data:
                    input_socket.remove(sock)
                    sock.close()
                    continue
                
                data_str = data.decode('utf-8')
                request_header = data_str.split('\r\n')
                
                if len(request_header[0].split()) < 2:
                    continue
                    
                request_file = request_header[0].split()[1].lstrip('/')
                
                # Check for index files first
                if request_file == '' or request_file == '/':
                    request_path = '.'
                else:
                    request_path = request_file

                if os.path.isdir(request_path):
                    index_php = os.path.join(request_path, 'index.php')
                    if os.path.exists(index_php):
                        request_file = index_php
                    else:
                        response_data = generate_directory_listing(request_path)
                        content_length = len(response_data)
                        response_header = f'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Length: {content_length}\r\n\r\n'
                        response = (response_header + response_data).encode('utf-8')
                        sock.sendall(response)
                        continue

                # Handle file requests
                if os.path.exists(request_file):
                    mime_type, _ = mimetypes.guess_type(request_file)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    
                    # Special handling for PHP files
                    if request_file.endswith('.php'):
                        # For this example, just serve the PHP file as text
                        mime_type = 'text/plain'
                    
                    with open(request_file, 'rb') as f:
                        response_data = f.read()
                    
                    content_length = len(response_data)
                    response_header = f'HTTP/1.1 200 OK\r\nContent-Type: {mime_type}\r\nContent-Length: {content_length}\r\n\r\n'
                    response = response_header.encode('utf-8') + response_data
                    sock.sendall(response)
                else:
                    response_header = 'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n'
                    sock.sendall(response_header.encode('utf-8'))

except KeyboardInterrupt:        
    server_socket.close()
    sys.exit(0)
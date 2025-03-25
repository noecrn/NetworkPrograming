import socket
import threading
import select
import os
import datetime
import time
from typing import Dict, Set

class FileServer:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Add socket reuse option
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.clients: Dict[str, socket.socket] = {}
        self.client_locks = {}
        self.log_lock = threading.Lock()
        self.clients_lock = threading.Lock()
        self.running = True
        self.transfer_timeouts = 15.0  # Increased timeout for more reliability
        self.max_retries = 3
        print("📡 File Server initialized (ACK timeout: {}s)".format(self.transfer_timeouts))

    def log_activity(self, message: str):
        with self.log_lock:
            timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            log_entry = f"{timestamp} {message}"
            # Write to log file
            with open("server_log.txt", "a") as log:
                log.write(log_entry + "\n")
            # Print to console
            print(log_entry)

    def remove_client(self, client_id):
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id].close()
                del self.clients[client_id]
                del self.client_locks[client_id]
                self.log_activity(f"Client {client_id} disconnected")

    def handle_client(self, client_socket: socket.socket, client_address):
        client_id = None
        try:
            while True:
                message = client_socket.recv(1024).decode().strip()
                if not message:
                    break

                if message.startswith("REGISTER:"):
                    client_id = message.split(":")[1]
                    with self.clients_lock:
                        self.clients[client_id] = client_socket
                        self.client_locks[client_id] = threading.Lock()
                    self.log_activity(f"Client {client_id} registered")
                    client_socket.send("Registration successful".encode())

                elif message.startswith("SEND:"):
                    _, filename, filesize, sender_id = message.split(":")
                    filesize = int(filesize)
                    self.handle_file_transfer(sender_id, filename, filesize, client_socket)

        except Exception as e:
            self.log_activity(f"Error handling client {client_address}: {str(e)}")
        finally:
            if client_id:
                self.remove_client(client_id)
            else:
                client_socket.close()

    def handle_file_transfer(self, sender_id: str, filename: str, filesize: int, sender_socket: socket.socket):
        try:
            self.log_activity(f"📤 Client {sender_id} sending {filename} ({filesize} bytes)")
            
            # Receive file data with proper chunking
            file_data = bytearray()
            remaining = filesize
            progress = 0
            while remaining > 0:
                chunk = sender_socket.recv(min(4096, remaining))
                if not chunk:
                    raise RuntimeError("Connection broken during file transfer")
                file_data.extend(chunk)
                remaining -= len(chunk)
                new_progress = ((filesize - remaining) / filesize) * 100
                if int(new_progress / 20) > int(progress / 20):
                    self.log_activity(f"⏳ Receiving from {sender_id}: {new_progress:.1f}%")
                progress = new_progress

            self.log_activity(f"✅ Received complete file from {sender_id}")
            # Acknowledge receipt to sender
            sender_socket.send(f"RECEIVED:{filename}".encode())
            time.sleep(0.1)  # Small delay between messages

            # Forward to other clients
            with self.clients_lock:
                active_clients = [cid for cid in self.clients.keys() if cid != sender_id]
            
            if not active_clients:
                self.log_activity("ℹ️ No other clients connected")
                sender_socket.send("STATUS:No other clients connected".encode())
                return

            self.log_activity(f"📩 Forwarding to {len(active_clients)} clients: {', '.join(active_clients)}")
            failed_clients = set()

            for client_id in active_clients:
                retry_count = self.max_retries
                while retry_count > 0:
                    try:
                        with self.client_locks[client_id]:
                            client_socket = self.clients[client_id]
                            client_socket.settimeout(self.transfer_timeouts)
                            
                            try:
                                # Send file info with retry
                                info_msg = f"FILE:{filename}:{filesize}:{sender_id}"
                                retry_count = 3
                                while retry_count > 0:
                                    try:
                                        self.log_activity(f"📤 Sending to {client_id}: {info_msg}")
                                        client_socket.send(info_msg.encode())
                                        break
                                    except socket.timeout:
                                        retry_count -= 1
                                        if retry_count == 0:
                                            raise
                                        time.sleep(0.5)
                                
                                # Rest of the transfer code remains the same
                                # Send file data with progress
                                total_sent = 0
                                while total_sent < filesize:
                                    chunk_size = min(4096, filesize - total_sent)
                                    sent = client_socket.send(file_data[total_sent:total_sent + chunk_size])
                                    if sent == 0:
                                        raise RuntimeError(f"Connection to {client_id} broken")
                                    total_sent += sent
                                    if total_sent % (filesize // 10) == 0:  # Log every 10%
                                        self.log_activity(f"⏳ Progress to {client_id}: {(total_sent/filesize)*100:.1f}%")
                                
                                # Wait for ACK with proper timeout
                                self.log_activity(f"⏳ Waiting for ACK from {client_id}")
                                ack = client_socket.recv(1024).decode()
                                if ack == f"ACK:{filename}:{client_id}":
                                    self.log_activity(f"✅ Client {client_id} acknowledged {filename}")
                                    break
                                else:
                                    raise RuntimeError(f"Invalid ACK from {client_id}: {ack}")
                                
                            finally:
                                client_socket.settimeout(None)
                                
                    except socket.timeout:
                        retry_count -= 1
                        if retry_count > 0:
                            self.log_activity(f"⚠️ Retry {self.max_retries - retry_count} for {client_id}")
                            time.sleep(1)
                            continue
                        self.log_activity(f"❌ Timeout waiting for {client_id}")
                        failed_clients.add(client_id)
                    except Exception as e:
                        self.log_activity(f"❌ Error sending to {client_id}: {str(e)}")
                        failed_clients.add(client_id)
                        break

            # Log results
            success_count = len(active_clients) - len(failed_clients)
            self.log_activity(f"📊 File {filename} delivery summary: {success_count}/{len(active_clients)} successful")

            # Send final status to sender
            status_msg = f"STATUS:File delivered to {success_count}/{len(active_clients)} clients"
            sender_socket.send(status_msg.encode())

        except Exception as e:
            error_msg = f"❌ Error in file transfer: {str(e)}"
            self.log_activity(error_msg)
            sender_socket.send(f"ERROR:{str(e)}".encode())

    def stop(self):
        self.log_activity("🛑 Shutting down server...")
        self.running = False
        # Close all client connections
        with self.clients_lock:
            for client_id, client_socket in self.clients.items():
                try:
                    self.log_activity(f"👋 Closing connection to {client_id}")
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
            self.client_locks.clear()
        
        # Close server socket
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
        except:
            pass
        self.log_activity("✅ Server shutdown complete")

    def run(self):
        self.log_activity("🚀 File Server is running...")
        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    thread = threading.Thread(target=self.handle_client, 
                                           args=(client_socket, client_address))
                    thread.daemon = True  # Make thread daemon so it exits when main thread exits
                    thread.start()
                except socket.error:
                    if not self.running:
                        break
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.stop()

if __name__ == "__main__":
    server = None
    try:
        server = FileServer()
        server.run()
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if server:
            server.stop()
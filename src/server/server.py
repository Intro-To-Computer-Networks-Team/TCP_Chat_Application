import socket
import threading
import time
import sqlite3

# Server Configuration
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 4000       # Port to listen on
class ChatServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))

        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.init_db()
        self.clients = {}
        self.lock = threading.Lock()

    def init_db(self):
        connection = sqlite3.connect('server_chat.db', check_same_thread=False)
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                sender TEXT,
                receiver TEXT,
                message TEXT
            )
        ''')
        connection.commit()
        connection.close()

    def update_contacts(self):
        with self.lock:
            contact_list = ",".join(self.clients.keys())
            msg = f"CONTACTS:{contact_list}\n"
            print(f"[DEBUG CONTACT DATA]: {contact_list}")
            print(f"[DEBUG CLIENTS COUNT]: {len(self.clients)}")

        active_sockets = list(self.clients.values())
        for i, client_socket in enumerate(active_sockets):
            try:
                print(f"[DEBUG] Sending contact update to client #{i+1}")
                client_socket.send(msg.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Could not update contacts for client #{i+1}: {e}")

    def handle_client(self, client_socket):
        username = ""
        try:
            client_socket.send("Welcome! Please enter your username: ".encode('utf-8'))
            username = client_socket.recv(1024).decode('utf-8').strip()
            with self.lock:
                if username in self.clients:
                    client_socket.send("[Server]: Username already taken. Disconnecting.".encode('utf-8'))
                    client_socket.close()
                    return

            self.clients[username] = client_socket
            print(f"[NEW CONNECTION] {username} connected.")
            time.sleep(0.1)
            self.update_contacts()

            welcome= f"Connected successfully as {username}.\n"
            time.sleep(0.1)
            client_socket.send(welcome.encode('utf-8'))

            while True:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break

                if ':' in message:
                    target_name, msg_content = message.split(':', 1)
                    target_name = target_name.strip()
                    if target_name in self.clients:
                        dest_socket = self.clients[target_name]
                        dest_socket.send(f"{username}: {msg_content}".encode('utf-8'))
                    else:
                        client_socket.send(f"[SERVER]: User '{target_name}' not found.".encode('utf-8'))
                        self.update_contacts()

                else:
                    client_socket.send("[SERVER]: Invalid format. Use TARGET:MESSAGE".encode('utf-8'))

        except ConnectionResetError:
            print(f"[ERROR] Connection lost with {username}")
        except Exception as e:
            print(f"[ERROR] Error handling client {username}: {e}")
        finally:
            if username in self.clients:
                del self.clients[username]
                self.update_contacts()
                print(f"[DISCONNECT] {username} disconnected.")
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        try:
            client_socket.close()
        except Exception as e:
            print(f"[ERROR] Could not close client socket for {username}: {e}")

    def start_server(self):
        self.server_socket.listen(5)
        print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

        while True:
            client_sock, addr = self.server_socket.accept()
            print(f"[CONNECTION] Connection from {addr}")

            thread = threading.Thread(target=self.handle_client, args=(client_sock,))
            thread.start()

            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    server = ChatServer()
    server.start_server()


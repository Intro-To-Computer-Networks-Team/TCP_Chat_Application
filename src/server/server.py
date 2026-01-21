import socket
import threading
import time
import sqlite3

# ==================== SERVER CONFIGURATION ====================
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 4000       # Port to listen on
max_clients = 5  # Maximum number of concurrent client connections
# ==================== CHAT SERVER ====================
class ChatServer:
    """Multithreaded chat server handling client connections and message routing."""
    def __init__(self):
        """Initialize server socket, database, and client tracking structures."""
        # Create TCP socket for client connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))

        # Set socket options to optimize performance
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # Initialize database for message persistence
        self.init_db()

        # Dictionary mapping usernames to their socket connections
        self.clients = {}

        # Lock for thread-safe access to shared client dictionary
        self.lock = threading.Lock()

    # ==================== DATABASE SETUP ====================
    def init_db(self):
        """Create database and messages table if they don't exist."""
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

    # ==================== CONTACT LIST MANAGEMENT ====================
    def update_contacts(self):
        """Broadcast updated list of online users to all connected clients."""
        # Build comma-separated list of online usernames
        with self.lock:
            contact_list = ",".join(self.clients.keys())
            msg = f"CONTACTS:{contact_list}\n"
            print(f"[DEBUG CONTACT DATA]: {contact_list}")
            print(f"[DEBUG CLIENTS COUNT]: {len(self.clients)}")
        # Send updated contact list to all connected clients
        active_sockets = list(self.clients.values())
        for i, client_socket in enumerate(active_sockets):
            try:
                print(f"[DEBUG] Sending contact update to client #{i+1}")
                client_socket.send(msg.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Could not update contacts for client #{i+1}: {e}")

    # ==================== CLIENT CONNECTION HANDLER ====================
    def handle_client(self, client_socket):
        """Handle individual client connection: authentication, message routing, and cleanup."""
        username = ""
        try:
            # ==================== AUTHENTICATION PHASE ====================
            # Request username from newly connected client
            client_socket.send("Welcome! Please enter your username: ".encode('utf-8'))
            username = client_socket.recv(1024).decode('utf-8').strip()

            # Check if username is already taken
            with self.lock:
                if username in self.clients:
                    client_socket.send("[Server]: Username already taken. Disconnecting.".encode('utf-8'))
                    client_socket.close()
                    return

            # Register new client in the clients dictionary
            self.clients[username] = client_socket
            print(f"[NEW CONNECTION] {username} connected.")

            # Notify all clients of updated contact list
            time.sleep(0.1)
            self.update_contacts()

            # Send welcome message to the newly connected client
            welcome= f"Connected successfully as {username}.\n"
            time.sleep(0.1)
            client_socket.send(welcome.encode('utf-8'))

            # ==================== MESSAGE ROUTING LOOP ====================
            while True:
                # Continuously listen for messages from this client
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break

                if ':' in message:
                    # Parse message format: "recipient:content"
                    target_name, msg_content = message.split(':', 1)
                    target_name = target_name.strip()

                    if target_name in self.clients:
                        # Route message to target recipient if online
                        dest_socket = self.clients[target_name]
                        dest_socket.send(f"{username}: {msg_content}".encode('utf-8'))
                    else:
                        # Notify sender if recipient is not found
                        client_socket.send(f"[Server]: User '{target_name}' not found.".encode('utf-8'))
                        self.update_contacts()

        except ConnectionResetError:
            print(f"[ERROR] Connection lost with {username}")
            self.notify_disconnection(username)
        except Exception as e:
            print(f"[ERROR] Error handling client {username}: {e}")
            self.notify_disconnection(username)
        finally:
            # ==================== CLEANUP ON DISCONNECT ====================
            # Remove client from active clients list
            if username in self.clients:
                del self.clients[username]
                # Notify remaining clients about updated contact list
                time.sleep(0.1)
                print(f"[DISCONNECT] {username} disconnected.")
                time.sleep(0.1)
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
                self.update_contacts()

        # Close the client socket
        try:
            client_socket.close()
        except Exception as e:
            print(f"[ERROR] Could not close client socket for {username}: {e}")

    # ==================== DISCONNECTION NOTIFICATION ====================
    def notify_disconnection(self, disconnected_username):
        """Notify all clients about a user's disconnection."""
        msg = f"[Server]: User: '{disconnected_username}' has disconnected."
        active_sockets = list(self.clients.values())
        for client_socket in active_sockets:
            try:
                client_socket.send(msg.encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Could not notify disconnection to a client: {e}")
    # ==================== SERVER MAIN LOOP ====================
    def start_server(self):
        """Start listening for incoming client connections and spawn handler threads."""
        # Begin listening for incoming connections (queue up to 5)
        self.server_socket.listen(max_clients) # Allow up to 5 queued connections (change as needed)
        print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

        # Accept and handle client connections continuously
        while True:
            # Accept new client connection
            client_sock, addr = self.server_socket.accept()
            print(f"[CONNECTION] Connection from {addr}")

            #Check for maximum connections
            with self.lock:
                if len(self.clients) >=max_clients: # Max 5 connections (change as needed)
                    print(f"[MAX CONNECTIONS REACHED] Rejecting connection from {addr}")
                    try:
                        client_sock.send("[Server]: Maximum connections reached. Try again later.".encode('utf-8'))
                    except Exception as e:
                        print(f"[ERROR] Could not send max connection message to {addr}: {e}")
                    client_sock.close()
                    continue

            # Spawn new thread to handle this client
            thread = threading.Thread(target=self.handle_client, args=(client_sock,))
            thread.start()

            # Display current number of active connections
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

# ==================== SERVER ENTRY POINT ====================
if __name__ == "__main__":
    # Create and start the chat server
    server = ChatServer()
    server.start_server()


import socket
import threading

# Server Configuration
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 4444       # Port to listen on

# Dictionary to store connected clients: {username: socket_object}
clients = {}

def handle_client(client_socket):
    """
    Handles the connection for a single client in a separate thread.
    Manages authentication (username) and message routing.
    """
    username = ""
    try:
        # Step 1: Registration - Request and receive username
        client_socket.send("Welcome! Please enter your username: ".encode('utf-8'))
        username = client_socket.recv(1024).decode('utf-8').strip()
        
        # Check if username is already taken
        if username in clients:
            client_socket.send("Username already taken. Disconnecting.".encode('utf-8'))
            client_socket.close()
            return

        # Add client to the active list
        clients[username] = client_socket
        print(f"[NEW CONNECTION] {username} connected.")
        
        # Send instructions to the client
        instructions = f"Connected successfully as {username}.\nTo chat, use format: DEST_NAME:MESSAGE"
        client_socket.send(instructions.encode('utf-8'))

        # Step 2: Main loop - Listen for messages from this client
        while True:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break # Client disconnected

            # Expected message format: TARGET_NAME:MESSAGE_CONTENT
            if ':' in message:
                target_name, msg_content = message.split(':', 1)
                
                # Check if the target user exists
                if target_name in clients:
                    dest_socket = clients[target_name]
                    # Forward the message to the target client
                    dest_socket.send(f"[{username}]: {msg_content}".encode('utf-8'))
                else:
                    # Notify sender that user was not found
                    client_socket.send(f"[SERVER]: User '{target_name}' not found.".encode('utf-8'))
            else:
                client_socket.send("[SERVER]: Invalid format. Use TARGET:MESSAGE".encode('utf-8'))

    except ConnectionResetError:
        print(f"[ERROR] Connection lost with {username}")
    except Exception as e:
        print(f"[ERROR] Error handling client {username}: {e}")
    finally:
        # Cleanup: Remove client from list and close socket
        if username in clients:
            del clients[username]
            print(f"[DISCONNECT] {username} disconnected.")
        client_socket.close()

def start_server():
    """
    Main function to start the server and accept incoming connections.
    """
    # Create a TCP/IP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the address and port
    server.bind((HOST, PORT))
    
    # Listen for incoming connections (queue of 5)
    server.listen(5)
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        # Accept a new connection
        client_sock, addr = server.accept()
        print(f"[CONNECTION] Connection from {addr}")
        
        # Create a new thread to handle this client specifically
        thread = threading.Thread(target=handle_client, args=(client_sock,))
        thread.start()
        
        # specific to project requirements: Handle multiple clients concurrently
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()
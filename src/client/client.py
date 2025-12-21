import socket
import threading
import sys

# Server Connection Details
SERVER_IP = '127.0.0.1' # Localhost (change this if server is on another machine)
SERVER_PORT = 4444

def receive_messages(sock):
    """
    Function running in a separate thread to listen for incoming messages
    from the server continuously.
    """
    while True:
        try:
            # Receive message from server
            msg = sock.recv(1024).decode('utf-8')
            if msg:
                print(f"\n{msg}\n>>> ", end="") # Print message and restore prompt
            else:
                # Empty message indicates server closed connection
                print("\n[DISCONNECTED] Server closed connection.")
                sock.close()
                break
        except Exception as e:
            print(f"\n[ERROR] Reading error: {e}")
            sock.close()
            break

def start_client():
    """
    Main function to connect to the server and handle user input.
    """
    # Create a TCP/IP socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        client.connect((SERVER_IP, SERVER_PORT))
    except Exception as e:
        print(f"Could not connect to server: {e}")
        return

    # Registration Phase
    try:
        # Receive welcome message
        welcome_msg = client.recv(1024).decode('utf-8')
        print(welcome_msg, end="") 
        
        # Send username
        username = input()
        client.send(username.encode('utf-8'))
    except Exception as e:
        print("Error during registration")
        client.close()
        return

    # Start a background thread to receive messages
    # This allows receiving messages while waiting for user input (blocking)
    receive_thread = threading.Thread(target=receive_messages, args=(client,))
    receive_thread.daemon = True # Thread ends when main program ends
    receive_thread.start()

    # Main Loop: Send messages
    print(">>> ", end="")
    while True:
        try:
            msg = input()
            
            # Allow user to quit cleanly
            if msg.lower() == 'quit':
                break
            
            # Send message to server
            client.send(msg.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
            break

    client.close()

if __name__ == "__main__":
    start_client()
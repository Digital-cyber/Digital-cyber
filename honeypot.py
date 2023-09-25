import socket
import threading

# Define the honeypot web server configuration
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 80         # Listen on port 80 (HTTP)

# Define a simple HTTP response that the honeypot will send to attackers
HTTP_RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"

# Define a function to handle incoming client connections
def handle_client(client_socket):
    # Send the honeypot HTTP response to the client
    client_socket.send(HTTP_RESPONSE)
    # Log the connection and any other information you need
    print(f"[*] Connection from: {client_socket.getpeername()}")

    # Close the client socket
    client_socket.close()

# Create a socket to listen for incoming connections
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)  # Allow up to 5 simultaneous connections

print(f"[*] Listening on {HOST}:{PORT}")

# Accept and handle incoming connections in a loop
while True:
    client_socket, addr = server.accept()
    print(f"[*] Accepted connection from: {addr[0]}:{addr[1]}")
    
    # Start a new thread to handle the client
    client_handler = threading.Thread(target=handle_client, args=(client_socket,))
    client_handler.start()

import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 6880))  # Bind to all interfaces
server_socket.listen(5)
print(f"Server is listening on {server_socket.getsockname()}")
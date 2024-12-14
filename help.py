import socket

def get_local_ip():
    try:
        # Create a socket connection to Google's DNS server
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # Connect to 8.8.8.8 on port 80 (no actual data sent)
            local_ip = s.getsockname()[0]  # Get the local IP address
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None

# Example usage
my_ip = get_local_ip()
if my_ip:
    print(f"My local IP address: {my_ip}")
import pickle
import socket
from multiprocessing import freeze_support
from time import sleep

from tqdm import tqdm

freeze_support()

TCP_PORT = 12345       # Must match the server's TCP port
UDP_PORT = 54321       # Must match the server's UDP discovery port
DISCOVERY_MSG = "DISCOVER_SERVER"
RESPONSE_MSG = "SERVER_HERE"
BROADCAST_ADDR = '<broadcast>'  # Special address for UDP broadcast

def discover_server(timeout=3):
    """
    Send a UDP broadcast to discover the server.
    Returns the server's IP address if found, otherwise None.
    """
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)

    try:
        print("[UDP] Sending discovery broadcast...")
        udp_sock.sendto(DISCOVERY_MSG.encode('utf-8'), (BROADCAST_ADDR, UDP_PORT))
        data, addr = udp_sock.recvfrom(9988)
        if data.decode('utf-8') == RESPONSE_MSG:
            print(f"[UDP] Server discovered at {addr[0]}")
            return addr[0]
    except socket.timeout:
        print("[UDP] Discovery timed out. No server found.")
    except Exception as e:
        print(f"[UDP] Error during discovery: {e}")
    return None

def send_folder(folder_path, tcp_sock, log_callback=print):
    """
    Walk through folder_path and send each file (its relative path and content)
    to the server over the provided TCP socket.
    """
    import os
    files = [os.path.join(root, file)
             for root, _, files in os.walk(folder_path)
             for file in files]

    with tqdm(total=len(files), desc="Sending files", unit="file") as pbar:
        for file_path in files:
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                file_info = pickle.dumps({
                    "file_name": os.path.relpath(file_path, folder_path).replace("\\", "/"),
                    "file_data": file_data
                })
                # Send length first, then the data.
                tcp_sock.sendall(len(file_info).to_bytes(4, 'big'))
                tcp_sock.sendall(file_info)
                sleep(0.05)  # Let the server process
                pbar.update(1)
                log_callback(f"[TCP] Sent {file_path}")
            except Exception as e:
                log_callback(f"[TCP] Error sending file {file_path}: {e}")

    try:
        tcp_sock.sendall(b"EOF")  # Indicate end of transmission
    except Exception as e:
        log_callback(f"[TCP] Error sending EOF: {e}")
    log_callback("[TCP] Folder transfer complete.")

def tcp_client(server_ip, folder_path, log_callback=print):
    """
    Connect to the server via TCP and send the folder.
    """
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        log_callback(f"[TCP] Connecting to server at {server_ip}:{TCP_PORT} ...")
        tcp_sock.connect((server_ip, TCP_PORT))
        sleep(1)
        send_folder(folder_path, tcp_sock, log_callback=log_callback)
        log_callback("[TCP] Folder sent successfully.")
    except Exception as e:
        log_callback(f"[TCP] Error: {e}")
    finally:
        tcp_sock.close()

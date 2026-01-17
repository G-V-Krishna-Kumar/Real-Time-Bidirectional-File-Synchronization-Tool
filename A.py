import socket
import threading
import os
import time
import hashlib

FOLDER = "Folder 1"
PEER_IP = "127.0.0.1"    
PEER_PORT = 5001         
LOCAL_PORT = 5000        
POLL_INTERVAL = 1     

os.makedirs(FOLDER, exist_ok=True)

file_hashes = {}      
ignore_changes = set()

def get_file_hash(path):
    """Return MD5 hash of file contents"""
    if not os.path.exists(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()

def send_file(filename, operation):
    filepath = os.path.join(FOLDER, filename)
    filesize = os.path.getsize(filepath) if operation != "DELETE" else 0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PEER_IP, PEER_PORT))
            s.sendall(operation.encode().ljust(6))       
            s.sendall(filename.encode().ljust(256))      
            s.sendall(str(filesize).encode().ljust(16)) 
            if operation != "DELETE":
                with open(filepath, "rb") as f:
                    while chunk := f.read(4096):
                        s.sendall(chunk)
    except Exception as e:
        print(f"[Send Error] {filename}: {e}")

def handle_client(conn):
    try:
        operation = conn.recv(6).decode().strip()
        filename = conn.recv(256).decode().strip()
        filesize = int(conn.recv(16).decode().strip())
        filepath = os.path.join(FOLDER, filename)

        if operation != "DELETE":
            ignore_changes.add(filename)

        if operation == "DELETE":
            if os.path.exists(filepath):
                os.remove(filepath)
                file_hashes.pop(filename, None)
                print(f"[Received] Deleted: {filename}")
        else:
            with open(filepath, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = conn.recv(min(4096, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
            file_hashes[filename] = get_file_hash(filepath)
            print(f"[Received] {operation}: {filename}")

    except Exception as e:
        print(f"[Receive Error] {filename}: {e}")
    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", LOCAL_PORT))
        s.listen()
        print(f"Listening on port {LOCAL_PORT}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

def poll_folder():
    global file_hashes
    while True:
        time.sleep(POLL_INTERVAL)
        current_files = {f: get_file_hash(os.path.join(FOLDER, f)) 
                         for f in os.listdir(FOLDER)}

        for f, h in current_files.items():
            if f in ignore_changes:
                ignore_changes.remove(f)
                continue
            if f not in file_hashes:
                file_hashes[f] = h
                print(f"[Local] Created: {f}")
                send_file(f, "CREATE")
            elif file_hashes[f] != h:
                file_hashes[f] = h
                print(f"[Local] Modified: {f}")
                send_file(f, "UPDATE")

        # Detect deleted files
        for f in list(file_hashes.keys()):
            if f not in current_files:
                file_hashes.pop(f)
                if f in ignore_changes:
                    ignore_changes.remove(f)
                    continue
                print(f"[Local] Deleted: {f}")
                send_file(f, "DELETE")

threading.Thread(target=start_server, daemon=True).start()
threading.Thread(target=poll_folder, daemon=True).start()

print(f"Monitoring folder: {FOLDER}")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting...")
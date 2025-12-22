import socket
import threading
import time

def worker(i):
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', 8080))
        request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        s.send(request)
        data = s.recv(4096)
        s.close()
        end = time.time()
        print(f"[{i}] Status: OK, Bytes: {len(data)}, Time: {end-start:.4f}s")
    except Exception as e:
        print(f"[{i}] Error: {e}")

threads = []
print("Starting 10 concurrent requests...")
for i in range(10):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Done.")

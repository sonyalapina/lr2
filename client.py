import os
import time

def client():
    fifo_to_server = "/tmp/ping_fifo"
    fifo_from_server = "/tmp/pong_fifo"
    
    if not os.path.exists(fifo_to_server): os.mkfifo(fifo_to_server)
    if not os.path.exists(fifo_from_server): os.mkfifo(fifo_from_server)
    
    for i in range(5):
        with open(fifo_to_server, 'w') as f:
            f.write("PING")
            print(f"Клиент отправил: PING")
        
        with open(fifo_from_server, 'r') as f:
            response = f.read().strip()
            print(f"Клиент получил: {response}")
        
        time.sleep(1)

if __name__ == "__main__":
    client()

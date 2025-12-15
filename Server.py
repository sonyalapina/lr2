#!/usr/bin/env python3

import os
import sys
import errno
import time
import uuid
import signal

def server(server_id=None):
    if server_id is None:
        server_id = str(uuid.uuid4())[:4]
    
    shared_file = f"/tmp/shared_communication_{server_id}.txt"
    
    clients_file = f"/tmp/clients_info_{server_id}.txt"
    
    is_shutting_down = False
    
    def shutdown_handler(signum, frame):
        nonlocal is_shutting_down
        if not is_shutting_down:
            is_shutting_down = True
            print(f"\nThe server {server_id} is closing...")
            
            try:
                if os.path.exists(shared_file):
                    fd = os.open(shared_file, os.O_RDWR)
                    try:
                        os.lockf(fd, os.F_LOCK, 0)
                        
                        shutdown_msg = "SERVER_SHUTDOWN"
                        os.lseek(fd, 0, os.SEEK_SET)
                        os.write(fd, shutdown_msg.encode('utf-8'))
                        os.ftruncate(fd, len(shutdown_msg))
                        
                        os.fsync(fd)
                        
                        os.lockf(fd, os.F_ULOCK, 0)
                    except Exception as e:
                        try:
                            os.lockf(fd, os.F_ULOCK, 0)
                        except:
                            pass
                    finally:
                        os.close(fd)
            except Exception as e:
                print(f"Error when notifying clients: {e}")
            
            time.sleep(1)
            
            if os.path.exists(shared_file):
                os.unlink(shared_file)
                print(f"{shared_file} file deleted")
            
            if os.path.exists(clients_file):
                os.unlink(clients_file)
                print(f"{clients_file} file deleted")
            
            sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        with open(clients_file, 'w') as f:
            f.write("0")
    except:
        pass

    print("\n")
    print(f"The {server_id} server is running")
    print(f"The communication file: {shared_file}")
    print("To connect the client, use the command:")
    print(f"python3 upd_client.py {server_id}")
    print("To end the server, click Ctrl+C")
    print()
    
    try:
        with open(shared_file, 'w') as f:
            pass
        print(f"The {shared_file} file is ready")

        print("Waiting for a request from the client...\n")
        
        while True:
            try:
                fd = os.open(shared_file, os.O_RDWR)
                
                try:
                    os.lockf(fd, os.F_LOCK, 0)
                    
                    os.lseek(fd, 0, os.SEEK_SET)
                    
                    data = os.read(fd, 1024)
                    
                    if data:
                        message_data = data.decode('utf-8').strip()
                        
                        if message_data == "SERVER_SHUTDOWN":
                            os.lseek(fd, 0, os.SEEK_SET)
                            os.write(fd, b" ")
                            os.fsync(fd)
                        elif ':' in message_data:
                            client_num, message = message_data.split(':', 1)
                            client_num = client_num.strip()
                            message = message.strip()
                            
                            print(f"The server {server_id}: message from the client №{client_num}: {message}")
                            
                            time.sleep(1)
                            os.ftruncate(fd, 0)

                            if message.lower() == "ping":
                                response = f'The client №{client_num}: "pong" from the server {server_id}'
                                os.lseek(fd, 0, os.SEEK_SET)
                                os.write(fd, response.encode('utf-8'))
                                print(f'The server {server_id}: "pong" sent to the client №{client_num}')
                                
                                os.fsync(fd)                            
                            else:
                                error_msg = f"The server {server_id}: client №{client_num}: invalid request"
                                print(error_msg)
                                os.lseek(fd, 0, os.SEEK_SET)
                                os.write(fd, b" ")
                                os.fsync(fd)
                        else:                            
                            print(f"The server {server_id}: invalid request: {message_data}")
                            os.lseek(fd, 0, os.SEEK_SET)
                            os.write(fd, b" ")
                            os.fsync(fd)
                        
                        print("\n")
                    
                    os.lockf(fd, os.F_ULOCK, 0)
                    
                except Exception as e:
                    try:
                        os.lockf(fd, os.F_ULOCK, 0)
                    except:
                        pass
                    raise
            
                os.close(fd)
                time.sleep(0.1)
                    
            except KeyboardInterrupt:
                continue
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
                continue
                
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    server_id = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(server(server_id))

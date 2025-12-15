#!/usr/bin/env python3
import os
import time
import sys
import errno
import threading

def client(server_id):
    #используем тот же файл что и сервер
    shared_file = f"/tmp/shared_communication_{server_id}.txt"
    
    if not os.path.exists(shared_file):
        print(f"The server with ID '{server_id}' is not running or the file is not found")
        print("Start the server with the command: python server.py [server_id]")
        return 1
    
    #файл для хранения информации о клиентах
    clients_file = f"/tmp/clients_info_{server_id}.txt"
    client_number = None
    
    #флаг для завершения работы
    shutdown_event = threading.Event()
    
    #получаем номер клиента
    try:
        fd = os.open(clients_file, os.O_RDWR | os.O_CREAT)
        os.lockf(fd, os.F_LOCK, 0)
        
        #читаем текущее кол-во клиентов
        try:
            data = os.read(fd, 1024)
            if data:
                current_clients = int(data.decode('utf-8').strip())
            else:
                current_clients = 0
        except:
            current_clients = 0
        
        client_number = current_clients + 1
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, str(client_number).encode('utf-8'))
        os.ftruncate(fd, len(str(client_number)))
        os.fsync(fd)
        
        os.lockf(fd, os.F_ULOCK, 0)
        os.close(fd)
        
        print(f"\nConnecting to the server {server_id}")
        print(f"You are a client №{client_number}")
        print("Enter a request or 'exit' to exit\n")
        
    except Exception as e:
        print(f"Error when receiving the client's number: {e}")
        return 1
    
    #фоновый мониторинг сервера
    def monitor_server():
        last_check = 0
        check_interval = 0.5
        
        while not shutdown_event.is_set():
            current_time = time.time()
            if current_time - last_check >= check_interval:
                last_check = current_time
                
                #проверяем наличие файлов сервера
                if not os.path.exists(shared_file) or not os.path.exists(clients_file):
                    shutdown_event.set()
                    print(f"\nThe server is disabled")
                    os._exit(0)
                    return
                
                #проверяем есть ли сообщения о завершении сервера
                try:
                    if os.path.exists(shared_file):
                        fd = os.open(shared_file, os.O_RDWR)
                        try:
                            os.lockf(fd, os.F_LOCK, 0)
                            os.lseek(fd, 0, os.SEEK_SET)
                            data = os.read(fd, 1024)
                            
                            if data:
                                response = data.decode('utf-8')
                                if response.strip() == "SERVER_SHUTDOWN":
                                    shutdown_event.set()
                                    print(f"\nThe server is disabled")
                                    os._exit(0)
                                    return
                            
                            os.lockf(fd, os.F_ULOCK, 0)
                        except:
                            try:
                                os.lockf(fd, os.F_ULOCK, 0)
                            except:
                                pass
                        finally:
                            os.close(fd)
                except:
                    pass
            
            time.sleep(0.1)
    
    #фоновый мониторинг
    monitor_thread = threading.Thread(target=monitor_server, daemon=True)
    monitor_thread.start()
    
    try:
        while not shutdown_event.is_set():
            try:
                user_input = input("Enter a request: ").strip()
                
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("\nClient shutdown...")
                break
            except Exception as e:
                continue
            
            if shutdown_event.is_set():
                print(f"\nThe server is disabled")
                os._exit(0)
                return 0
            
            if user_input.lower() == "exit":
                print(f"Client №{client_number} is closing...")
                
                #уменьшаем счетчик клиентов при выходе
                try:
                    fd = os.open(clients_file, os.O_RDWR)
                    os.lockf(fd, os.F_LOCK, 0)
                    
                    data = os.read(fd, 1024)
                    if data:
                        current_clients = int(data.decode('utf-8').strip())
                        if current_clients > 0:
                            new_count = current_clients - 1
                            os.lseek(fd, 0, os.SEEK_SET)
                            os.write(fd, str(new_count).encode('utf-8'))
                            os.ftruncate(fd, len(str(new_count)))
                    
                    os.lockf(fd, os.F_ULOCK, 0)
                    os.close(fd)
                except:
                    pass
                    
                break

            if not user_input:
                print(f"Error: The request cannot be empty\n")
                continue
            
            try:
                if shutdown_event.is_set():
                    print(f"\nThe server is disabled")
                    os._exit(0)
                    return 0
                
                #открываем файл для записи с блокировкой
                fd = os.open(shared_file, os.O_RDWR)
                os.lockf(fd, os.F_LOCK, 0)
                
                #записываем запрос в файл с номером клиента
                request_data = f"{client_number}:{user_input}"
                os.lseek(fd, 0, os.SEEK_SET)
                os.write(fd, request_data.encode('utf-8'))
                
                #сбрасываем на диск(синхронизируем)
                os.fsync(fd)
                
                #снимаем блокировку
                os.lockf(fd, os.F_ULOCK, 0)
                os.close(fd)
                
                response_received = False
                timeout = 5
                start_time = time.time()
                
                while not response_received and not shutdown_event.is_set() and (time.time() - start_time) < timeout:
                    try:                        
                        fd = os.open(shared_file, os.O_RDWR)                       
                        os.lockf(fd, os.F_LOCK, 0)
                        os.lseek(fd, 0, os.SEEK_SET)
                        data = os.read(fd, 1024)
                        
                        if data:
                            response = data.decode('utf-8')
                            response_trimmed = response.strip()
                            
                            #проверяем не пришло ли сообщение о завершении сервера
                            if response_trimmed == "SERVER_SHUTDOWN":
                                shutdown_event.set()
                                print(f"\nThe server is disabled")
                                os._exit(0)
                                return 0
                            elif response == " ":
                                #ответ от сервера на неверный запрос
                                print(f"Error: Invalid request (the server did not recognize the command)")
                                response_received = True
                            elif response_trimmed:
                                #проверяем, что ответ и наш запрос это не одно и то же
                                if "pong" in response_trimmed.lower() or "server" in response_trimmed.lower():
                                    print(f"{response_trimmed}")
                                    response_received = True
                                elif not response_trimmed.startswith(f"{client_number}:"):
                                    print(f"{response_trimmed}")
                                    response_received = True
                            
                            #очищаем файл если получили ответ
                            if response_received:
                                os.ftruncate(fd, 0)

                        os.lockf(fd, os.F_ULOCK, 0)
                        os.close(fd)
                   
                    except Exception as e:
                        #если файл не найден значит сервер завершил работу
                        if isinstance(e, FileNotFoundError):
                            shutdown_event.set()
                            print(f"\nThe server is disabled")
                            os._exit(0)
                            return 0
                        
                        try:
                            if 'fd' in locals():
                                os.lockf(fd, os.F_ULOCK, 0)
                                os.close(fd)
                        except:
                            pass
                        continue
                    
                    if not response_received and not shutdown_event.is_set():
                        time.sleep(0.1)
                
                if shutdown_event.is_set():
                    print(f"\nThe server is disabled")
                    os._exit(0)
                    return 0
                
                if not response_received:
                    print(f"Timeout: the server did not respond")
                
                print()
           
            except FileNotFoundError:
                shutdown_event.set()
                print(f"\nThe server is disabled")
                os._exit(0)
                return 0
            except OSError as e:
                if e.errno == errno.EACCES:
                    print(f"File access error")
                else:
                    shutdown_event.set()
                    print(f"\nThe server is disabled")
                    os._exit(0)
                return 0
            except Exception as e:
                print(f"Unexpected error: {e}")
                break
    
    except KeyboardInterrupt:
        print(f"\nClient №{client_number} is closing...")
        shutdown_event.set()
        
        #уменьшаем счетчик клиентов при прерывании
        try:
            fd = os.open(clients_file, os.O_RDWR)
            os.lockf(fd, os.F_LOCK, 0)
            
            data = os.read(fd, 1024)
            if data:
                current_clients = int(data.decode('utf-8').strip())
                if current_clients > 0:
                    new_count = current_clients - 1
                    os.lseek(fd, 0, os.SEEK_SET)
                    os.write(fd, str(new_count).encode('utf-8'))
                    os.ftruncate(fd, len(str(new_count)))
            
            os.lockf(fd, os.F_ULOCK, 0)
            os.close(fd)
        except:
            pass
        
        os._exit(0)

    shutdown_event.set()
    time.sleep(0.5)
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using: python client.py <server_id>")
        print("Example: python client.py server1")
        sys.exit(1)
    
    server_id = sys.argv[1]
    sys.exit(client(server_id))

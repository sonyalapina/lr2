#!/usr/bin/env python3
import os
import sys
import time

def server_logic():
    shared_file = "/tmp/shared_communication.txt"
    
    print("\nСервер запущен и ожидает сообщения...")
    print("Для завершения нажмите Ctrl+C\n")
    if not os.path.exists(shared_file):
        with open(shared_file, 'w') as f:
            pass
        print(f"Создан общий файл: {shared_file}")

    print("Ожидание запроса от клиента...")
    
    while True:
        try:
            fd = os.open(shared_file, os.O_RDWR)
            os.lockf(fd, os.F_LOCK, 0)

            os.lseek(fd, 0, os.SEEK_SET)
            
            data = os.read(fd, 1024)
            
            if data:
                message = data.decode('utf-8').strip()
                print(f"Получено сообщение: '{message}'")
                
                #Очищаем файл
                os.ftruncate(fd, 0)
                
                if message.lower() == "ping":
                    response = "pong"
                else:
                    response = f"error: expected 'ping', got '{message}'"
                
                os.lseek(fd, 0, os.SEEK_SET)
                os.write(fd, response.encode('utf-8'))
                print(f"Отправлен ответ: '{response}'")
                
                os.fsync(fd)
                
                print("=" * 40 + "\n")
            
            os.lockf(fd, os.F_ULOCK, 0)

            os.close(fd)
            
            #Небольшая пауза
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nСервер завершает работу...")
            break

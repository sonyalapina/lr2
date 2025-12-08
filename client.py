#!/usr/bin/env python3
import os
import time
import sys

def client():
    shared_file = "/tmp/shared_communication.txt" #Общий файл для общения  
    if not os.path.exists(shared_file):
        print("Запустите сначала сервер")
        return 1
    print("\nВведите 'ping' для запроса")
    print("Или 'exit' для выхода\n")
    
    while True:
        user_input = input("Введите сообщение: ").strip()
        if user_input.lower() == "exit":
            print("Завершение работы клиента...")
            break
        print(f"\nОтправка запроса '{user_input}' серверу...")
        fd = os.open(shared_file, os.O_RDWR)
        os.lockf(fd, os.F_LOCK, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, user_input.encode('utf-8'))
        os.fsync(fd)
        print(f"Запрос записан в файл")
        os.lockf(fd, os.F_ULOCK, 0)
        os.close(fd)
        print("Ожидание ответа от сервера...")
        response_received = False
        timeout = 5
        start_time = time.time()
        
        while not response_received and (time.time() - start_time) < timeout:
            fd = os.open(shared_file, os.O_RDWR)
            os.lockf(fd, os.F_LOCK, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            data = os.read(fd, 1024)
            if data:
                response = data.decode('utf-8').strip()
                if response != user_input:
                    print(f"Получен ответ от сервера: '{response}'")
                    response_received = True     
                    os.ftruncate(fd, 0)
            os.lockf(fd, os.F_ULOCK, 0)
            os.close(fd)
            if not response_received: time.sleep(0.1)
                
        if not response_received: print("Таймаут: сервер не ответил")
        print(f"\n{'~' * 44}\n")
    return 0

if __name__ == "__main__":
    sys.exit(client())

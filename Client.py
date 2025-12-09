#!/usr/bin/env python3
import os
import time
import sys
import errno

def client():
    shared_file = "/tmp/shared_communication.txt"
    
    if not os.path.exists(shared_file):
        print("Для начала запустите сервер:)")
        return 1
    
    print("\nВведите запрос или 'exit' для выхода\n")
    
    try:    
        while True:
            user_input = input("Введите сообщение: ").strip()
            
            if user_input.lower() == "exit":
                print("Завершение работы клиента...")
                break

            if not user_input:                
                print("Ошибка: запрос не может быть пустым\n")
                continue
            
            try:            
                #открываем файл для записи с блокировкой
                fd = os.open(shared_file, os.O_RDWR)            
                os.lockf(fd, os.F_LOCK, 0)
                
                #записываем запрос в файл
                os.lseek(fd, 0, os.SEEK_SET)
                os.write(fd, user_input.encode('utf-8'))
                
                #сбрасываем на диск
                os.fsync(fd)
                
                #снимаем блокировку
                os.lockf(fd, os.F_ULOCK, 0)
                os.close(fd)
                
                response_received = False
                timeout = 5
                start_time = time.time()
                
                while not response_received and (time.time() - start_time) < timeout:
                    try:
                        #открываем для чтения
                        fd = os.open(shared_file, os.O_RDWR)
                        
                        #блокируем для чтения
                        os.lockf(fd, os.F_LOCK, 0)
                        
                        #читаем ответ
                        os.lseek(fd, 0, os.SEEK_SET)
                        data = os.read(fd, 1024)
                        
                        if data:
                            response = data.decode('utf-8')
                            
                            if response == " ":
                                print("Ошибка: неверный запрос")
                                response_received = True
                            else:
                                response_stripped = response.strip()
                                if response_stripped != user_input:
                                    print(f"Получен ответ от сервера: {response_stripped}")
                                    response_received = True
                            
                            #очищаем файл
                            if response_received:
                                os.ftruncate(fd, 0)

                        os.lockf(fd, os.F_ULOCK, 0)
                        os.close(fd)
                        
                    except KeyboardInterrupt:
                        raise
                    except Exception as e:
                        try:
                            os.lockf(fd, os.F_ULOCK, 0)
                            os.close(fd)
                        except:
                            pass
                        continue
                    
                    if not response_received:
                        time.sleep(0.1)
                
                if not response_received:
                    print("Таймаут: сервер не ответил")
                
                print("\n")
           
            except OSError as e:
                if e.errno == errno.EACCES:
                    print("Ошибка доступа к файлу")
                break
            except Exception as e:
                print(f"Неожиданная ошибка: {e}")
                break
    
    except KeyboardInterrupt:
        print("\nЗавершение работы клиента...")
    
    return 0

if __name__ == "__main__":
    sys.exit(client())

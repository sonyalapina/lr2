#!/usr/bin/env python3
import os
import sys
import errno
import time

def server():
    #общbq файл для общения
    shared_file = "/tmp/shared_communication.txt"
    
    try:
        #cоздаем файл если его пока нет
        if not os.path.exists(shared_file):
            with open(shared_file, 'w') as f:
                pass
            print(f"Создан общий файл: {shared_file}")

        print("Ожидание запроса от клиента...")
        
        while True:
            try:
                #открываем файл для чтения
                fd = os.open(shared_file, os.O_RDWR)

                try:
                    #блокируем файл
                    os.lockf(fd, os.F_LOCK, 0)
                    
                    #перемещаем указатель в начало
                    os.lseek(fd, 0, os.SEEK_SET)
                    
                    #читаем данные
                    data = os.read(fd, 1024)
                    
                    if data:
                        message = data.decode('utf-8').strip()
                        print(f"Получено сообщение: '{message}'")
                        
                        #очищаем файл
                        os.ftruncate(fd, 0)
                      
                        if message.lower() == "ping":
                            response = "pong"
                        else:
                            response = "Ошибка: неверный запрос"
                        
                        #записываем ответ в файл
                        os.lseek(fd, 0, os.SEEK_SET)
                        os.write(fd, response.encode('utf-8'))
                        print(f"Отправлен ответ: '{response}'")
                        
                        #сбрасываем буферы на диск
                        os.fsync(fd)                        
                        print("\n")
                        
                    os.lockf(fd, os.F_ULOCK, 0)
                    
                except Exception as e:
                    #в случае ошибки снимаем блокировку
                    try:
                        os.lockf(fd, os.F_ULOCK, 0)
                    except:
                        pass
                    raise

                os.close(fd)                
                    
            except KeyboardInterrupt:
                print("\nСервер завершает работу...")
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                continue
                
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return 1
    finally:
        try:
            os.unlink(shared_file)
            print(f"Файл {shared_file} удален")
        except:
            pass
    
    return 0

if __name__ == "__main__":
    sys.exit(server())

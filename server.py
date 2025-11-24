import os
import time
from config import PIPE_PATH, TIMEOUT, PING_MESSAGE, PONG_MESSAGE, BUFFER_SIZE, ENCODING

class Server:
    def __init__(self):
        self.pipe_path = PIPE_PATH
        self.setup_pipe()
    
    def setup_pipe(self):
        if not os.path.exists(self.pipe_path):
            os.mkfifo(self.pipe_path)
            print(f"создан pipe: {self.pipe_path}")
        else:
            print(f"pipe уже существует: {self.pipe_path}")

    
    def wait_for_request(self):
        
        print(f"сервер: ожидание запроса...")
        
        try:
            #открываем pipe на чтение (блокирующее) - программа "застынет" здесь, пока не придут данные
            with open(self.pipe_path, 'r') as pipe:
                message = pipe.read().strip()
                print(f"сервер: получено сообщение: '{message}'")
                
                if message == PING_MESSAGE:
                    return True, message
                else:
                    print(f"сервер: получено неверное сообщение")
                    return False, message
                    
        except Exception as e:
            print(f"сервер: ошибка при чтении запроса: {e}")
            return False, None
    
    def process_request(self, request):
        
        if request == PING_MESSAGE:  
            print("сервер: обрабатываю запрос...")
            #имитация обработки
            time.sleep(0.5)
            return PONG_MESSAGE
        else:
            print(f"сервер: не могу обработать запрос")
            return None
    
    def send_response(self, response):
        
        if response is None:
            print("сервер: нечего отправлять")
            return False
            
        print(f"сервер: отправляю ответ '{response}'...")
        
        try:
            #открываем pipe на запись
            with open(self.pipe_path, 'w') as pipe:
                pipe.write(response)
                pipe.flush() #принудительно записываем в pipe
            print("сервер: ответ успешно отправлен")
            return True
            
        except Exception as e:
            print(f"сервер: ошибка при отправке ответа")
            return False
    
    def run(self):
        
        #основной цикл сервера
        print("сервер запущен...")
        
        while True:
            try:
                #состояние 1
                success, request = self.wait_for_request()
                
                if not success:
                    print("сервер: пропускаем невалидный запрос")
                    continue
                
                #состояние 2
                response = self.process_request(request)
                
                #состояние 3
                send_success = self.send_response(response)
                
                if send_success:
                    print("сервер: цикл завершен успешно, переходим к следующему запросу\n")
                else:
                    print("сервер: ошибка отправки, переходим к обработке ошибок")
                    #здесь будет переход к состоянию 4
                    break
                    
            except KeyboardInterrupt:
                print("\nсервер: остановка по запросу пользователя")
                break
            except Exception as e:
                print(f"сервер: какая-то ошибка: {e}")
                break
        
        self.cleanup()
    
    def cleanup(self):
        #очистка ресурсов
        #иначе будет что-то типа "pipe уже существует"
        try:
            if os.path.exists(self.pipe_path):
                os.unlink(self.pipe_path) #удаление из файловой системы
                print(f"сервер: pipe удален: {self.pipe_path}")
        except Exception as e:
            print(f"сервер: ошибка при очистке: {e}")

def main():
    #точка входа для сервера
    server = Server()
    server.run()

if __name__ == "__main__":
    main()

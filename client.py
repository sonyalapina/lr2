import os

def client():
    PIPE_PATH = "/tmp/ping_pong_pipe"
    ENCODING = "utf-8"

    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
        print(f"клиент: создан pipe: {PIPE_PATH}")
    else: print(f"клиент: pipe уже существует: {PIPE_PATH}")
    
    print("клиент: для отправки сообщения введите 'ping' или любое другое слово")
    print("клиент: для выхода введите 'exit'")
    
    while True:
        user_input = input("\nклиент: введите сообщение: ").strip()
        
        if user_input.lower() == "exit":
            print("клиент: выход из программы")
            break
        
        print(f"клиент: отправляю '{user_input}'...")
        try:
            with open(PIPE_PATH, 'w') as pipe:
                pipe.write(user_input)
                pipe.flush()
            print("клиент: сообщение отправлено")
        except Exception as e:
            print(f"клиент: ошибка при отправке: {e}")
            continue
        
        print("клиент: ожидаю ответ...")
        try:
            with open(PIPE_PATH, 'r') as pipe:
                response = pipe.read().strip()
                print(f"клиент: получен ответ: '{response}'")
                
                if user_input.lower() == "ping" and response == "pong": print("клиент: корректный обмен сообщениями")
                elif response == "error": print("клиент: сервер вернул ошибку")
                else: print("клиент: неожиданный ответ")
                    
        except Exception as e:
            print(f"клиент: ошибка при чтении ответа: {e}")
            continue

if __name__ == "__main__":
    client()

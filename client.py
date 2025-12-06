import os
import sys

try:
    from ClientErrors import ClientErrors, with_client_error_handling
    error_handler = ClientErrors(max_retries=3, timeout_seconds=5, retry_delay=1.0)
    ERROR_HANDLER_ENABLED = False
    print("клиент: обработчик ошибок подключен")
except ImportError as e:
    print(f"клиент: не удалось импортировать обработчик ошибок: {e}")
    print("клиент: продолжение без обработчика ошибок")
    error_handler = None
    ERROR_HANDLER_ENABLED = False

from config import PIPE_PATH, ENCODING
@with_client_error_handling(error_handler=error_handler if ERROR_HANDLER_ENABLED else None, context="client_main")

def client():
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
        print(f"клиент: создан pipe: {PIPE_PATH}")
    else: 
        print(f"клиент: pipe уже существует: {PIPE_PATH}")
    
    print("клиент: для отправки сообщения введите 'ping' или любое другое слово")
    print("клиент: для выхода введите 'exit'")
    
    while True:
        user_input = input("\nклиент: введите сообщение: ").strip()
        
        if user_input.lower() == "exit":
            print("клиент: выход из программы")
            break
        
        if ERROR_HANDLER_ENABLED and error_handler:
            is_valid, validation_msg = error_handler.validate_input(user_input)
            if not is_valid:
                print(f"клиент: некорректный ввод: {validation_msg}")
                continue
            
            exists, error_msg = error_handler.check_pipe_exists(PIPE_PATH)
            if not exists:
                print(f"клиент: {error_msg}")
                if not error_handler.should_continue_after_error():
                    print("клиент: критическая ошибка, завершаю работу")
                    break
                continue

        print(f"клиент: отправляю '{user_input}'...")
        try:
            if ERROR_HANDLER_ENABLED and error_handler:
                success, error_msg = error_handler.handle_send_with_retry(PIPE_PATH, user_input)
                if not success:
                    print(f"клиент: ошибка при отправке: {error_msg}")
                    if not error_handler.should_continue_after_error():
                        print("клиент: слишком много ошибок, завершаю работу")
                        break
                    continue
            else:
                with open(PIPE_PATH, 'w') as pipe:
                    pipe.write(user_input)
                    pipe.flush()
            print("клиент: сообщение отправлено")

            import time #микро задержка перед чтением
            time.sleep(0.1)

        except Exception as e:
            print(f"клиент: ошибка при отправке: {e}")
            if ERROR_HANDLER_ENABLED and error_handler:
                error_handler._log_error(type(e).__name__, f"Ошибка отправки: {e}")
                if not error_handler.should_continue_after_error():
                    print("клиент: слишком много ошибок, завершаю работу")
                    break
            continue
        
        print("клиент: ожидаю ответ...")
        try:
            if ERROR_HANDLER_ENABLED and error_handler:
                success, response, error_msg = error_handler.handle_receive_with_timeout(PIPE_PATH)
                if not success:
                    print(f"клиент: ошибка при получении ответа: {error_msg}")
                    if not error_handler.should_continue_after_error():
                        print("клиент: слишком много ошибок, завершаю работу")
                        break
                    continue
            else:
                import time
                start_time = time.time()
                response = None
                while time.time() - start_time < 5:
                    try:
                        with open(PIPE_PATH, 'r') as pipe:
                            response = pipe.read().strip()
                            if response:
                                break
                    except (FileNotFoundError, OSError):
                        time.sleep(0.1)
                        continue
                
                if not response:
                    print("клиент: таймаут ожидания ответа")
                    continue
            if response == user_input:
                print(f"клиент: получено мое же сообщение обратно (сервер не ответил)")
    
    #Обработка как ошибка
                if ERROR_HANDLER_ENABLED and error_handler:
                    error_handler._log_error("ServerNotResponding", "Сервер не ответил, получено свое сообщение")
                    if not error_handler.should_continue_after_error():
                        print("клиент: слишком много ошибок, завершаю работу")
                        break
                continue 
            print(f"клиент: получен ответ: '{response}'")
        
            if ERROR_HANDLER_ENABLED and error_handler:
                is_valid_response, validation_msg = error_handler.validate_server_response(user_input, response)
                if not is_valid_response:
                    print(f"клиент: {validation_msg}")
                    if not error_handler.should_continue_after_error():
                        print("клиент: слишком много ошибок протокола, завершаю работу")
                        break
                    continue
                else:
                    print("клиент: корректный обмен сообщениями")
            else:
                if user_input.lower() == "ping" and response == "pong": 
                    print("клиент: корректный обмен сообщениями")
                elif response == "error": 
                    print("клиент: сервер вернул ошибку")
                else: 
                    print("клиент: неожиданный ответ")
                    
        except Exception as e:
            print(f"клиент: ошибка при чтении ответа: {e}")
            if ERROR_HANDLER_ENABLED and error_handler:
                error_handler._log_error(type(e).__name__, f"ошибка получения: {e}")
                if not error_handler.should_continue_after_error():
                    print("клиент: слишком много ошибок, завершаю работу")
                    break
            continue

if __name__ == "__main__":
    client()
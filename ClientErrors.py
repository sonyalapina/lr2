import time
import sys
import os
from typing import Tuple, Optional

class ClientErrors:
    def __init__(self, max_retries: int = 3, timeout_seconds: int = 5, retry_delay: float = 1.0):
        """
        max_retries - максимальное количество повторных попыток
        timeout_seconds - интервал ожидания ответа в секундах
        retry_delay - задержка между повторными попытками в секундах
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.retry_delay = retry_delay
        self.total_errors = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
    def handle_send_with_retry(self, pipe_path: str, message: str, pipe_mode: str = 'w') -> Tuple[bool, Optional[str]]:
        """
        pipe_path - путь к именованному каналу
        message - сообщение для отправки
        pipe_mode - режим открытия файла
        Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
        """
        for attempt in range(self.max_retries):
            try:
                #пытаемся открыть и записать в pipe с интервалом
                start_time = time.time()
                
                with open(pipe_path, pipe_mode) as pipe:
                    if time.time() - start_time > self.timeout_seconds:
                        return False, f"интервал при открытии pipe для записи (попытка {attempt + 1})"
                    
                    pipe.write(message)
                    pipe.flush()  #принудительная запись
                    
                self.consecutive_errors = 0
                return True, None
                
            except FileNotFoundError as e:
                error_msg = f"pipe не найден: {pipe_path} (попытка {attempt + 1})"
                self._log_error("FileNotFoundError", error_msg)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False, error_msg
                
            except PermissionError as e:
                error_msg = f"нет прав доступа к pipe (попытка {attempt + 1})"
                self._log_error("PermissionError", error_msg)
                return False, error_msg
                
            except OSError as e:
                error_msg = f"ошибка OS при записи в pipe: {e} (попытка {attempt + 1})"
                self._log_error("OSError", error_msg)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False, error_msg
                
            except Exception as e:
                error_msg = f"неожиданная ошибка при отправке: {e} (попытка {attempt + 1})"
                self._log_error(type(e).__name__, error_msg)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False, error_msg
        
        return False, f"превышено максимальное количество попыток ({self.max_retries})"
    
    def handle_receive_with_timeout(self, pipe_path: str, pipe_mode: str = 'r') -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            start_time = time.time()
            end_time = start_time + self.timeout_seconds
            
            while time.time() < end_time:
                try:
                    with open(pipe_path, pipe_mode) as pipe:
                        read_start = time.time()
                        response = pipe.read().strip()
                        
                        if time.time() - read_start > self.timeout_seconds:
                            return False, None, f"интервал при чтении из pipe"
                        
                        if response:
                            self.consecutive_errors = 0
                            return True, response, None
                        
                except FileNotFoundError:
                    #рipe может временно отсутствовать, продолжаем попытки
                    pass
                except OSError as e:
                    #другие ошибки ОС логируем, но продолжаем
                    self._log_error("OSError", f"ошибка при чтении: {e}")
                
                time.sleep(0.1)
            
            #если вышли из цикла - интервал
            return False, None, f"интервал ожидания ответа ({self.timeout_seconds} секунд)"
            
        except Exception as e:
            error_msg = f"неожиданная ошибка при получении ответа: {e}"
            self._log_error(type(e).__name__, error_msg)
            return False, None, error_msg
    
    def validate_input(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        user_input - введенная строка
        Tuple[bool, Optional[str]]: (валидность, сообщение об ошибке)
        """
        if not user_input or not user_input.strip():
            return False, "пустой ввод"
        
        #проверяем, не содержит ли ввод "опасных" символов
        dangerous_chars = ['\0', '\n', '\r', ';', '|', '&', '$', '`']
        for char in dangerous_chars:
            if char in user_input:
                return False, f"ввод содержит недопустимый символ: {repr(char)}"
        
        #проверяем длину
        if len(user_input) > 100:
            return False, "сообщение слишком длинное (макс. 100 символов)"
        
        return True, None
    
    def validate_server_response(self, user_input: str, server_response: str) -> Tuple[bool, Optional[str]]:
        """
        user_input - сообщение, отправленное клиентом
        server_response - ответ от сервера
        Tuple[bool, Optional[str]]: (валидность, сообщение об ошибке)
        """
        if not server_response or not server_response.strip():
            return False, "пустой ответ от сервера"
        
        #если клиент отправил "ping", сервер должен ответить "pong"
        if user_input.lower() == "ping":
            if server_response != "pong":
                error_msg = f"недопустимый ответ от сервера: ожидалось 'pong', получено '{server_response}'"
                self._log_error("ProtocolError", error_msg)
                return False, error_msg
            return True, None
        
        #если клиент отправил что-то кроме "ping", сервер должен ответить "error"
        if server_response != "error":
            error_msg = f"недопустимый ответ от сервера: ожидалось 'error', получено '{server_response}'"
            self._log_error("ProtocolError", error_msg)
            return False, error_msg
        
        return True, None
    
    def check_pipe_exists(self, pipe_path: str) -> Tuple[bool, Optional[str]]:
        """
        Tuple[bool, Optional[str]]: (существует, сообщение об ошибке)
        """
        try:
            if not os.path.exists(pipe_path):
                return False, f"рipe не существует: {pipe_path}"
            
            #проверяем, является ли это именованным каналом
            if not os.path.exists(pipe_path) or not os.path.isfile(pipe_path):
                try:
                    with open(pipe_path, 'r'):
                        pass
                    return True, None
                except:
                    return False, f"файл существует, но не является pipe: {pipe_path}"
            
            return True, None
            
        except Exception as e:
            return False, f"ошибка при проверке pipe: {e}"
    
    def should_continue_after_error(self) -> bool:
        """
       bool: True если можно продолжать, False если нужно остановиться
        """
        self.consecutive_errors += 1
        self.total_errors += 1
        
        if self.consecutive_errors >= self.max_consecutive_errors:
            print(f"превышено максимальное количество последовательных ошибок: {self.consecutive_errors}")
            print("   рекомендуется проверить состояние сервера и pipe")
            return False
        
        if self.total_errors > 20:
            print(f"превышено общее количество ошибок: {self.total_errors}")
            print("   возможно, есть системные проблемы")
            return False
        
        return True
    
    def _log_error(self, error_type: str, message: str):
        """
        error_type - тип ошибки
        message - сообщение об ошибке
        """
        self.consecutive_errors += 1
        self.total_errors += 1
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [CLIENT ERROR] [{error_type}] {message}"
        
        #вывод в stderr
        print(log_message, file=sys.stderr)
        
        #дополнительно можно записывать в файл
        self._write_to_error_log(log_message)
    
    def _write_to_error_log(self, message: str):
        """
        message - сообщение для записи
        """
        try:
            log_dir = "/tmp/ping_pong_logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, "client_errors.log")
            with open(log_file, 'a') as f:
                f.write(message + "\n")
        except Exception:
            pass
    
    def reset_error_counters(self):
        self.consecutive_errors = 0

#декоратор для обработки ошибок клиента
def with_client_error_handling(error_handler: ClientErrors, context: str = ""):
    """
    error_handler - экземпляр ClientErrors
    context - контекст операции
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                error_handler.reset_error_counters()
                return result
            except KeyboardInterrupt:
                print("\nпрерывание пользователем")
                raise
            except Exception as e:
                error_msg = f"ошибка в {context or func.__name__}: {type(e).__name__}: {str(e)}"
                error_handler._log_error(type(e).__name__, error_msg)
                
                if error_handler.should_continue_after_error():
                    print(f"продолжаем работу после ошибки")
                    return None
                else:
                    print(f"слишком много ошибок, останавливаем клиента")
                    raise
        return wrapper
    return decorator
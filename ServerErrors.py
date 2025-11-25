import errno
import os
import time
from typing import Tuple
import logging

class ServerErrors(Exception):
    pass

class PipeError(ServerErrors):
    pass

class ProtocolError(ServerErrors):
    pass

class ErrorHandler:
    def __init__(self):
        self.consecutive_errors=0
        self.max_consecutive_errors=5

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",)
        self.logger=logging.getLogger("ServerErrorHandler")

    def handle_error(self,error: Exception, context:str="")->Tuple[bool,str]:
        error_code=getattr(error,"errno", None)
        self.logger.error(f"[{context}] {type(error).__name__}: {str(error)}")
        self.consecutive_errors+=1

        if self.consecutive_errors>=self.max_consecutive_errors:
            return False, "Слишком много ошибок подряд, требуется перезапуск"
        if isinstance(error,BrokenPipeError):
            self.consecutive_errors=0
            return True, "BrokenPipeError: восстановление соединения"
        if isinstance(error, FileNotFoundError):
            self.consecutive_errors=0
            return True, "FileNotFoundError: файл будет создан"

        recoverable_errors=[
            errno.EEXIST,
            errno.EPIPE,
            errno.ENXIO,
            errno.EAGAIN,
            errno.EINTR,
        ]

        if error_code in recoverable_errors:
            self.consecutive_errors=0
            return True, f"Восстанавливаемая ошибка: {error_code}"

        fatal_errors=[
            errno.EACCES,
            errno.ENOSPC,
            errno.EROFS,
            errno.ENOMEM,
        ]
        if error_code in fatal_errors:
            return False, self._get_fatal_message(error_code,context)
        if isinstance(error,ProtocolError):
            self.consecutive_errors=0
            return True, "Некорректное сообщение, отправленное клиентом, ждем дальше"
        return True, f"Ошибка {type(error).__name__}, работа продолжается :) "

    def _get_fatal_message(self,error_code:int, context:str)->str:
        message={
            errno.EACCES: "Критическая ошибка: нет прав доступа",
            errno.ENOSPC: "Критическая ошибка: нет места на диске",
            errno.EROFS: "Критическая ошибка: файловая система только для чтения",
            errno.ENOMEM: "Критическая ошибка: недостаточно памяти",
        }
        return message.get(error_code,"Ошибка критическая, нужна перезагрузка")

    def reset_consecutive_errors(self):
        self.consecutive_errors=0

    def validate_ping_message(self,received_message:str, expected_ping: str)->bool:
        if received_message!=expected_ping:
            raise ProtocolError(f"Ожидалось '{expected_ping}', получено '{received_message}'")
        return True

def with_error_handling(error_handler: ErrorHandler,context:str=""):
    def decorator(func):
        def wrapper(*args,**kwargs):
            try:
                result=func(*args, **kwargs)
                error_handler.reset_consecutive_errors()
                return result
            except Exception as e:
                can_continue, message= error_handler.handle_error(e,context or func.__name__)
                if not can_continue:
                    raise ServerErrors(message) from e
                return None
        return wrapper
    return decorator

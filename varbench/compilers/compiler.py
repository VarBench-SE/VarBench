from abc import ABC, abstractmethod
import os

import PIL.Image


class Compiler(ABC):
    def __init__(self):
        self.cache_path = os.path.join(os.environ.get("HOME"), ".cache/varbench")
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)

    @abstractmethod
    def compile(self, input, output):
        pass

    @abstractmethod
    def compile_from_string(self, input_string) -> PIL.Image:
        pass


class CompilerException(Exception):
    def __init__(self, message:str, *args: object) -> None:
        self.message = message
        super().__init__(*args)
    def __str__(self) -> str:
        return f"[CompilerExceptionself:{self.message}]"

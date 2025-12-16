"""
Noxy Interpreter - Módulo de Erros
Define todas as exceções usadas pelo interpretador.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceLocation:
    """Localização no código fonte."""
    line: int
    column: int
    file: str = "<stdin>"
    
    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


class NoxyError(Exception):
    """Classe base para todos os erros do Noxy."""
    
    def __init__(self, message: str, location: Optional[SourceLocation] = None):
        self.message = message
        self.location = location
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        if self.location:
            return f"[{self.location}] {self.message}"
        return self.message


class NoxyLexerError(NoxyError):
    """Erro durante a tokenização."""
    pass


class NoxyParserError(NoxyError):
    """Erro durante o parsing."""
    pass


class NoxyTypeError(NoxyError):
    """Erro de tipo estático."""
    
    def __init__(self, message: str, location: Optional[SourceLocation] = None,
                 expected_type: Optional[str] = None, actual_type: Optional[str] = None):
        self.expected_type = expected_type
        self.actual_type = actual_type
        super().__init__(message, location)


class NoxyRuntimeError(NoxyError):
    """Erro durante a execução."""
    pass


class NoxyNameError(NoxyRuntimeError):
    """Erro de nome não encontrado."""
    pass


class NoxyIndexError(NoxyRuntimeError):
    """Erro de índice fora dos limites."""
    pass


class NoxyDivisionError(NoxyRuntimeError):
    """Erro de divisão por zero."""
    pass


class NoxyBreakException(Exception):
    """Exceção usada para implementar break em loops."""
    pass


class NoxyReturnException(Exception):
    """Exceção usada para implementar return em funções."""
    
    def __init__(self, value):
        self.value = value
        super().__init__()





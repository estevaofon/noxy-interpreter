"""
Noxy Interpreter - Lexer
Tokenização do código fonte Noxy.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
from errors import NoxyLexerError, SourceLocation


class TokenType(Enum):
    """Tipos de tokens do Noxy."""
    # Literais
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BYTES = auto()
    FSTRING = auto()
    
    # Identificador
    IDENTIFIER = auto()
    
    # Palavras-chave - Declarações
    LET = auto()
    GLOBAL = auto()
    FUNC = auto()
    STRUCT = auto()
    
    # Palavras-chave - Controle de fluxo
    IF = auto()
    THEN = auto()
    ELSE = auto()
    END = auto()
    WHILE = auto()
    DO = auto()
    RETURN = auto()
    BREAK = auto()
    
    # Palavras-chave - Tipos
    TYPE_INT = auto()
    TYPE_FLOAT = auto()
    TYPE_STRING = auto()
    TYPE_STR = auto()
    TYPE_BOOL = auto()
    TYPE_BYTES = auto()
    TYPE_VOID = auto()
    REF = auto()
    
    # Palavras-chave - Literais
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    
    # Palavras-chave - Módulos
    USE = auto()
    SELECT = auto()
    
    # Palavras-chave - Especiais
    ZEROS = auto()
    
    # Operadores aritméticos
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %
    
    # Operadores de comparação
    GT = auto()         # >
    LT = auto()         # <
    GTE = auto()        # >=
    LTE = auto()        # <=
    EQ = auto()         # ==
    NEQ = auto()        # !=
    
    # Operadores lógicos
    AND = auto()        # &
    OR = auto()         # |
    NOT = auto()        # !
    
    # Atribuição
    ASSIGN = auto()     # =
    
    # Retorno de função
    ARROW = auto()      # ->
    
    # Delimitadores
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    COMMA = auto()      # ,
    COLON = auto()      # :
    DOT = auto()        # .
    
    # Especiais
    NEWLINE = auto()
    EOF = auto()


# Mapa de palavras-chave
KEYWORDS = {
    # Declarações
    "let": TokenType.LET,
    "global": TokenType.GLOBAL,
    "func": TokenType.FUNC,
    "struct": TokenType.STRUCT,
    
    # Controle de fluxo
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
    "end": TokenType.END,
    "while": TokenType.WHILE,
    "do": TokenType.DO,
    "return": TokenType.RETURN,
    "break": TokenType.BREAK,
    
    # Tipos
    "int": TokenType.TYPE_INT,
    "float": TokenType.TYPE_FLOAT,
    "string": TokenType.TYPE_STRING,
    "str": TokenType.TYPE_STR,
    "bool": TokenType.TYPE_BOOL,
    "bytes": TokenType.TYPE_BYTES,
    "void": TokenType.TYPE_VOID,
    "ref": TokenType.REF,
    
    # Literais
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    
    # Módulos
    "use": TokenType.USE,
    "select": TokenType.SELECT,
    
    # Especiais
    "zeros": TokenType.ZEROS,
}


@dataclass
class Token:
    """Token do lexer."""
    type: TokenType
    value: any
    location: SourceLocation
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.location})"


class Lexer:
    """Tokenizador do Noxy."""
    
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
    
    @property
    def current_char(self) -> Optional[str]:
        """Retorna o caractere atual ou None se acabou."""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def peek(self, offset: int = 1) -> Optional[str]:
        """Olha um caractere à frente."""
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self) -> str:
        """Avança para o próximo caractere."""
        char = self.current_char
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def location(self) -> SourceLocation:
        """Retorna a localização atual."""
        return SourceLocation(self.line, self.column, self.filename)
    
    def error(self, message: str) -> NoxyLexerError:
        """Cria um erro de lexer."""
        return NoxyLexerError(message, self.location())
    
    def skip_whitespace(self):
        """Pula espaços em branco (exceto newline)."""
        while self.current_char and self.current_char in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """Pula comentário de linha."""
        while self.current_char and self.current_char != '\n':
            self.advance()
    
    def read_number(self) -> Token:
        """Lê um número inteiro ou float."""
        loc = self.location()
        number = ""
        
        # Parte inteira
        while self.current_char and self.current_char.isdigit():
            number += self.advance()
        
        # Parte decimal (float)
        if self.current_char == '.' and self.peek() and self.peek().isdigit():
            number += self.advance()  # .
            while self.current_char and self.current_char.isdigit():
                number += self.advance()
            return Token(TokenType.FLOAT, float(number), loc)
        
        return Token(TokenType.INT, int(number), loc)
    
    def read_bytes(self) -> Token:
        """Lê um literal de bytes (b'...' ou b"...")."""
        loc = self.location()
        self.advance()  # Pula o 'b'
        quote = self.current_char
        self.advance()  # Pula a aspa
        
        value = bytearray()
        while self.current_char and self.current_char != quote:
            if self.current_char == '\\':
                self.advance()
                escape = self.current_char
                if escape == 'n':
                    value.extend(b'\n')
                elif escape == 't':
                    value.extend(b'\t')
                elif escape == 'r':
                    value.extend(b'\r')
                elif escape == '"':
                    value.extend(b'"')
                elif escape == "'":
                    value.extend(b"'")
                elif escape == '\\':
                    value.extend(b'\\')
                elif escape == 'x':
                    # Hex: \x00
                    self.advance()
                    hex_val = ""
                    if self.current_char:
                        hex_val += self.current_char
                        self.advance()
                    if self.current_char:
                        hex_val += self.current_char
                        self.advance()
                        # Voltar um pois o loops vai avançar depois?
                        # Não, a logica do loop principal é diferente.
                        # Vamos ajustar.
                        self.pos -= 1 # Volta um pq o next loop vai pegar
                    
                    try:
                        value.append(int(hex_val, 16))
                    except ValueError:
                        raise self.error(f"Sequência de escape bytes inválida: \\x{hex_val}")
                    continue # Já avançamos
                else:
                    # Escape desconhecido, mantém literal?
                    # Em python b'\\' é um backslash apenas se for duplo.
                    # Simplificação: trata como char raw
                    value.append(ord(escape))

                if self.current_char:
                    self.advance()
            elif self.current_char == '\n':
                raise self.error("Literal bytes não fechado")
            else:
                value.append(ord(self.current_char))
                self.advance()
        
        if not self.current_char:
            raise self.error("Literal bytes não fechado")
        
        self.advance()  # Pula a aspa de fechamento
        return Token(TokenType.BYTES, bytes(value), loc)
    
    def read_string(self) -> Token:
        """Lê uma string literal."""
        loc = self.location()
        self.advance()  # Pula o "
        
        value = ""
        while self.current_char and self.current_char != '"':
            if self.current_char == '\\':
                self.advance()
                escape = self.current_char
                if escape == 'n':
                    value += '\n'
                elif escape == 't':
                    value += '\t'
                elif escape == 'r':
                    value += '\r'
                elif escape == '"':
                    value += '"'
                elif escape == '\\':
                    value += '\\'
                else:
                    value += escape or ''
                if self.current_char:
                    self.advance()
            elif self.current_char == '\n':
                raise self.error("String não fechada")
            else:
                value += self.advance()
        
        if not self.current_char:
            raise self.error("String não fechada")
        
        self.advance()  # Pula o "
        return Token(TokenType.STRING, value, loc)
    
    def read_fstring(self) -> Token:
        """Lê uma f-string."""
        loc = self.location()
        self.advance()  # Pula o f
        self.advance()  # Pula o "
        
        # Para f-strings, guardamos o conteúdo bruto para processar no parser
        parts = []
        current_text = ""
        
        while self.current_char and self.current_char != '"':
            if self.current_char == '\\':
                self.advance()
                escape = self.current_char
                if escape == 'n':
                    current_text += '\n'
                elif escape == 't':
                    current_text += '\t'
                elif escape == 'r':
                    current_text += '\r'
                elif escape == '"':
                    current_text += '"'
                elif escape == '\\':
                    current_text += '\\'
                elif escape == '{':
                    current_text += '{'
                elif escape == '}':
                    current_text += '}'
                else:
                    current_text += escape or ''
                if self.current_char:
                    self.advance()
            elif self.current_char == '{':
                # Início de interpolação
                if current_text:
                    parts.append(("text", current_text))
                    current_text = ""
                self.advance()  # Pula o {
                
                # Lê a expressão e formato
                expr = ""
                brace_count = 1
                while self.current_char and brace_count > 0:
                    if self.current_char == '{':
                        brace_count += 1
                    elif self.current_char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            break
                    expr += self.advance()
                
                if not self.current_char:
                    raise self.error("F-string interpolação não fechada")
                
                self.advance()  # Pula o }
                
                # Separa expressão do format spec
                if ':' in expr:
                    expr_part, format_spec = expr.split(':', 1)
                    parts.append(("expr", expr_part.strip(), format_spec))
                else:
                    parts.append(("expr", expr.strip(), None))
            elif self.current_char == '\n':
                raise self.error("F-string não fechada")
            else:
                current_text += self.advance()
        
        if current_text:
            parts.append(("text", current_text))
        
        if not self.current_char:
            raise self.error("F-string não fechada")
        
        self.advance()  # Pula o "
        return Token(TokenType.FSTRING, parts, loc)
    
    def read_identifier(self) -> Token:
        """Lê um identificador ou palavra-chave."""
        loc = self.location()
        ident = ""
        
        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            ident += self.advance()
        
        # Verifica se é f-string
        if ident == 'f' and self.current_char == '"':
            self.pos -= 1
            self.column -= 1
            return self.read_fstring()
        
        # Verifica se é palavra-chave
        token_type = KEYWORDS.get(ident, TokenType.IDENTIFIER)
        return Token(token_type, ident, loc)
    
    def tokenize(self) -> list[Token]:
        """Tokeniza todo o código fonte."""
        while self.current_char:
            # Pula espaços
            if self.current_char in ' \t\r':
                self.skip_whitespace()
                continue
            
            # Newline
            if self.current_char == '\n':
                loc = self.location()
                self.advance()
                self.tokens.append(Token(TokenType.NEWLINE, '\n', loc))
                continue
            
            # Comentário
            if self.current_char == '/' and self.peek() == '/':
                self.skip_comment()
                continue
            
            # Número
            if self.current_char.isdigit():
                self.tokens.append(self.read_number())
                continue
            
            # String
            if self.current_char == '"':
                self.tokens.append(self.read_string())
                continue

            # Bytes literal
            if self.current_char == 'b' and (self.peek() == '"' or self.peek() == "'"):
                self.tokens.append(self.read_bytes())
                continue
            
            # Identificador ou palavra-chave
            if self.current_char.isalpha() or self.current_char == '_':
                self.tokens.append(self.read_identifier())
                continue
            
            # Operadores e delimitadores
            loc = self.location()
            char = self.current_char
            
            # Operadores de dois caracteres
            if char == '-' and self.peek() == '>':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.ARROW, '->', loc))
            elif char == '>' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.GTE, '>=', loc))
            elif char == '<' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.LTE, '<=', loc))
            elif char == '=' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.EQ, '==', loc))
            elif char == '!' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.NEQ, '!=', loc))
            # Operadores de um caractere
            elif char == '+':
                self.advance()
                self.tokens.append(Token(TokenType.PLUS, '+', loc))
            elif char == '-':
                self.advance()
                self.tokens.append(Token(TokenType.MINUS, '-', loc))
            elif char == '*':
                self.advance()
                self.tokens.append(Token(TokenType.STAR, '*', loc))
            elif char == '/':
                self.advance()
                self.tokens.append(Token(TokenType.SLASH, '/', loc))
            elif char == '%':
                self.advance()
                self.tokens.append(Token(TokenType.PERCENT, '%', loc))
            elif char == '>':
                self.advance()
                self.tokens.append(Token(TokenType.GT, '>', loc))
            elif char == '<':
                self.advance()
                self.tokens.append(Token(TokenType.LT, '<', loc))
            elif char == '=':
                self.advance()
                self.tokens.append(Token(TokenType.ASSIGN, '=', loc))
            elif char == '&':
                self.advance()
                self.tokens.append(Token(TokenType.AND, '&', loc))
            elif char == '|':
                self.advance()
                self.tokens.append(Token(TokenType.OR, '|', loc))
            elif char == '!':
                self.advance()
                self.tokens.append(Token(TokenType.NOT, '!', loc))
            elif char == '(':
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, '(', loc))
            elif char == ')':
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ')', loc))
            elif char == '[':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACKET, '[', loc))
            elif char == ']':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACKET, ']', loc))
            elif char == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, '{', loc))
            elif char == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, '}', loc))
            elif char == ',':
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ',', loc))
            elif char == ':':
                self.advance()
                self.tokens.append(Token(TokenType.COLON, ':', loc))
            elif char == '.':
                self.advance()
                self.tokens.append(Token(TokenType.DOT, '.', loc))
            else:
                raise self.error(f"Caractere inesperado: '{char}'")
        
        # EOF
        self.tokens.append(Token(TokenType.EOF, None, self.location()))
        return self.tokens


def tokenize(source: str, filename: str = "<stdin>") -> list[Token]:
    """Função auxiliar para tokenizar código."""
    lexer = Lexer(source, filename)
    return lexer.tokenize()





"""
Noxy Interpreter - Nós da AST
Define todas as dataclasses que representam nós da Abstract Syntax Tree.
"""

from dataclasses import dataclass, field
from typing import Optional, Union
from errors import SourceLocation


# ============================================================================
# TIPOS
# ============================================================================

@dataclass
class NoxyType:
    """Classe base para todos os tipos Noxy."""
    pass


@dataclass
class PrimitiveType(NoxyType):
    """Tipo primitivo: int, float, string, bool, void."""
    name: str  # "int", "float", "string", "bool", "void"
    
    def __eq__(self, other):
        if isinstance(other, PrimitiveType):
            # "str" é alias para "string"
            name1 = "string" if self.name == "str" else self.name
            name2 = "string" if other.name == "str" else other.name
            return name1 == name2
        return False
    
    def __hash__(self):
        name = "string" if self.name == "str" else self.name
        return hash(("primitive", name))
    
    def __str__(self):
        return self.name


@dataclass
class ArrayType(NoxyType):
    """Tipo array: int[5], string[], etc."""
    element_type: NoxyType
    size: Optional[int] = None  # None para arrays sem tamanho fixo (parâmetros)
    
    def __eq__(self, other):
        if isinstance(other, ArrayType):
            return self.element_type == other.element_type
        return False
    
    def __hash__(self):
        return hash(("array", self.element_type))
    
    def __str__(self):
        if self.size is not None:
            return f"{self.element_type}[{self.size}]"
        return f"{self.element_type}[]"


@dataclass
class StructType(NoxyType):
    """Tipo struct definido pelo usuário."""
    name: str
    
    def __eq__(self, other):
        if isinstance(other, StructType):
            return self.name == other.name
        return False
    
    def __hash__(self):
        return hash(("struct", self.name))
    
    def __str__(self):
        return self.name


@dataclass
class RefType(NoxyType):
    """Tipo referência: ref Node, ref Pessoa, etc."""
    inner_type: NoxyType
    
    def __eq__(self, other):
        if isinstance(other, RefType):
            return self.inner_type == other.inner_type
        return False
    
    def __hash__(self):
        return hash(("ref", self.inner_type))
    
    def __str__(self):
        return f"ref {self.inner_type}"


# ============================================================================
# EXPRESSÕES
# ============================================================================

@dataclass
class Expr:
    """Classe base para todas as expressões."""
    pass


@dataclass
class IntLiteral(Expr):
    """Literal inteiro: 42, -10, 0."""
    value: int
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class FloatLiteral(Expr):
    """Literal float: 3.14, -0.5."""
    value: float
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class StringLiteral(Expr):
    """Literal string: "Hello"."""
    value: str
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class BoolLiteral(Expr):
    """Literal booleano: true, false."""
    value: bool
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class NullLiteral(Expr):
    """Literal null."""
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class Identifier(Expr):
    """Identificador/variável: x, nome, contador."""
    name: str
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class BinaryOp(Expr):
    """Operação binária: a + b, x > y, etc."""
    left: Expr
    operator: str  # "+", "-", "*", "/", "%", ">", "<", ">=", "<=", "==", "!=", "&", "|"
    right: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class UnaryOp(Expr):
    """Operação unária: -x, !ativo."""
    operator: str  # "-", "!"
    operand: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class CallExpr(Expr):
    """Chamada de função ou construtor: func(a, b), Pessoa("Ana", 25)."""
    callee: Expr
    arguments: list[Expr]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class IndexExpr(Expr):
    """Acesso por índice: arr[0], str[i]."""
    object: Expr
    index: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class FieldAccess(Expr):
    """Acesso a campo de struct: pessoa.nome."""
    object: Expr
    field_name: str
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class ArrayLiteral(Expr):
    """Literal de array: [1, 2, 3]."""
    elements: list[Expr]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class RefExpr(Expr):
    """Expressão ref: ref node."""
    value: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class FStringExpr:
    """Parte interpolada de uma f-string: {expr:format}."""
    expr: Expr
    format_spec: Optional[str] = None


@dataclass
class FString(Expr):
    """F-string formatada: f"Hello {name}!"."""
    parts: list[Union[str, FStringExpr]]  # Alternância de strings e expressões
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class ZerosExpr(Expr):
    """Expressão zeros: zeros(100)."""
    size: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class GroupExpr(Expr):
    """Expressão entre parênteses: (a + b)."""
    expr: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


# ============================================================================
# STATEMENTS
# ============================================================================

@dataclass
class Stmt:
    """Classe base para todos os statements."""
    pass


@dataclass
class LetStmt(Stmt):
    """Declaração let: let x: int = 42."""
    name: str
    var_type: NoxyType
    initializer: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class GlobalStmt(Stmt):
    """Declaração global: global contador: int = 0."""
    name: str
    var_type: NoxyType
    initializer: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class AssignStmt(Stmt):
    """Atribuição: x = 10, arr[0] = 5, pessoa.nome = "Ana"."""
    target: Expr  # Identifier, IndexExpr, ou FieldAccess
    value: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class ExprStmt(Stmt):
    """Statement de expressão (chamadas de função, etc)."""
    expr: Expr
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class IfStmt(Stmt):
    """Condicional if-then-else."""
    condition: Expr
    then_body: list[Stmt]
    else_body: list[Stmt]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class WhileStmt(Stmt):
    """Loop while."""
    condition: Expr
    body: list[Stmt]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class ReturnStmt(Stmt):
    """Return statement."""
    value: Optional[Expr]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class BreakStmt(Stmt):
    """Break statement."""
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class FuncParam:
    """Parâmetro de função."""
    name: str
    param_type: NoxyType


@dataclass
class FuncDef(Stmt):
    """Definição de função."""
    name: str
    params: list[FuncParam]
    return_type: NoxyType
    body: list[Stmt]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class StructField:
    """Campo de struct."""
    name: str
    field_type: NoxyType


@dataclass
class StructDef(Stmt):
    """Definição de struct."""
    name: str
    fields: list[StructField]
    location: Optional[SourceLocation] = field(default=None, compare=False)


@dataclass
class UseStmt(Stmt):
    """Import de módulo: use module select func1, func2."""
    module_path: list[str]  # ["utils", "math"]
    imports: list[str]  # ["add", "multiply"] ou ["*"]
    location: Optional[SourceLocation] = field(default=None, compare=False)


# ============================================================================
# PROGRAMA
# ============================================================================

@dataclass
class Program:
    """Programa Noxy completo."""
    statements: list[Stmt]

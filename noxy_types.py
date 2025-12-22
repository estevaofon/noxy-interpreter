"""
Noxy Interpreter - Sistema de Tipos
Verificação de tipos estática e utilitários de tipos.
"""


from typing import Any
from ast_nodes import (

    NoxyType, PrimitiveType, ArrayType, StructType, RefType,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BytesLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, CallExpr, IndexExpr, FieldAccess,
    ArrayLiteral, RefExpr, FString, ZerosExpr, GroupExpr, FStringExpr,
    Stmt, LetStmt, GlobalStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt,
    ReturnStmt, BreakStmt, FuncDef, StructDef, UseStmt, Program
)
from noxy_signatures import BUILTIN_SIGNATURES
from errors import NoxyTypeError, SourceLocation, NoxyError

from pathlib import Path


def type_to_str(t: NoxyType) -> str:
    """Converte um tipo para string legível."""
    return str(t)


def types_equal(t1: NoxyType, t2: NoxyType) -> bool:
    """Verifica se dois tipos são iguais."""
    return t1 == t2


def is_numeric(t: NoxyType) -> bool:
    """Verifica se é tipo numérico (int ou float)."""
    return isinstance(t, PrimitiveType) and t.name in ("int", "float")


def is_primitive(t: NoxyType) -> bool:
    """Verifica se é tipo primitivo."""
    return isinstance(t, PrimitiveType)


def is_ref_type(t: NoxyType) -> bool:
    """Verifica se é tipo referência."""
    return isinstance(t, RefType)


def is_array_type(t: NoxyType) -> bool:
    """Verifica se é tipo array."""
    return isinstance(t, ArrayType)


def is_struct_type(t: NoxyType) -> bool:
    """Verifica se é tipo struct."""
    return isinstance(t, StructType)


class TypeChecker:
    """Verificador de tipos estático."""
    
    def __init__(self, base_path: str = None):
        # Tabela de tipos de variáveis
        self.variables: dict[str, NoxyType] = {}
        # Pilha de escopos
        self.scopes: list[dict[str, NoxyType]] = [{}]
        # Definições de funções
        self.functions: dict[str, FuncDef] = {}
        # Definições de structs
        self.structs: dict[str, StructDef] = {}
        # Tipo de retorno da função atual (para verificar return)
        self.current_function_return_type: NoxyType | None = None
        
        self.base_path = Path(str(base_path)) if base_path else Path(".")
        self.stdlib_path = Path(__file__).parent / "stdlib"
        self.loaded_modules: set[str] = set()
    
    def push_scope(self):
        """Entra em novo escopo."""
        self.scopes.append({})
    
    def pop_scope(self):
        """Sai do escopo atual."""
        self.scopes.pop()
    
    def define_var(self, name: str, var_type: NoxyType):
        """Define variável no escopo atual."""
        self.scopes[-1][name] = var_type
    
    def lookup_var(self, name: str) -> NoxyType | None:
        """Busca tipo de variável nos escopos."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
    
    def check_program(self, program: Program):
        """Verifica tipos de todo o programa."""
        
        # Primeira passada: coleta definições de struct e função (e processa imports)
        for stmt in program.statements:
            if isinstance(stmt, StructDef):
                self.structs[stmt.name] = stmt
            elif isinstance(stmt, FuncDef):
                self.functions[stmt.name] = stmt
            elif isinstance(stmt, UseStmt):
                self.check_use(stmt)
        
        # Segunda passada: verifica tipos
        for stmt in program.statements:
            self.check_statement(stmt)
    
    def check_statement(self, stmt: Stmt):
        """Verifica tipos de um statement."""
        if isinstance(stmt, LetStmt):
            self.check_let(stmt)
        elif isinstance(stmt, GlobalStmt):
            self.check_global(stmt)
        elif isinstance(stmt, AssignStmt):
            self.check_assignment(stmt)
        elif isinstance(stmt, ExprStmt):
            self.check_expression(stmt.expr)
        elif isinstance(stmt, IfStmt):
            self.check_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.check_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.check_return(stmt)
        elif isinstance(stmt, FuncDef):
            self.check_func_def(stmt)
        elif isinstance(stmt, StructDef):
            pass  # Já processado na primeira passada
        elif isinstance(stmt, BreakStmt):
            pass  # OK
        elif isinstance(stmt, UseStmt):
            pass  # Já processado na primeira passada

    def check_use(self, stmt: UseStmt):
        """Processa import de módulo durante a checagem de tipos."""
        # Constrói o caminho do módulo
        module_path = "/".join(stmt.module_path) + ".nx"
        full_path = self.base_path / module_path
        
        # Verifica se o arquivo existe
        if not full_path.exists():
            # Tenta na stdlib (relativo ao interpretador/type checker)
            candidate = self.stdlib_path / module_path
            if candidate.exists():
                full_path = candidate
            else:
                raise NoxyTypeError(
                    f"Módulo não encontrado: {module_path}",
                    stmt.location
                )
            
        # Evita ciclos e processamento duplicado
        module_key = str(full_path.resolve())
        if module_key in self.loaded_modules:
            return
        self.loaded_modules.add(module_key)
        
        try:
            # Imports locais para evitar dependência circular
            from lexer import tokenize
            from parser import Parser
            
            # Lê e parseia o módulo
            source = full_path.read_text(encoding="utf-8")
            tokens = tokenize(source, str(full_path))
            parser = Parser(tokens)
            program = parser.parse()
            
            # Recursivamente verifica o módulo importado?
            # Na verdade, precisamos apenas extrair as definições.
            # Se quiséssemos verificar types do módulo também, chamaríamos recursivemente.
            # Por segurança e completude, vamos extrair definições.
            
            # Coleta definições do módulo
            module_functions: dict[str, FuncDef] = {}
            module_structs: dict[str, StructDef] = {}
            module_globals: dict[str, GlobalStmt] = {}
            
            # Nota: Ao importar, também processamos os imports DELE recursivamente
            # Para isso, criaríamos um novo TypeChecker ou reusaríamos este?
            # O ideal é apenas extrair as assinaturas públicas. 
            # Mas se ele usa tipos de outros módulos, precisaríamos saber.
            # Simplificação: Apenas extrai Structs e Funcs declarados nele.
            
            for s in program.statements:
                if isinstance(s, FuncDef):
                    module_functions[s.name] = s
                elif isinstance(s, StructDef):
                    module_structs[s.name] = s
                elif isinstance(s, GlobalStmt):
                    module_globals[s.name] = s
                # TODO: Suporte a imports transitivos se necessário
            
            # Importa os símbolos solicitados
            if stmt.imports == ["*"]:
                # Importa tudo
                for name, func in module_functions.items():
                    self.functions[name] = func
                for name, struct in module_structs.items():
                    self.structs[name] = struct
                for name, glob in module_globals.items():
                    self.define_var(name, glob.var_type)
            else:
                # Importa símbolos específicos
                for symbol in stmt.imports:
                    if symbol in module_functions:
                        self.functions[symbol] = module_functions[symbol]
                    elif symbol in module_structs:
                        self.structs[symbol] = module_structs[symbol]
                    elif symbol in module_globals:
                        self.define_var(symbol, module_globals[symbol].var_type)
                    else:
                        raise NoxyTypeError(
                            f"Símbolo '{symbol}' não encontrado no módulo '{'.'.join(stmt.module_path)}'",
                            stmt.location
                        )
                        
        except Exception as e:
            if isinstance(e, NoxyError):
                raise e
            raise NoxyTypeError(f"Erro ao importar módulo: {e}", stmt.location)
    
    def check_let(self, stmt: LetStmt):
        """Verifica declaração let."""
        init_type = self.check_expression(stmt.initializer)
        
        # Arrays têm regras especiais
        if isinstance(stmt.var_type, ArrayType):
            if isinstance(init_type, ArrayType):
                if not types_equal(stmt.var_type.element_type, init_type.element_type):
                    raise NoxyTypeError(
                        f"Tipo do elemento do array não corresponde: "
                        f"esperado '{stmt.var_type.element_type}', "
                        f"obtido '{init_type.element_type}'",
                        stmt.location
                    )
            # zeros() retorna int[]
        elif not self.types_compatible(stmt.var_type, init_type):
            raise NoxyTypeError(
                f"Tipo do valor inicial não corresponde ao tipo declarado: "
                f"esperado '{type_to_str(stmt.var_type)}', "
                f"obtido '{type_to_str(init_type)}'",
                stmt.location
            )
        
        self.define_var(stmt.name, stmt.var_type)
    
    def check_global(self, stmt: GlobalStmt):
        """Verifica declaração global."""
        init_type = self.check_expression(stmt.initializer)
        
        if not self.types_compatible(stmt.var_type, init_type):
            raise NoxyTypeError(
                f"Tipo do valor inicial não corresponde ao tipo declarado: "
                f"esperado '{type_to_str(stmt.var_type)}', "
                f"obtido '{type_to_str(init_type)}'",
                stmt.location
            )
        
        self.scopes[0][stmt.name] = stmt.var_type
    
    def check_assignment(self, stmt: AssignStmt):
        """Verifica atribuição."""
        target_type = self.check_expression(stmt.target)
        value_type = self.check_expression(stmt.value)
        
        if not self.types_compatible(target_type, value_type):
            raise NoxyTypeError(
                f"Não é possível atribuir valor do tipo '{type_to_str(value_type)}' "
                f"a variável do tipo '{type_to_str(target_type)}'. "
                f"O tipo de uma variável não pode ser alterado após a declaração.",
                stmt.location
            )
    
    def check_if(self, stmt: IfStmt):
        """Verifica if statement."""
        cond_type = self.check_expression(stmt.condition)
        if not isinstance(cond_type, PrimitiveType) or cond_type.name != "bool":
            raise NoxyTypeError(
                f"Condição do if deve ser bool, obtido '{type_to_str(cond_type)}'",
                stmt.location
            )
        
        self.push_scope()
        for s in stmt.then_body:
            self.check_statement(s)
        self.pop_scope()
        
        self.push_scope()
        for s in stmt.else_body:
            self.check_statement(s)
        self.pop_scope()
    
    def check_while(self, stmt: WhileStmt):
        """Verifica while statement."""
        cond_type = self.check_expression(stmt.condition)
        if not isinstance(cond_type, PrimitiveType) or cond_type.name != "bool":
            raise NoxyTypeError(
                f"Condição do while deve ser bool, obtido '{type_to_str(cond_type)}'",
                stmt.location
            )
        
        self.push_scope()
        for s in stmt.body:
            self.check_statement(s)
        self.pop_scope()
    
    def check_return(self, stmt: ReturnStmt):
        """Verifica return statement."""
        if self.current_function_return_type is None:
            return
        
        if stmt.value is None:
            if not isinstance(self.current_function_return_type, PrimitiveType) or \
               self.current_function_return_type.name != "void":
                raise NoxyTypeError(
                    f"Função deve retornar '{type_to_str(self.current_function_return_type)}', "
                    f"mas retorna void",
                    stmt.location
                )
        else:
            value_type = self.check_expression(stmt.value)
            if not self.types_compatible(self.current_function_return_type, value_type):
                raise NoxyTypeError(
                    f"Função deve retornar '{type_to_str(self.current_function_return_type)}', "
                    f"mas retorna '{type_to_str(value_type)}'",
                    stmt.location
                )
    
    def check_func_def(self, stmt: FuncDef):
        """Verifica definição de função."""
        prev_return_type = self.current_function_return_type
        self.current_function_return_type = stmt.return_type
        
        self.push_scope()
        for param in stmt.params:
            self.define_var(param.name, param.param_type)
        
        for s in stmt.body:
            self.check_statement(s)
        
        self.pop_scope()
        self.current_function_return_type = prev_return_type
    
    def check_expression(self, expr: Expr) -> NoxyType:
        """Verifica tipo de uma expressão e retorna o tipo."""
        if isinstance(expr, IntLiteral):
            return PrimitiveType("int")
        
        if isinstance(expr, FloatLiteral):
            return PrimitiveType("float")
        
        if isinstance(expr, StringLiteral):
            return PrimitiveType("string")
            
        if isinstance(expr, BytesLiteral):
            return PrimitiveType("bytes")
        
        if isinstance(expr, BoolLiteral):
            return PrimitiveType("bool")
        
        if isinstance(expr, NullLiteral):
            # null pode ser qualquer ref type - retorna tipo especial
            return RefType(PrimitiveType("void"))
        
        if isinstance(expr, Identifier):
            var_type = self.lookup_var(expr.name)
            if var_type is None:
                # Pode ser um construtor de struct
                if expr.name in self.structs:
                    return StructType(expr.name)
                raise NoxyTypeError(
                    f"Variável '{expr.name}' não definida",
                    expr.location
                )
            return var_type
        
        if isinstance(expr, BinaryOp):
            return self.check_binary_op(expr)
        
        if isinstance(expr, UnaryOp):
            return self.check_unary_op(expr)
        
        if isinstance(expr, CallExpr):
            return self.check_call(expr)
        
        if isinstance(expr, IndexExpr):
            return self.check_index(expr)
        
        if isinstance(expr, FieldAccess):
            return self.check_field_access(expr)
        
        if isinstance(expr, ArrayLiteral):
            return self.check_array_literal(expr)
        
        if isinstance(expr, RefExpr):
            inner_type = self.check_expression(expr.value)
            return RefType(inner_type)
        
        if isinstance(expr, FString):
            return PrimitiveType("string")
        
        if isinstance(expr, ZerosExpr):
            size_type = self.check_expression(expr.size)
            if not isinstance(size_type, PrimitiveType) or size_type.name != "int":
                raise NoxyTypeError(
                    f"Tamanho de zeros() deve ser int, obtido '{type_to_str(size_type)}'",
                    expr.location
                )
            return ArrayType(PrimitiveType("int"), None)
        
        if isinstance(expr, GroupExpr):
            return self.check_expression(expr.expr)
        
        raise NoxyTypeError(f"Expressão desconhecida: {type(expr)}", expr.location)
    
    def check_binary_op(self, expr: BinaryOp) -> NoxyType:
        """Verifica operação binária."""
        left_type = self.check_expression(expr.left)
        right_type = self.check_expression(expr.right)
        op = expr.operator
        
        # Operadores aritméticos
        if op in ("+", "-", "*", "/", "%"):
            if op == "+" and isinstance(left_type, PrimitiveType) and left_type.name == "string":
                if not isinstance(right_type, PrimitiveType) or right_type.name != "string":
                    raise NoxyTypeError(
                        f"Concatenação requer string + string",
                        expr.location
                    )
                return PrimitiveType("string")
            
            if op == "+" and isinstance(left_type, PrimitiveType) and left_type.name == "bytes":
                if not isinstance(right_type, PrimitiveType) or right_type.name != "bytes":
                    raise NoxyTypeError(
                        f"Concatenação requer bytes + bytes",
                        expr.location
                    )
                return PrimitiveType("bytes")
            
            if not types_equal(left_type, right_type):
                raise NoxyTypeError(
                    f"Operador '{op}' requer operandos do mesmo tipo, "
                    f"obtido '{type_to_str(left_type)}' e '{type_to_str(right_type)}'",
                    expr.location
                )
            if not is_numeric(left_type):
                raise NoxyTypeError(
                    f"Operador '{op}' requer tipos numéricos",
                    expr.location
                )
            return left_type
        
        # Operadores de comparação
        if op in (">", "<", ">=", "<="):
            if not types_equal(left_type, right_type):
                raise NoxyTypeError(
                    f"Comparação requer operandos do mesmo tipo",
                    expr.location
                )
            if not is_numeric(left_type):
                raise NoxyTypeError(
                    f"Operador '{op}' requer tipos numéricos",
                    expr.location
                )
            return PrimitiveType("bool")
        
        # Igualdade
        if op in ("==", "!="):
            # Permite comparação com null para tipos ref
            if isinstance(left_type, RefType) or isinstance(right_type, RefType):
                return PrimitiveType("bool")
            if not types_equal(left_type, right_type):
                raise NoxyTypeError(
                    f"Comparação requer operandos do mesmo tipo",
                    expr.location
                )
            return PrimitiveType("bool")
        
        # Operadores lógicos
        if op in ("&", "|"):
            if not isinstance(left_type, PrimitiveType) or left_type.name != "bool":
                raise NoxyTypeError(
                    f"Operador '{op}' requer operandos bool",
                    expr.location
                )
            if not isinstance(right_type, PrimitiveType) or right_type.name != "bool":
                raise NoxyTypeError(
                    f"Operador '{op}' requer operandos bool",
                    expr.location
                )
            return PrimitiveType("bool")
        
        raise NoxyTypeError(f"Operador desconhecido: {op}", expr.location)
    
    def check_unary_op(self, expr: UnaryOp) -> NoxyType:
        """Verifica operação unária."""
        operand_type = self.check_expression(expr.operand)
        
        if expr.operator == "-":
            if not is_numeric(operand_type):
                raise NoxyTypeError(
                    f"Operador '-' requer tipo numérico",
                    expr.location
                )
            return operand_type
        
        if expr.operator == "!":
            if not isinstance(operand_type, PrimitiveType) or operand_type.name != "bool":
                raise NoxyTypeError(
                    f"Operador '!' requer tipo bool",
                    expr.location
                )
            return PrimitiveType("bool")
        
        raise NoxyTypeError(f"Operador unário desconhecido: {expr.operator}", expr.location)
    
    def check_call(self, expr: CallExpr) -> NoxyType:
        """Verifica chamada de função/construtor."""
        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            
            # Construtor de struct
            if name in self.structs:
                struct_def = self.structs[name]
                if len(expr.arguments) != len(struct_def.fields):
                    raise NoxyTypeError(
                        f"Construtor '{name}' espera {len(struct_def.fields)} argumentos, "
                        f"recebeu {len(expr.arguments)}",
                        expr.location
                    )
                for arg, field in zip(expr.arguments, struct_def.fields):
                    arg_type = self.check_expression(arg)
                    if not self.types_compatible(field.field_type, arg_type):
                        raise NoxyTypeError(
                            f"Argumento para campo '{field.name}' tem tipo errado: "
                            f"esperado '{type_to_str(field.field_type)}', "
                            f"obtido '{type_to_str(arg_type)}'",
                            expr.location
                        )
                return StructType(name)
        
        # Method call syntax support (e.g., io.open)
        callee_expr = expr.callee
        method_name = None
        
        if isinstance(callee_expr, FieldAccess):
            # Valida se é chamada em io
            obj_type = self.check_expression(callee_expr.object)
            if isinstance(obj_type, StructType) and obj_type.name == "IO":
                # Mapeia io.method -> io_method
                method_name = f"io_{callee_expr.field_name}"
            # Poderíamos adicionar outros tipos no futuro
            
        elif isinstance(callee_expr, Identifier):
             method_name = callee_expr.name

        if method_name:
            # Função definida pelo usuário (somente se não for builtin mapeado)
            if not method_name.startswith("io_") and method_name in self.functions:
                 func_def = self.functions[method_name]
                 if len(expr.arguments) != len(func_def.params):
                     raise NoxyTypeError(
                         f"Função '{method_name}' espera {len(func_def.params)} argumentos, "
                         f"recebeu {len(expr.arguments)}",
                         expr.location
                     )
                 for i, (arg, param) in enumerate(zip(expr.arguments, func_def.params)):
                     arg_type = self.check_expression(arg)
                     # Permite passar struct ou array como ref (referência implícita)
                     if isinstance(param.param_type, RefType):
                         inner = param.param_type.inner_type
                         # Struct passado como ref
                         if isinstance(arg_type, StructType) and inner == arg_type:
                             continue
                         # Array passado como ref
                         if isinstance(arg_type, ArrayType) and isinstance(inner, ArrayType):
                             if arg_type.element_type == inner.element_type:
                                 continue
                     if not self.types_compatible(param.param_type, arg_type):
                         raise NoxyTypeError(
                             f"Argumento {i + 1} da função '{method_name}' tem tipo "
                             f"'{type_to_str(arg_type)}', esperado '{type_to_str(param.param_type)}'",
                             expr.location
                         )
                 return func_def.return_type

            # Builtin Functions
            if method_name in BUILTIN_SIGNATURES:
                ret_type, param_types = BUILTIN_SIGNATURES[method_name]
                
                # Varargs check (print)
                if param_types == [Any]:
                    for arg in expr.arguments:
                        self.check_expression(arg)
                    return ret_type if ret_type else PrimitiveType("void")

                if len(expr.arguments) != len(param_types):
                     raise NoxyTypeError(
                         f"Função '{method_name}' espera {len(param_types)} argumentos, "
                         f"recebeu {len(expr.arguments)}",
                         expr.location
                     )
                
                for i, (arg, expected_type) in enumerate(zip(expr.arguments, param_types)):
                    arg_type = self.check_expression(arg)
                    if expected_type == Any:
                        continue
                        
                    if not self.types_compatible(expected_type, arg_type):
                         # Caso especial: permitindo conversão implícita ou checks relaxados?
                         # Por agora strict
                         raise NoxyTypeError(
                             f"Argumento {i + 1} da função '{method_name}' tem tipo "
                             f"'{type_to_str(arg_type)}', esperado '{type_to_str(expected_type)}'",
                             expr.location
                         )
                return ret_type

        # Se chegou aqui e era Identifier, mas não achou
        if isinstance(callee_expr, Identifier):
             raise NoxyTypeError(f"Função '{callee_expr.name}' não definida", expr.location)
             
        # Se era FieldAccess mas não mapeou
        if isinstance(callee_expr, FieldAccess):
             raise NoxyTypeError(f"Método '{callee_expr.field_name}' não suportado em '{type_to_str(obj_type)}'", expr.location)
             
        # Fallback

        
        # Fallback
        for arg in expr.arguments:
            self.check_expression(arg)
        return PrimitiveType("void")
    
    def check_index(self, expr: IndexExpr) -> NoxyType:
        """Verifica acesso por índice."""
        obj_type = self.check_expression(expr.object)
        index_type = self.check_expression(expr.index)
        
        if not isinstance(index_type, PrimitiveType) or index_type.name != "int":
            raise NoxyTypeError(
                f"Índice deve ser int, obtido '{type_to_str(index_type)}'",
                expr.location
            )
        
        # Desreferencia ref types automaticamente
        if isinstance(obj_type, RefType):
            obj_type = obj_type.inner_type
        
        if isinstance(obj_type, ArrayType):
            return obj_type.element_type
        
        if isinstance(obj_type, PrimitiveType) and obj_type.name == "string":
            return PrimitiveType("string")

        if isinstance(obj_type, PrimitiveType) and obj_type.name == "bytes":
            return PrimitiveType("int")
        
        raise NoxyTypeError(
            f"Tipo '{type_to_str(obj_type)}' não suporta indexação",
            expr.location
        )
    
    def check_field_access(self, expr: FieldAccess) -> NoxyType:
        """Verifica acesso a campo."""
        obj_type = self.check_expression(expr.object)
        
        # Desreferencia ref types automaticamente
        if isinstance(obj_type, RefType):
            obj_type = obj_type.inner_type
        
        if isinstance(obj_type, StructType):
            struct_def = self.structs.get(obj_type.name)
            if struct_def is None:
                raise NoxyTypeError(
                    f"Struct '{obj_type.name}' não definido",
                    expr.location
                )
            for field in struct_def.fields:
                if field.name == expr.field_name:
                    return field.field_type
            raise NoxyTypeError(
                f"Struct '{obj_type.name}' não tem campo '{expr.field_name}'",
                expr.location
            )
        
        raise NoxyTypeError(
            f"Tipo '{type_to_str(obj_type)}' não suporta acesso a campos",
            expr.location
        )
    
    def check_array_literal(self, expr: ArrayLiteral) -> NoxyType:
        """Verifica literal de array."""
        if not expr.elements:
            # Array vazio - tipo será determinado pelo contexto
            return ArrayType(PrimitiveType("void"), 0)
        
        first_type = self.check_expression(expr.elements[0])
        
        for elem in expr.elements[1:]:
            elem_type = self.check_expression(elem)
            if not self.types_compatible(first_type, elem_type):
                raise NoxyTypeError(
                    f"Elementos do array têm tipos inconsistentes: "
                    f"'{type_to_str(first_type)}' e '{type_to_str(elem_type)}'",
                    expr.location
                )
        
        return ArrayType(first_type, len(expr.elements))
    
    def types_compatible(self, expected: NoxyType, actual: NoxyType) -> bool:
        """Verifica se tipos são compatíveis para atribuição."""
        # null é compatível com qualquer tipo ref
        if isinstance(actual, RefType):
            if isinstance(actual.inner_type, PrimitiveType) and actual.inner_type.name == "void":
                return isinstance(expected, RefType)
        
        # Arrays com mesmo tipo de elemento são compatíveis
        if isinstance(expected, ArrayType) and isinstance(actual, ArrayType):
            return types_equal(expected.element_type, actual.element_type)
        
        return types_equal(expected, actual)


def check_types(program: Program, base_path: str = "."):
    """Função auxiliar para verificar tipos."""
    checker = TypeChecker(base_path)
    checker.check_program(program)


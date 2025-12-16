"""
Noxy Interpreter - Sistema de Tipos
Verificação de tipos estática e utilitários de tipos.
"""

from ast_nodes import (
    NoxyType, PrimitiveType, ArrayType, StructType, RefType,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, CallExpr, IndexExpr, FieldAccess,
    ArrayLiteral, RefExpr, FString, ZerosExpr, GroupExpr, FStringExpr,
    Stmt, LetStmt, GlobalStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt,
    ReturnStmt, BreakStmt, FuncDef, StructDef, UseStmt, Program
)
from errors import NoxyTypeError, SourceLocation


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
    
    def __init__(self):
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
        # Primeira passada: coleta definições de struct e função
        for stmt in program.statements:
            if isinstance(stmt, StructDef):
                self.structs[stmt.name] = stmt
            elif isinstance(stmt, FuncDef):
                self.functions[stmt.name] = stmt
        
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
            pass  # Não implementado
    
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
            
            # Função definida
            if name in self.functions:
                func_def = self.functions[name]
                if len(expr.arguments) != len(func_def.params):
                    raise NoxyTypeError(
                        f"Função '{name}' espera {len(func_def.params)} argumentos, "
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
                            f"Argumento {i + 1} da função '{name}' tem tipo "
                            f"'{type_to_str(arg_type)}', esperado '{type_to_str(param.param_type)}'",
                            expr.location
                        )
                return func_def.return_type
            
            # Funções builtin (verificação relaxada)
            if name in ("print", "to_str", "to_int", "to_float", "strlen", "ord", "length"):
                for arg in expr.arguments:
                    self.check_expression(arg)
                if name == "print":
                    return PrimitiveType("void")
                elif name == "to_str":
                    return PrimitiveType("string")
                elif name == "to_int":
                    return PrimitiveType("int")
                elif name == "to_float":
                    return PrimitiveType("float")
                elif name in ("strlen", "ord", "length"):
                    return PrimitiveType("int")
        
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


def check_types(program: Program):
    """Função auxiliar para verificar tipos."""
    checker = TypeChecker()
    checker.check_program(program)


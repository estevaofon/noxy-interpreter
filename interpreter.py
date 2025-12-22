"""
Noxy Interpreter - Interpretador Tree-Walking
Avalia a AST e executa o programa.
"""

from typing import Any, Optional
from pathlib import Path
from ast_nodes import (
    NoxyType, PrimitiveType, ArrayType, StructType, RefType,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BytesLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, CallExpr, IndexExpr, FieldAccess,
    ArrayLiteral, RefExpr, FString, FStringExpr, ZerosExpr, GroupExpr,
    Stmt, LetStmt, GlobalStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt,
    ReturnStmt, BreakStmt, FuncDef, StructDef, UseStmt, Program
)
from environment import (
    Environment, NoxyStruct, NoxyRef, NoxyArray,
    deep_copy_value
)
from noxy_builtins import get_builtin, is_builtin, format_value, value_to_string
from errors import (
    NoxyRuntimeError, NoxyNameError, NoxyDivisionError, NoxyIndexError,
    NoxyBreakException, NoxyReturnException, NoxyTypeError
)


class Interpreter:
    """Interpretador tree-walking para Noxy."""
    
    def __init__(self, base_path: str = "."):
        self.global_env = Environment()
        self.current_env = self.global_env
        self.base_path = Path(base_path)  # Diretório base para resolver imports
        # Define o caminho da stdlib relativo ao arquivo do interpretador
        self.stdlib_path = Path(__file__).parent / "stdlib"
        self.loaded_modules: set[str] = set()  # Módulos já carregados
    
    def run(self, program: Program):
        """Executa um programa Noxy."""
        # Primeira passada: processa imports
        for stmt in program.statements:
            if isinstance(stmt, UseStmt):
                self.execute_use(stmt)
        
        # Segunda passada: registra structs e funções locais
        for stmt in program.statements:
            if isinstance(stmt, StructDef):
                self.global_env.define_struct(stmt)
            elif isinstance(stmt, FuncDef):
                self.global_env.define_function(stmt)
        
        # Terceira passada: executa statements
        for stmt in program.statements:
            if not isinstance(stmt, (StructDef, FuncDef, UseStmt)):
                self.execute(stmt)
    
    def get_default_value(self, type_node: NoxyType) -> Any:
        """Retorna valor padrão para um tipo."""
        if isinstance(type_node, PrimitiveType):
            if type_node.name == "int": return 0
            if type_node.name == "float": return 0.0
            if type_node.name == "string": return ""
            if type_node.name == "str": return ""
            if type_node.name == "bool": return False
            if type_node.name == "bytes": return b""
            return None
        
        if isinstance(type_node, ArrayType):
            if type_node.size is not None:
                elements = []
                for _ in range(type_node.size):
                     val = self.get_default_value(type_node.element_type)
                     elements.append(val)
                return NoxyArray(elements, type_node.element_type)
            return NoxyArray([], type_node.element_type)
            
        if isinstance(type_node, StructType):
            struct_def = self.current_env.get_struct(type_node.name)
            # Se struct não encontrado (ex: forward decl?), retorna None ou erro?
            # Vamos arriscar erro explícito ou None
            if not struct_def:
                 # Pode ser importado? Global env deve ter
                 struct_def = self.global_env.get_struct(type_node.name)
            
            if struct_def:
                fields = {}
                for field in struct_def.fields:
                    fields[field.name] = self.get_default_value(field.field_type)
                return NoxyStruct(type_node.name, fields)
            
            # Se não achou struct, não podemos instanciar -> Erro
            raise NoxyRuntimeError(f"Struct '{type_node.name}' não encontrado para inicialização padrão")
            
        return None

    def execute(self, stmt: Stmt):
        """Executa um statement."""
        if isinstance(stmt, LetStmt):
            self.execute_let(stmt)
        elif isinstance(stmt, GlobalStmt):
            self.execute_global(stmt)
        elif isinstance(stmt, AssignStmt):
            self.execute_assign(stmt)
        elif isinstance(stmt, ExprStmt):
            self.evaluate(stmt.expr)
        elif isinstance(stmt, IfStmt):
            self.execute_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self.execute_while(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.execute_return(stmt)
        elif isinstance(stmt, BreakStmt):
            raise NoxyBreakException()
        elif isinstance(stmt, FuncDef):
            # Já registrado na primeira passada
            pass
        elif isinstance(stmt, StructDef):
            # Já registrado na primeira passada
            pass
        elif isinstance(stmt, UseStmt):
            self.execute_use(stmt)
        else:
            raise NoxyRuntimeError(f"Statement desconhecido: {type(stmt)}")
    
    def execute_let(self, stmt: LetStmt):
        """Executa declaração let."""
        if stmt.initializer:
            value = self.evaluate(stmt.initializer)
        else:
            value = self.get_default_value(stmt.var_type)
        self.current_env.define(stmt.name, stmt.var_type, value)
    
    def execute_global(self, stmt: GlobalStmt):
        """Executa declaração global."""
        value = self.evaluate(stmt.initializer)
        self.global_env.define(stmt.name, stmt.var_type, value, is_global=True)
    
    def execute_assign(self, stmt: AssignStmt):
        """Executa atribuição."""
        value = self.evaluate(stmt.value)
        self.assign_target(stmt.target, value)
    
    def assign_target(self, target: Expr, value: Any):
        """Atribui valor a um alvo (variável, índice, campo)."""
        if isinstance(target, Identifier):
            self.current_env.set(target.name, value)
        
        elif isinstance(target, IndexExpr):
            obj = self.evaluate(target.object)
            index = self.evaluate(target.index)
            
            if not isinstance(index, int):
                raise NoxyRuntimeError("Índice deve ser inteiro")
            
            if isinstance(obj, list):
                if index < 0 or index >= len(obj):
                    raise NoxyIndexError(f"Índice {index} fora dos limites")
                obj[index] = value
            elif isinstance(obj, NoxyArray):
                if index < 0 or index >= len(obj):
                     raise NoxyIndexError(f"Índice {index} fora dos limites")
                obj[index] = value
            elif isinstance(obj, str):
                raise NoxyRuntimeError("Strings são imutáveis")
            else:
                raise NoxyRuntimeError(f"Tipo não suporta indexação: {type(obj)}")
        
        elif isinstance(target, FieldAccess):
            obj = self.evaluate(target.object)
            
            # Desreferencia NoxyRef
            while isinstance(obj, NoxyRef):
                obj = obj.get_value()
            
            if isinstance(obj, NoxyStruct):
                obj.set_field(target.field_name, value)
            else:
                raise NoxyRuntimeError(f"Tipo não suporta acesso a campo: {type(obj)}")
        
        else:
            raise NoxyRuntimeError(f"Alvo de atribuição inválido: {type(target)}")
    
    def execute_if(self, stmt: IfStmt):
        """Executa if statement."""
        condition = self.evaluate(stmt.condition)
        
        if self.is_truthy(condition):
            self.execute_block(stmt.then_body)
        else:
            self.execute_block(stmt.else_body)
    
    def execute_while(self, stmt: WhileStmt):
        """Executa while loop."""
        try:
            while self.is_truthy(self.evaluate(stmt.condition)):
                try:
                    self.execute_block(stmt.body)
                except NoxyBreakException:
                    break
        except NoxyBreakException:
            pass  # Break no nível externo
    
    def execute_return(self, stmt: ReturnStmt):
        """Executa return statement."""
        value = None
        if stmt.value:
            value = self.evaluate(stmt.value)
        raise NoxyReturnException(value)
    
    def execute_use(self, stmt: UseStmt):
        """Executa import de módulo."""
        # Constrói o caminho do módulo
        # use math select add  -> math.nx
        # use utils.math select add -> utils/math.nx
        module_path = "/".join(stmt.module_path) + ".nx"
        full_path = self.base_path / module_path
        
        # Verifica se o módulo existe
        if not full_path.exists():
            # Tenta na stdlib (relativo ao interpretador)
            candidate = self.stdlib_path / module_path
            if candidate.exists():
                full_path = candidate
            else:
                raise NoxyRuntimeError(
                    f"Módulo não encontrado: {module_path}",
                    stmt.location
                )
        
        # Evita carregar o mesmo módulo duas vezes
        module_key = str(full_path.resolve())
        if module_key in self.loaded_modules:
            return
        self.loaded_modules.add(module_key)
        
        # Lê e parseia o módulo
        from lexer import tokenize
        from parser import Parser
        
        source = full_path.read_text(encoding="utf-8")
        tokens = tokenize(source, str(full_path))
        parser = Parser(tokens)
        program = parser.parse()
        
        # Coleta definições do módulo (funções, structs e globals)
        module_functions: dict[str, FuncDef] = {}
        module_structs: dict[str, StructDef] = {}
        module_globals: dict[str, GlobalStmt] = {}
        
        for s in program.statements:
            if isinstance(s, FuncDef):
                module_functions[s.name] = s
            elif isinstance(s, StructDef):
                module_structs[s.name] = s
            elif isinstance(s, GlobalStmt):
                module_globals[s.name] = s
        
        # Importa os símbolos solicitados
        if stmt.imports == ["*"]:
            # Importa tudo
            for name, func in module_functions.items():
                self.global_env.define_function(func)
            for name, struct in module_structs.items():
                self.global_env.define_struct(struct)
            
            # Avalia globais no contexto do módulo
            module_env = self.global_env.new_child()
            for name, func in module_functions.items():
                module_env.define_function(func)
            for name, struct in module_structs.items():
                module_env.define_struct(struct)
            
            # Necessário para referências cruzadas entre globais
            prev_env = self.current_env
            self.current_env = module_env
            try:
                for name, glob in module_globals.items():
                    # Executa initializer
                    val = self.evaluate(glob.initializer)
                    module_env.define(name, glob.var_type, val) # Define localmente para outros usarem
                    # Define no global env do importador
                    self.global_env.define(name, glob.var_type, val, is_global=True)
            finally:
                self.current_env = prev_env
                
        else:
            # Importa símbolos específicos
            
            # Prepara ambiente para avaliação (lazy definition)
            module_env = self.global_env.new_child()
            for name, func in module_functions.items():
                module_env.define_function(func)
            for name, struct in module_structs.items():
                module_env.define_struct(struct)
                
            prev_env = self.current_env
            self.current_env = module_env
            
            try:
                # Ordenação simplificada: avalia o que foi pedido
                # Se houver dependência entre globais, isso pode falhar se não importarmos na ordem certa ou tudo.
                # Assumimos que globais exportados são independentes ou dependem de funcs/structs.
                
                for symbol in stmt.imports:
                    if symbol in module_functions:
                        self.global_env.define_function(module_functions[symbol])
                    elif symbol in module_structs:
                        self.global_env.define_struct(module_structs[symbol])
                    elif symbol in module_globals:
                        glob = module_globals[symbol]
                        val = self.evaluate(glob.initializer)
                        self.global_env.define(symbol, glob.var_type, val, is_global=True)
                    else:
                        raise NoxyRuntimeError(
                            f"Símbolo '{symbol}' não encontrado no módulo '{'.'.join(stmt.module_path)}'",
                            stmt.location
                        )
            finally:
                self.current_env = prev_env

    
    def execute_block(self, statements: list[Stmt]):
        """Executa um bloco de statements."""
        previous_env = self.current_env
        self.current_env = self.current_env.new_child()
        
        try:
            for stmt in statements:
                self.execute(stmt)
        finally:
            self.current_env = previous_env
    
    def evaluate(self, expr: Expr) -> Any:
        """Avalia uma expressão e retorna o valor."""
        if isinstance(expr, IntLiteral):
            return expr.value
        
        if isinstance(expr, FloatLiteral):
            return expr.value
        
        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, BytesLiteral):
            return expr.value
        
        if isinstance(expr, BoolLiteral):
            return expr.value
        
        if isinstance(expr, NullLiteral):
            return None
        
        if isinstance(expr, Identifier):
            return self.current_env.get_value(expr.name)
        
        if isinstance(expr, BinaryOp):
            return self.evaluate_binary(expr)
        
        if isinstance(expr, UnaryOp):
            return self.evaluate_unary(expr)
        
        if isinstance(expr, CallExpr):
            return self.evaluate_call(expr)
        
        if isinstance(expr, IndexExpr):
            return self.evaluate_index(expr)
        
        if isinstance(expr, FieldAccess):
            return self.evaluate_field(expr)
        
        if isinstance(expr, ArrayLiteral):
            return [self.evaluate(e) for e in expr.elements]
        
        if isinstance(expr, RefExpr):
            return self.evaluate_ref(expr)
        
        if isinstance(expr, FString):
            return self.evaluate_fstring(expr)
        
        if isinstance(expr, ZerosExpr):
            size = self.evaluate(expr.size)
            if not isinstance(size, int):
                raise NoxyRuntimeError("Tamanho de zeros() deve ser int")
            return [0] * size
        
        if isinstance(expr, GroupExpr):
            return self.evaluate(expr.expr)
        
        raise NoxyRuntimeError(f"Expressão desconhecida: {type(expr)}")
    
    def evaluate_binary(self, expr: BinaryOp) -> Any:
        """Avalia operação binária."""
        # Short-circuit para operadores lógicos
        if expr.operator == "&":
            left = self.evaluate(expr.left)
            if not self.is_truthy(left):
                return False
            return self.is_truthy(self.evaluate(expr.right))
        
        if expr.operator == "|":
            left = self.evaluate(expr.left)
            if self.is_truthy(left):
                return True
            return self.is_truthy(self.evaluate(expr.right))
        
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        op = expr.operator
        
        # Aritméticos
        if op == "+":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, bytes) and isinstance(right, bytes):
                return left + right
            return left + right
        
        if op == "-":
            return left - right
        
        if op == "*":
            return left * right
        
        if op == "/":
            if right == 0:
                raise NoxyDivisionError("Divisão por zero")
            if isinstance(left, int) and isinstance(right, int):
                return left // right  # Divisão inteira
            return left / right
        
        if op == "%":
            if right == 0:
                raise NoxyDivisionError("Módulo por zero")
            return left % right
        
        # Comparação
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == "==":
            return self.equals(left, right)
        if op == "!=":
            return not self.equals(left, right)
        
        raise NoxyRuntimeError(f"Operador desconhecido: {op}")
    
    def evaluate_unary(self, expr: UnaryOp) -> Any:
        """Avalia operação unária."""
        operand = self.evaluate(expr.operand)
        
        if expr.operator == "-":
            return -operand
        
        if expr.operator == "!":
            return not self.is_truthy(operand)
        
        raise NoxyRuntimeError(f"Operador unário desconhecido: {expr.operator}")
    
    def evaluate_call(self, expr: CallExpr) -> Any:
        """Avalia chamada de função ou construtor."""
        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            
            # Construtor de struct
            struct_def = self.current_env.get_struct(name)
            if struct_def:
                return self.create_struct(struct_def, expr.arguments)
            
            # Função definida pelo usuário
            func_def = self.current_env.get_function(name)
            if func_def:
                return self.call_function(func_def, expr.arguments)
            
            # Função builtin
            if is_builtin(name):
                args = [self.evaluate(arg) for arg in expr.arguments]
                builtin_fn = get_builtin(name)
                return builtin_fn(*args)
            
            raise NoxyNameError(f"Função '{name}' não definida")
        
        # Chamada de método (io.open etc)
        if isinstance(expr.callee, FieldAccess):
            obj = self.evaluate(expr.callee.object)
            method_name = expr.callee.field_name
            
            # Verifica se é objeto IO
            if isinstance(obj, NoxyStruct) and obj.type_name == "IO":
                builtin_name = f"io_{method_name}"
                if is_builtin(builtin_name):
                    args = [self.evaluate(arg) for arg in expr.arguments]
                    builtin_fn = get_builtin(builtin_name)
                    res = builtin_fn(*args)
                    
                    # Converte dict para NoxyStruct se necessário
                    if isinstance(res, dict):
                        # Detecta tipo de retorno baseado no método
                        # Simplificação: se tem 'fd', é File. Se tem 'ok', é IOResult/FileInfo
                        if "fd" in res:
                            return NoxyStruct("File", res)
                        elif "exists" in res:
                            return NoxyStruct("FileInfo", res)
                        elif "ok" in res:
                            # Tratamento especial para IOResult.data que pode ser list
                            data = res["data"]
                            # Se for lista, converte para NoxyArray (se tivermos suporte) ou ...
                            # NoxyArray espera tipo.
                            # Mas IOResult é {ok: bool, data: string, error: string}
                            # Se data for lista, vai quebrar se não tratarmos.
                            # Hack: se for lista, converte pra string representação ou mantém lista python se engine aguentar?
                            # O engine Python aguenta lista em value.
                            return NoxyStruct("IOResult", res)
                    return res
                else:
                    raise NoxyRuntimeError(f"Método IO '{method_name}' não suportado")
            
            # Verifica se é objeto Net
            if isinstance(obj, NoxyStruct) and obj.type_name == "Net":
                builtin_name = f"net_{method_name}"
                if is_builtin(builtin_name):
                    args = [self.evaluate(arg) for arg in expr.arguments]
                    builtin_fn = get_builtin(builtin_name)
                    res = builtin_fn(*args)
                    return res
                else:
                    raise NoxyRuntimeError(f"Método Net '{method_name}' não suportado")

            # Verifica se é objeto Sqlite
            if isinstance(obj, NoxyStruct) and obj.type_name == "Sqlite":
                builtin_name = f"sqlite_{method_name}"
                if is_builtin(builtin_name):
                    args = [self.evaluate(arg) for arg in expr.arguments]
                    builtin_fn = get_builtin(builtin_name)
                    res = builtin_fn(*args)
                    return res
                else:
                    raise NoxyRuntimeError(f"Método Sqlite '{method_name}' não suportado")

        
        # Chamada em expressão
        callee = self.evaluate(expr.callee)
        raise NoxyRuntimeError(f"Não é possível chamar: {type(callee)}")
    
    def create_struct(self, struct_def: StructDef, args: list[Expr]) -> NoxyStruct:
        """Cria uma instância de struct."""
        if len(args) != len(struct_def.fields):
            raise NoxyRuntimeError(
                f"Construtor '{struct_def.name}' espera {len(struct_def.fields)} "
                f"argumentos, recebeu {len(args)}"
            )
        
        fields = {}
        for field, arg in zip(struct_def.fields, args):
            value = self.evaluate(arg)
            fields[field.name] = value
        
        return NoxyStruct(struct_def.name, fields)
    
    def call_function(self, func_def: FuncDef, args: list[Expr]) -> Any:
        """Chama uma função definida pelo usuário."""
        if len(args) != len(func_def.params):
            raise NoxyRuntimeError(
                f"Função '{func_def.name}' espera {len(func_def.params)} "
                f"argumentos, recebeu {len(args)}"
            )
        
        # Cria novo ambiente para a função
        func_env = self.global_env.new_child()
        
        # Avalia e passa argumentos
        for param, arg in zip(func_def.params, args):
            value = self.evaluate(arg)
            
            # Semântica de passagem por valor vs referência
            if isinstance(param.param_type, RefType):
                # Passagem por referência - mantém o valor original (não copia)
                if isinstance(arg, RefExpr):
                    # value já é NoxyRef
                    pass
                elif isinstance(value, NoxyRef):
                    # Já é referência
                    pass
                # Struct ou array passado diretamente como ref - não copia
            elif isinstance(param.param_type, StructType):
                # Struct sem ref = cópia profunda
                value = deep_copy_value(value)
            elif isinstance(param.param_type, ArrayType):
                # Array sem ref = cópia profunda
                if isinstance(value, list):
                    value = deep_copy_value(value)
            
            func_env.define(param.name, param.param_type, value)
        
        # Executa corpo da função
        previous_env = self.current_env
        self.current_env = func_env
        
        try:
            for stmt in func_def.body:
                self.execute(stmt)
        except NoxyReturnException as ret:
            return ret.value
        finally:
            self.current_env = previous_env
        
        return None
    
    def evaluate_index(self, expr: IndexExpr) -> Any:
        """Avalia acesso por índice."""
        obj = self.evaluate(expr.object)
        index = self.evaluate(expr.index)
        
        if not isinstance(index, int):
            raise NoxyRuntimeError("Índice deve ser inteiro")
        
        # Desreferencia se necessário
        while isinstance(obj, NoxyRef):
            obj = obj.get_value()
        
        if isinstance(obj, list) or isinstance(obj, NoxyArray):
            if index < 0 or index >= len(obj):
                raise NoxyIndexError(f"Índice {index} fora dos limites [0, {len(obj)})")
            return obj[index]
        
        if isinstance(obj, str):
            if index < 0 or index >= len(obj):
                raise NoxyIndexError(f"Índice {index} fora dos limites [0, {len(obj)})")
            return obj[index]
        
        if isinstance(obj, bytes):
            if index < 0 or index >= len(obj):
                raise NoxyIndexError(f"Índice {index} fora dos limites [0, {len(obj)})")
            return obj[index]
        
        raise NoxyRuntimeError(f"Tipo não suporta indexação: {type(obj)}")
    
    def evaluate_field(self, expr: FieldAccess) -> Any:
        """Avalia acesso a campo."""
        obj = self.evaluate(expr.object)
        
        # Desreferencia NoxyRef
        while isinstance(obj, NoxyRef):
            obj = obj.get_value()
        
        if obj is None:
            raise NoxyRuntimeError("Tentativa de acessar campo em null")
        
        if isinstance(obj, NoxyStruct):
            return obj.get_field(expr.field_name)
        
        raise NoxyRuntimeError(f"Tipo não suporta acesso a campo: {type(obj)}")
    
    def evaluate_ref(self, expr: RefExpr) -> NoxyRef:
        """Avalia expressão ref."""
        # Cria uma referência para o valor
        inner = expr.value
        
        if isinstance(inner, Identifier):
            # Referência para variável
            var = self.current_env.get(inner.name)
            # Retorna o próprio valor (não cópia) envolto em NoxyRef
            return NoxyRef(target=var.value)
        
        if isinstance(inner, FieldAccess):
            # Referência para campo de struct
            obj = self.evaluate(inner.object)
            while isinstance(obj, NoxyRef):
                obj = obj.get_value()
            return NoxyRef.create_from_field(obj, inner.field_name)
        
        if isinstance(inner, IndexExpr):
            # Referência para elemento de array
            arr = self.evaluate(inner.object)
            index = self.evaluate(inner.index)
            return NoxyRef.create_from_index(arr, index)
        
        # Valor literal - cria referência direta
        value = self.evaluate(inner)
        return NoxyRef(target=value)
    
    def evaluate_fstring(self, expr: FString) -> str:
        """Avalia f-string."""
        result = []
        
        for part in expr.parts:
            if isinstance(part, str):
                result.append(part)
            elif isinstance(part, FStringExpr):
                value = self.evaluate(part.expr)
                formatted = format_value(value, part.format_spec)
                result.append(formatted)
        
        return "".join(result)
    
    def is_truthy(self, value: Any) -> bool:
        """Verifica se um valor é verdadeiro."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, NoxyRef):
            return value.get_value() is not None
        return True
    
    def equals(self, left: Any, right: Any) -> bool:
        """Verifica igualdade entre valores."""
        # null checks
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        
        # NoxyRef comparisons
        if isinstance(left, NoxyRef):
            left = left.get_value()
        if isinstance(right, NoxyRef):
            right = right.get_value()
        
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        
        return left == right


def interpret(program: Program):
    """Função auxiliar para interpretar um programa."""
    interpreter = Interpreter()
    interpreter.run(program)
    return interpreter


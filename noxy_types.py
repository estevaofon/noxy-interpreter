"""
Noxy Interpreter - Sistema de Tipos
Verificação de tipos estática e utilitários de tipos.
"""


from typing import Any
from ast_nodes import (

    NoxyType, PrimitiveType, ArrayType, StructType, RefType, MapType, ModuleType,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BytesLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, CallExpr, IndexExpr, FieldAccess,
    ArrayLiteral, MapLiteral, RefExpr, FString, ZerosExpr, GroupExpr, FStringExpr,
    # Statements
    Stmt, LetStmt, GlobalStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt,
    ReturnStmt, BreakStmt, FuncDef, StructDef, UseStmt, Program
)
from noxy_signatures import BUILTIN_SIGNATURES
from errors import NoxyTypeError, SourceLocation, NoxyError

from pathlib import Path


def type_to_str(t: NoxyType) -> str:
    """Converte um tipo para string legível."""
    if t is Any:
        return "any"
    return str(t)


def types_equal(t1: NoxyType, t2: NoxyType) -> bool:
    """Verifica se dois tipos são idênticos."""
    if t1 is Any or t2 is Any:
        return True
    if t1 == t2:
        return True
    return False


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


def is_map_type(t: NoxyType) -> bool:
    """Verifica se é tipo map."""
    return isinstance(t, MapType)


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
        self.loaded_modules_cache: dict[str, ModuleType] = {}
    
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
        module_path_parts = stmt.module_path
        rel_path = "/".join(module_path_parts)
        
        candidates = [
            self.base_path / (rel_path + ".nx"),
            self.base_path / rel_path,
            self.stdlib_path / (rel_path + ".nx"),
            self.stdlib_path / rel_path
        ]
        
        full_path = None
        for cand in candidates:
            if cand.exists():
                full_path = cand
                break
        
        if not full_path:
            raise NoxyTypeError(
                f"Módulo não encontrado: {'.'.join(module_path_parts)}",
                stmt.location
            )
            
        # Evita ciclos e processamento duplicado
        module_key = str(full_path.resolve())
        
        module_def = None
        if module_key in self.loaded_modules_cache:
             module_def = self.loaded_modules_cache[module_key]
        else:
             try:
                 # Helper recursivo para carregar definições
                 module_def = self._load_module_definitions(full_path, module_path_parts[-1])
                 self.loaded_modules_cache[module_key] = module_def
             except Exception as e:
                 if isinstance(e, NoxyError):
                     raise e
                 import traceback
                 traceback.print_exc()
                 raise NoxyTypeError(f"Erro ao importar módulo: {e}", stmt.location)

        # Importa os símbolos solicitados (SEMPRE executa, mesmo se cacheado)
        if stmt.imports is None:
            # use pkg -> define 'pkg' como ModuleType
            self.define_var(module_def.name, module_def)
            
        elif stmt.imports == ["*"]:
            # use pkg select *
            # Importa tudo para o escopo atual
            for name, info in module_def.members.items():
                category, data = info
                if category == "func":
                    self.functions[name] = data
                elif category == "struct":
                    self.structs[name] = data
                elif category == "var":
                    self.define_var(name, data)
        else:
            # Importa símbolos específicos
            for symbol in stmt.imports:
                if symbol in module_def.members:
                    category, data = module_def.members[symbol]
                    if category == "func":
                            self.functions[symbol] = data
                    elif category == "struct":
                            self.structs[symbol] = data
                    elif category == "var":
                            self.define_var(symbol, data)
                else:
                    raise NoxyTypeError(
                        f"Símbolo '{symbol}' não encontrado no módulo '{'.'.join(stmt.module_path)}'",
                        stmt.location
                    )

    def _load_module_definitions(self, path: Path, name: str) -> ModuleType:
        """Carrega definições de um módulo (arquivo ou pasta)."""
        module_type = ModuleType(name)
        
        if path.is_file():
            # Arquivo único
            self._parse_and_collect(path, module_type)
        elif path.is_dir():
             # Diretório
             for child in path.iterdir():
                 if child.name.startswith(".") or child.name.startswith("__"):
                     continue
                 
                 if child.is_dir():
                     sub_mod = self._load_module_definitions(child, child.name)
                     # Submódulos são tratados como variáveis do tipo ModuleType
                     module_type.members[child.name] = ("var", sub_mod)
                 elif child.suffix == ".nx":
                     # Se for arquivo no folder, seus membros são do módulo pai?
                     # Na implementação do INTERPRETER, sim (se não me engano aggregação).
                     # Vamos checar:
                     # interpreter.py _load_module:
                     # elif child.suffix == ".nx": sub_mod = self._load_module(child); module.set_member(child.stem, sub_mod)
                     # ENTÃO NÃO! O interpretador cria sub-módulos para arquivos dentro da pasta.
                     # "use pkg" -> pkg é pasta. pkg.mod é arquivo.
                     # pkg.mod deve ser acessível.
                     
                     sub_mod = self._load_module_definitions(child, child.stem)
                     module_type.members[child.stem] = ("var", sub_mod)
                     
                     # IMPORTANTE: Se o arquivo é init.nx (ou mod.nx principal?), ele poderia exportar para o pai?
                     # Noxy atual usa hierarquia estrita.
                     
        return module_type

    def _parse_and_collect(self, path: Path, module_type: ModuleType):
        """Parseia arquivo e coleta definições."""
        # Imports locais para evitar dependência circular
        from lexer import tokenize
        from parser import Parser
        
        source = path.read_text(encoding="utf-8")
        tokens = tokenize(source, str(path))
        parser = Parser(tokens)
        program = parser.parse()
        
        for s in program.statements:
             if isinstance(s, FuncDef):
                 module_type.members[s.name] = ("func", s)
             elif isinstance(s, StructDef):
                 module_type.members[s.name] = ("struct", s)
             elif isinstance(s, GlobalStmt):
                 module_type.members[s.name] = ("var", s.var_type)
             # Recursão de UseStmt?
             # Se o módulo importa outros, eles não são exportados automaticamente (public by default?).
             # Python não exporta imports. Noxy também não deve.

    
    def check_let(self, stmt: LetStmt):
        """Verifica declaração let."""
        if stmt.initializer:
            init_type = self.check_expression(stmt.initializer)
            
            # Arrays têm regras especiais
            if isinstance(stmt.var_type, ArrayType):
                if isinstance(init_type, ArrayType):
                    # Se array vazio (void), é compatível
                    if isinstance(init_type.element_type, PrimitiveType) and init_type.element_type.name == "void":
                        pass
                    elif not types_equal(stmt.var_type.element_type, init_type.element_type):
                        raise NoxyTypeError(
                            f"Tipo do elemento do array não corresponde: "
                            f"esperado '{type_to_str(stmt.var_type.element_type)}', "
                            f"obtido '{type_to_str(init_type.element_type)}'",
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
        
        if isinstance(expr, MapLiteral):
            return self.check_map_literal(expr)
        
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
            
            if isinstance(obj_type, ModuleType):
                 # Chamada de função em módulo: pkg.func()
                 member_name = callee_expr.field_name
                 if member_name not in obj_type.members:
                     raise NoxyTypeError(f"Membro '{member_name}' não encontrado no módulo '{obj_type.name}'", expr.location)
                 
                 category, data = obj_type.members[member_name]
                 if category == "func":
                     # check func def call
                     func_def = data
                     if len(expr.arguments) != len(func_def.params):
                         raise NoxyTypeError(
                             f"Função '{member_name}' espera {len(func_def.params)} argumentos, "
                             f"recebeu {len(expr.arguments)}",
                             expr.location
                         )
                     for i, (arg, param) in enumerate(zip(expr.arguments, func_def.params)):
                         arg_type = self.check_expression(arg)
                         if isinstance(param.param_type, RefType):
                             inner = param.param_type.inner_type
                             if isinstance(arg_type, StructType) and inner == arg_type: continue
                             if isinstance(arg_type, ArrayType) and isinstance(inner, ArrayType) and arg_type.element_type == inner.element_type: continue
                         
                         if not self.types_compatible(param.param_type, arg_type):
                             raise NoxyTypeError(
                                 f"Argumento {i + 1} da função '{member_name}' tem tipo "
                                 f"'{type_to_str(arg_type)}', esperado '{type_to_str(param.param_type)}'",
                                 expr.location
                             )
                     return func_def.return_type
                 elif category == "struct":
                     # struct constructor via module? pkg.Struct()
                     struct_def = data
                     if len(expr.arguments) != len(struct_def.fields):
                        raise NoxyTypeError(
                            f"Construtor '{member_name}' espera {len(struct_def.fields)} argumentos, "
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
                     return StructType(struct_def.name, obj_type.name)
                 else:
                     raise NoxyTypeError(f"'{member_name}' não é chamável", expr.location)
            
            if isinstance(obj_type, StructType) and obj_type.name == "IO":
                # Mapeia io.method -> io_method
                method_name = f"io_{callee_expr.field_name}"
            # Net support
            elif isinstance(obj_type, StructType) and obj_type.name == "Net":
                method_name = f"net_{callee_expr.field_name}"
            # SQLite support
            elif isinstance(obj_type, StructType) and obj_type.name == "Sqlite":
                method_name = f"sqlite_{callee_expr.field_name}"
            # Strings support
            elif isinstance(obj_type, StructType) and obj_type.name == "Strings":
                method_name = f"strings_{callee_expr.field_name}"
            
            # Array methods support
            elif isinstance(obj_type, ArrayType):
                # Mapping: arr.append(x) -> append(arr, x)
                # Supported methods: append, pop, remove, length, contains
                if callee_expr.field_name in ("append", "pop", "remove", "length", "contains"):
                    method_name = callee_expr.field_name
                else:
                    raise NoxyTypeError(
                        f"Método '{callee_expr.field_name}' não suportado para Array",
                        expr.location
                    )
            
            # Map methods support
            elif isinstance(obj_type, MapType):
                # Mapping: map.keys() -> keys(map)
                # Supported methods: keys, has_key, delete, length
                if callee_expr.field_name in ("keys", "has_key", "delete", "length"):
                    method_name = callee_expr.field_name
                else:
                    raise NoxyTypeError(
                        f"Método '{callee_expr.field_name}' não suportado para Map",
                        expr.location
                    )

        elif isinstance(callee_expr, Identifier):
             method_name = callee_expr.name

        if method_name:



            # Builtin Functions
            if method_name in BUILTIN_SIGNATURES:
                ret_type, param_types = BUILTIN_SIGNATURES[method_name]


            # Função definida pelo usuário (somente se não for builtin mapeado)
            if not method_name.startswith("io_") and not method_name.startswith("net_") and not method_name.startswith("sqlite_") and not method_name.startswith("strings_") and method_name in self.functions:
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
                
                # Para chamadas de método em Arrays/Maps, o primeiro argumento (self) é implícito
                effective_args = list(expr.arguments)
                expected_params = list(param_types)

                # Se for método de array/map, verificar se precisamos validar o 'self' como primeiro param
                if isinstance(expr.callee, FieldAccess):
                     # Recupera o tipo do objeto (já verificado acima, mas precisamos aqui)
                     obj_type = self.check_expression(expr.callee.object)
                     
                     if isinstance(obj_type, ArrayType) or isinstance(obj_type, MapType):
                         if len(expected_params) > 0:
                             # Verifica se o primeiro parametro da assinatura é compatível com o objeto
                             # Ex: append(arr, val) -> arr deve ser compativel com param[0]
                             if not self.types_compatible(expected_params[0], obj_type):
                                  # Se signature usa Any, passa.
                                  pass
                             
                             # Remove o primeiro parametro da lista de espera, pois 'self' já foi fornecido
                             expected_params.pop(0)

                # Valida quantidade de argumentos restantes
                # Exception: print accepts variable arguments
                if method_name != "print" and len(effective_args) != len(expected_params):
                    raise NoxyTypeError(
                        f"Função '{method_name}' espera {len(expected_params)} argumentos, "
                        f"recebeu {len(effective_args)}",
                        expr.location
                    )
                
                for arg, expected_type in zip(effective_args, expected_params):
                    arg_type = self.check_expression(arg)
                    if not self.types_compatible(expected_type, arg_type):
                        raise NoxyTypeError(
                            f"Argumento tem tipo errado: "
                            f"esperado '{type_to_str(expected_type)}', "
                            f"obtido '{type_to_str(arg_type)}'",
                            expr.location
                        )
                
                if not method_name == "print":
                    return ret_type
                
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
        
        if isinstance(obj_type, RefType):
            obj_type = obj_type.inner_type

        if isinstance(obj_type, ArrayType):
            if not isinstance(index_type, PrimitiveType) or index_type.name != "int":
                raise NoxyTypeError(f"Índice de array deve ser int, obtido '{type_to_str(index_type)}'", expr.location)
            return obj_type.element_type
        
        if isinstance(obj_type, PrimitiveType) and obj_type.name == "string":
            if not isinstance(index_type, PrimitiveType) or index_type.name != "int":
                raise NoxyTypeError(f"Índice de string deve ser int, obtido '{type_to_str(index_type)}'", expr.location)
            return PrimitiveType("string")

        if isinstance(obj_type, PrimitiveType) and obj_type.name == "bytes":
            if not isinstance(index_type, PrimitiveType) or index_type.name != "int":
                raise NoxyTypeError(f"Índice de bytes deve ser int, obtido '{type_to_str(index_type)}'", expr.location)
            return PrimitiveType("int")
            
        if isinstance(obj_type, MapType):
            if not types_equal(obj_type.key_type, index_type):
                raise NoxyTypeError(
                    f"Tipo da chave incorreto: esperado '{type_to_str(obj_type.key_type)}', "
                    f"obtido '{type_to_str(index_type)}'",
                    expr.location
                )
            return obj_type.value_type
        
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
            struct_def = None
            if obj_type.module:
                 # Procura no módulo
                 mod_type = self.lookup_var(obj_type.module)
                 if isinstance(mod_type, ModuleType):
                      if obj_type.name in mod_type.members:
                           cat, data = mod_type.members[obj_type.name]
                           if cat == "struct":
                                struct_def = data
            else:
                 struct_def = self.structs.get(obj_type.name)

            if struct_def is None:
                raise NoxyTypeError(
                    f"Struct '{obj_type.name}' não definido" + (f" no módulo '{obj_type.module}'" if obj_type.module else ""),
                    expr.location
                )
            for field in struct_def.fields:
                if field.name == expr.field_name:
                    return field.field_type
            raise NoxyTypeError(
                f"Struct '{obj_type.name}' não tem campo '{expr.field_name}'",
                expr.location
            )
        
        if isinstance(obj_type, ModuleType):
            if expr.field_name not in obj_type.members:
                 raise NoxyTypeError(f"Membro '{expr.field_name}' não encontrado no módulo '{obj_type.name}'", expr.location)
            category, data = obj_type.members[expr.field_name]
            if category == "var":
                return data # data is NoxyType
            if category == "func":
                # Retorna tipo função? Não temos. Retorna VOID? Erro?
                # Se estamos AVALIANDO o campo, e é função, e não chamando...
                # Noxy não suporta first-class functions.
                raise NoxyTypeError("Funções não podem ser usadas como valores", expr.location)
            if category == "struct":
                # Type?
                raise NoxyTypeError("Structs não podem ser usados como valores", expr.location)

        
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
    
    def check_map_literal(self, expr: MapLiteral) -> NoxyType:
        """Verifica literal de mapa."""
        if not expr.keys:
            # Mapa vazio - tipo será determinado pelo contexto ou default
            # Retorna MapType(void, void) que deve ser compatível com qualquer MapType
            return MapType(PrimitiveType("void"), PrimitiveType("void"))
            
        key_type = self.check_expression(expr.keys[0])
        val_type = self.check_expression(expr.values[0])
        
        # Verifica se todas as chaves e valores têm tipos compatíveis/iguais
        for i in range(1, len(expr.keys)):
            k_t = self.check_expression(expr.keys[i])
            v_t = self.check_expression(expr.values[i])
            
            if not self.types_compatible(key_type, k_t):
                raise NoxyTypeError(
                    f"Chaves do mapa têm tipos inconsistentes: "
                    f"esperado '{type_to_str(key_type)}', obtido '{type_to_str(k_t)}'",
                    expr.location
                )
            
            if not self.types_compatible(val_type, v_t):
                raise NoxyTypeError(
                    f"Valores do mapa têm tipos inconsistentes: "
                    f"esperado '{type_to_str(val_type)}', obtido '{type_to_str(v_t)}'",
                    expr.location
                )
                
        return MapType(key_type, val_type)

    def types_compatible(self, expected: NoxyType, actual: NoxyType) -> bool:
        """Verifica se tipos são compatíveis para atribuição."""
        if expected is Any or actual is Any:
            return True
            
        # null é compatível com qualquer tipo ref
        if isinstance(actual, RefType):
            if isinstance(actual.inner_type, PrimitiveType) and actual.inner_type.name == "void":
                return isinstance(expected, RefType)
        
        # Arrays
        if isinstance(expected, ArrayType) and isinstance(actual, ArrayType):
            # Array vazio (void[]) é compatível com qualquer array
            if isinstance(actual.element_type, PrimitiveType) and actual.element_type.name == "void":
                return True
            
            # Tipos de elementos devem ser iguais
            if not types_equal(expected.element_type, actual.element_type):
                return False
                
            # Se esperado tem tamanho fixo, atual deve ter mesmo tamanho?
            # Ou se esperado é dinâmico (None), aceita fixo?
            # Regra:
            # - Dinâmico <- Fixo: OK (Slice/Ref behavior)
            # - Dinâmico <- Dinâmico: OK
            # - Fixo <- Fixo: Tamanhos devem ser iguais
            # - Fixo <- Dinâmico: Erro (não seguro)
            
            if expected.size is None:
                return True
            
            if actual.size is None:
                # Permite atribuir array dinâmico a fixo (ex: retorno de zeros())
                # Isso relaxa a segurança, mas permite usar zeros(N) para inicializar arr[N]
                return True
                
            return expected.size == actual.size
        
        # Maps
        if isinstance(expected, MapType) and isinstance(actual, MapType):
            # Map vazio (void, void) é compatível com qualquer map
            if isinstance(actual.key_type, PrimitiveType) and actual.key_type.name == "void":
                return True
            
            return types_equal(expected.key_type, actual.key_type) and \
                   types_equal(expected.value_type, actual.value_type)
        
        # Structs
        if isinstance(expected, StructType) and isinstance(actual, StructType):
            return expected.name == actual.name
        
        return types_equal(expected, actual)


def check_types(program: Program, base_path: str = "."):
    """Função auxiliar para verificar tipos."""
    checker = TypeChecker(base_path)
    checker.check_program(program)


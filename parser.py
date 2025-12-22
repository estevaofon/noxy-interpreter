"""
Noxy Interpreter - Parser
Parser recursive descent que produz AST.
"""

from typing import Optional
from lexer import Token, TokenType, Lexer
from ast_nodes import (
    # Tipos
    NoxyType, PrimitiveType, ArrayType, StructType, RefType,
    # Expressões
    Expr, IntLiteral, FloatLiteral, StringLiteral, BytesLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, CallExpr, IndexExpr, FieldAccess,
    ArrayLiteral, RefExpr, FString, FStringExpr, ZerosExpr, GroupExpr,
    # Statements
    Stmt, LetStmt, GlobalStmt, AssignStmt, ExprStmt, IfStmt, WhileStmt,
    ReturnStmt, BreakStmt, FuncDef, FuncParam, StructDef, StructField, UseStmt,
    # Programa
    Program
)
from errors import NoxyParserError, SourceLocation


class Parser:
    """Parser recursive descent para Noxy."""
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
    
    @property
    def current(self) -> Token:
        """Token atual."""
        return self.tokens[self.pos]
    
    @property
    def previous(self) -> Token:
        """Token anterior."""
        return self.tokens[self.pos - 1] if self.pos > 0 else self.tokens[0]
    
    def peek(self, offset: int = 1) -> Token:
        """Olha tokens à frente."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]
    
    def is_at_end(self) -> bool:
        """Verifica se chegou ao fim."""
        return self.current.type == TokenType.EOF
    
    def check(self, *types: TokenType) -> bool:
        """Verifica se o token atual é um dos tipos."""
        return self.current.type in types
    
    def advance(self) -> Token:
        """Avança para o próximo token."""
        token = self.current
        if not self.is_at_end():
            self.pos += 1
        return token
    
    def match(self, *types: TokenType) -> bool:
        """Consome o token se for um dos tipos."""
        if self.check(*types):
            self.advance()
            return True
        return False
    
    def consume(self, type: TokenType, message: str) -> Token:
        """Consome um token específico ou lança erro."""
        if self.check(type):
            return self.advance()
        raise NoxyParserError(message, self.current.location)
    
    def skip_newlines(self):
        """Pula tokens de newline."""
        while self.match(TokenType.NEWLINE):
            pass
    
    def error(self, message: str) -> NoxyParserError:
        """Cria um erro de parser."""
        return NoxyParserError(message, self.current.location)
    
    # =========================================================================
    # TIPOS
    # =========================================================================
    
    def parse_type(self) -> NoxyType:
        """Parseia um tipo."""
        # ref Type
        if self.match(TokenType.REF):
            inner = self.parse_type()
            return RefType(inner)
        
        # Tipo primitivo
        if self.match(TokenType.TYPE_INT):
            base_type = PrimitiveType("int")
        elif self.match(TokenType.TYPE_FLOAT):
            base_type = PrimitiveType("float")
        elif self.match(TokenType.TYPE_STRING, TokenType.TYPE_STR):
            base_type = PrimitiveType("string")
        elif self.match(TokenType.TYPE_BOOL):
            base_type = PrimitiveType("bool")
        elif self.match(TokenType.TYPE_BYTES):
            base_type = PrimitiveType("bytes")
        elif self.match(TokenType.TYPE_VOID):
            base_type = PrimitiveType("void")
        elif self.check(TokenType.IDENTIFIER):
            # Tipo struct
            name = self.advance().value
            base_type = StructType(name)
        else:
            raise self.error(f"Tipo esperado, encontrado '{self.current.value}'")
        
        # Verifica se é array: Type[size] ou Type[]
        while self.match(TokenType.LBRACKET):
            if self.match(TokenType.RBRACKET):
                # Array sem tamanho (parâmetro)
                base_type = ArrayType(base_type, None)
            else:
                # Array com tamanho
                size_token = self.consume(TokenType.INT, "Tamanho do array esperado")
                self.consume(TokenType.RBRACKET, "']' esperado")
                base_type = ArrayType(base_type, size_token.value)
        
        return base_type
    
    # =========================================================================
    # EXPRESSÕES
    # =========================================================================
    
    def parse_expression(self) -> Expr:
        """Parseia uma expressão (entrada principal)."""
        return self.parse_or()
    
    def parse_or(self) -> Expr:
        """Parseia expressão OR: expr | expr."""
        left = self.parse_and()
        
        while self.match(TokenType.OR):
            loc = self.previous.location
            right = self.parse_and()
            left = BinaryOp(left, "|", right, loc)
        
        return left
    
    def parse_and(self) -> Expr:
        """Parseia expressão AND: expr & expr."""
        left = self.parse_not()
        
        while self.match(TokenType.AND):
            loc = self.previous.location
            right = self.parse_not()
            left = BinaryOp(left, "&", right, loc)
        
        return left
    
    def parse_not(self) -> Expr:
        """Parseia expressão NOT: !expr."""
        if self.match(TokenType.NOT):
            loc = self.previous.location
            operand = self.parse_not()
            return UnaryOp("!", operand, loc)
        return self.parse_comparison()
    
    def parse_comparison(self) -> Expr:
        """Parseia comparação: expr > expr, expr == expr, etc."""
        left = self.parse_additive()
        
        while self.check(TokenType.GT, TokenType.LT, TokenType.GTE, 
                         TokenType.LTE, TokenType.EQ, TokenType.NEQ):
            op = self.advance()
            loc = op.location
            right = self.parse_additive()
            left = BinaryOp(left, op.value, right, loc)
        
        return left
    
    def parse_additive(self) -> Expr:
        """Parseia adição/subtração: expr + expr, expr - expr."""
        left = self.parse_multiplicative()
        
        while self.check(TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            loc = op.location
            right = self.parse_multiplicative()
            left = BinaryOp(left, op.value, right, loc)
        
        return left
    
    def parse_multiplicative(self) -> Expr:
        """Parseia multiplicação/divisão: expr * expr, expr / expr, expr % expr."""
        left = self.parse_unary()
        
        while self.check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance()
            loc = op.location
            right = self.parse_unary()
            left = BinaryOp(left, op.value, right, loc)
        
        return left
    
    def parse_unary(self) -> Expr:
        """Parseia unário: -expr."""
        if self.match(TokenType.MINUS):
            loc = self.previous.location
            operand = self.parse_unary()
            return UnaryOp("-", operand, loc)
        return self.parse_postfix()
    
    def parse_postfix(self) -> Expr:
        """Parseia postfix: expr.field, expr[index], expr(args)."""
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.DOT):
                # Acesso a campo: expr.field
                # Permite keywords como nome de campo (ex: net.select, obj.type)
                if self.check(TokenType.IDENTIFIER):
                    field = self.consume(TokenType.IDENTIFIER, "Nome do campo esperado")
                    expr = FieldAccess(expr, field.value, location=field.location)
                elif self.check(TokenType.SELECT):
                    # Exceção para 'select'
                    tok = self.advance()
                    expr = FieldAccess(expr, "select", location=tok.location)
                elif self.check(TokenType.TYPE_INT, TokenType.TYPE_FLOAT, TokenType.TYPE_STRING, TokenType.TYPE_BOOL, TokenType.TYPE_BYTES):
                    # Exceção para tipos primitivos
                    tok = self.advance()
                    expr = FieldAccess(expr, tok.value, location=tok.location)
                else:
                    raise self.error("Nome do campo esperado")
            elif self.match(TokenType.LBRACKET):
                # Acesso a índice: expr[index]
                loc = self.previous.location
                index = self.parse_expression()
                self.consume(TokenType.RBRACKET, "']' esperado")
                expr = IndexExpr(expr, index, loc)
            elif self.match(TokenType.LPAREN):
                # Chamada de função: expr(args)
                loc = self.previous.location
                args = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        self.skip_newlines()
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN, "')' esperado")
                expr = CallExpr(expr, args, loc)
            else:
                break
        
        return expr
    
    def parse_primary(self) -> Expr:
        """Parseia expressão primária."""
        loc = self.current.location
        
        # Literais
        if self.match(TokenType.INT):
            return IntLiteral(self.previous.value, loc)
        
        if self.match(TokenType.FLOAT):
            return FloatLiteral(self.previous.value, loc)
        
        if self.match(TokenType.STRING):
            return StringLiteral(self.previous.value, loc)

        if self.match(TokenType.BYTES):
            return BytesLiteral(self.previous.value, loc)
        
        if self.match(TokenType.TRUE):
            return BoolLiteral(True, loc)
        
        if self.match(TokenType.FALSE):
            return BoolLiteral(False, loc)
        
        if self.match(TokenType.NULL):
            return NullLiteral(loc)
        
        # F-string
        if self.match(TokenType.FSTRING):
            return self.parse_fstring_parts(self.previous.value, loc)
        
        # zeros(n)
        if self.match(TokenType.ZEROS):
            self.consume(TokenType.LPAREN, "'(' esperado após 'zeros'")
            size = self.parse_expression()
            self.consume(TokenType.RPAREN, "')' esperado")
            return ZerosExpr(size, loc)
        
        # ref expr
        if self.match(TokenType.REF):
            value = self.parse_postfix()
            return RefExpr(value, loc)
        
        # Array literal: [expr, expr, ...]
        if self.match(TokenType.LBRACKET):
            elements = []
            self.skip_newlines()
            if not self.check(TokenType.RBRACKET):
                elements.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    self.skip_newlines()
                    if self.check(TokenType.RBRACKET):
                        break
                    elements.append(self.parse_expression())
            self.skip_newlines()
            self.consume(TokenType.RBRACKET, "']' esperado")
            return ArrayLiteral(elements, loc)
        
        # Expressão entre parênteses
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN, "')' esperado")
            return GroupExpr(expr, loc)
        
        # Identificador
        if self.match(TokenType.IDENTIFIER):
            return Identifier(self.previous.value, loc)
            
        if self.match(TokenType.SELECT):
            return Identifier("select", loc)
        
        raise self.error(f"Expressão esperada, encontrado '{self.current.value}'")
    
    def parse_fstring_parts(self, parts: list, loc: SourceLocation) -> FString:
        """Parseia as partes de uma f-string."""
        result_parts = []
        
        for part in parts:
            if part[0] == "text":
                result_parts.append(part[1])
            elif part[0] == "expr":
                # Parseia a expressão dentro da interpolação
                expr_str = part[1]
                format_spec = part[2] if len(part) > 2 else None
                
                # Tokeniza e parseia a expressão
                from lexer import Lexer
                lexer = Lexer(expr_str)
                tokens = lexer.tokenize()
                parser = Parser(tokens)
                expr = parser.parse_expression()
                
                result_parts.append(FStringExpr(expr, format_spec))
        
        return FString(result_parts, loc)
    
    # =========================================================================
    # STATEMENTS
    # =========================================================================
    
    def parse_statement(self) -> Optional[Stmt]:
        """Parseia um statement."""
        self.skip_newlines()
        
        if self.is_at_end():
            return None
        
        loc = self.current.location
        
        # let
        if self.match(TokenType.LET):
            return self.parse_let_stmt(loc)
        
        # global
        if self.match(TokenType.GLOBAL):
            return self.parse_global_stmt(loc)
        
        # func
        if self.match(TokenType.FUNC):
            return self.parse_func_def(loc)
        
        # struct
        if self.match(TokenType.STRUCT):
            return self.parse_struct_def(loc)
        
        # if
        if self.match(TokenType.IF):
            return self.parse_if_stmt(loc)
        
        # while
        if self.match(TokenType.WHILE):
            return self.parse_while_stmt(loc)
        
        # return
        if self.match(TokenType.RETURN):
            return self.parse_return_stmt(loc)
        
        # break
        if self.match(TokenType.BREAK):
            return BreakStmt(loc)
        
        # use
        if self.match(TokenType.USE):
            return self.parse_use_stmt(loc)
        
        # Atribuição ou expressão
        return self.parse_assignment_or_expr(loc)
    
    def parse_let_stmt(self, loc: SourceLocation) -> LetStmt:
        """Parseia: let name: type = expr."""
        name = self.consume(TokenType.IDENTIFIER, "Nome da variável esperado").value
        self.consume(TokenType.COLON, "':' esperado")
        var_type = self.parse_type()
        self.consume(TokenType.ASSIGN, "'=' esperado")
        initializer = self.parse_expression()
        return LetStmt(name, var_type, initializer, loc)
    
    def parse_global_stmt(self, loc: SourceLocation) -> GlobalStmt:
        """Parseia: global name: type = expr."""
        name = self.consume(TokenType.IDENTIFIER, "Nome da variável esperado").value
        self.consume(TokenType.COLON, "':' esperado")
        var_type = self.parse_type()
        self.consume(TokenType.ASSIGN, "'=' esperado")
        initializer = self.parse_expression()
        return GlobalStmt(name, var_type, initializer, loc)
    
    def parse_func_def(self, loc: SourceLocation) -> FuncDef:
        """Parseia definição de função."""
        # Permite keywords como nome de função (ex: select)
        if self.check(TokenType.IDENTIFIER):
             name = self.consume(TokenType.IDENTIFIER, "Nome da função esperado").value
        elif self.check(TokenType.SELECT):
             tok = self.advance()
             name = "select"
        else:
             raise self.error("Nome da função esperado")
             
        self.consume(TokenType.LPAREN, "'(' esperado")
        
        # Parâmetros
        params = []
        if not self.check(TokenType.RPAREN):
            params.append(self.parse_param())
            while self.match(TokenType.COMMA):
                params.append(self.parse_param())
        self.consume(TokenType.RPAREN, "')' esperado")
        
        # Tipo de retorno
        return_type = PrimitiveType("void")
        if self.match(TokenType.ARROW):
            return_type = self.parse_type()
        
        # Corpo
        self.skip_newlines()
        body = []
        while not self.check(TokenType.END) and not self.is_at_end():
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        
        self.consume(TokenType.END, "'end' esperado")
        return FuncDef(name, params, return_type, body, loc)
    
    def parse_param(self) -> FuncParam:
        """Parseia um parâmetro de função."""
        name = self.consume(TokenType.IDENTIFIER, "Nome do parâmetro esperado").value
        self.consume(TokenType.COLON, "':' esperado")
        param_type = self.parse_type()
        return FuncParam(name, param_type)
    
    def parse_struct_def(self, loc: SourceLocation) -> StructDef:
        """Parseia definição de struct."""
        name = self.consume(TokenType.IDENTIFIER, "Nome do struct esperado").value
        self.skip_newlines()
        
        fields = []
        while not self.check(TokenType.END) and not self.is_at_end():
            field = self.parse_struct_field()
            if field:
                fields.append(field)
            else:
                # Se não é campo e não é END (verificado no loop), é erro ou travamento
                raise self.error(f"Esperado campo de struct ou 'end', encontrado '{self.current.value}'")
            self.skip_newlines()
        
        self.consume(TokenType.END, "'end' esperado")
        return StructDef(name, fields, loc)
    
    def parse_struct_field(self) -> Optional[StructField]:
        """Parseia um campo de struct."""
        if not self.check(TokenType.IDENTIFIER):
            return None
        
        name = self.advance().value
        self.consume(TokenType.COLON, "':' esperado")
        field_type = self.parse_type()
        self.match(TokenType.COMMA)  # Vírgula opcional
        return StructField(name, field_type)
    
    def parse_if_stmt(self, loc: SourceLocation) -> IfStmt:
        """Parseia: if cond then ... [else ...] end."""
        condition = self.parse_expression()
        self.consume(TokenType.THEN, "'then' esperado")
        self.skip_newlines()
        
        then_body = []
        while not self.check(TokenType.ELSE, TokenType.END) and not self.is_at_end():
            stmt = self.parse_statement()
            if stmt:
                then_body.append(stmt)
            self.skip_newlines()
        
        else_body = []
        if self.match(TokenType.ELSE):
            self.skip_newlines()
            while not self.check(TokenType.END) and not self.is_at_end():
                stmt = self.parse_statement()
                if stmt:
                    else_body.append(stmt)
                self.skip_newlines()
        
        self.consume(TokenType.END, "'end' esperado")
        return IfStmt(condition, then_body, else_body, loc)
    
    def parse_while_stmt(self, loc: SourceLocation) -> WhileStmt:
        """Parseia: while cond do ... end."""
        condition = self.parse_expression()
        self.consume(TokenType.DO, "'do' esperado")
        self.skip_newlines()
        
        body = []
        while not self.check(TokenType.END) and not self.is_at_end():
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        
        self.consume(TokenType.END, "'end' esperado")
        return WhileStmt(condition, body, loc)
    
    def parse_return_stmt(self, loc: SourceLocation) -> ReturnStmt:
        """Parseia: return [expr]."""
        value = None
        if not self.check(TokenType.NEWLINE, TokenType.END, TokenType.EOF):
            value = self.parse_expression()
        return ReturnStmt(value, loc)
    
    def parse_use_stmt(self, loc: SourceLocation) -> UseStmt:
        """Parseia: use module.path [select sym1, sym2]."""
        module_path = [self.consume(TokenType.IDENTIFIER, "Nome do módulo esperado").value]
        while self.match(TokenType.DOT):
            module_path.append(self.consume(TokenType.IDENTIFIER, "Nome do módulo esperado").value)
        
        imports = []
        if self.match(TokenType.SELECT):
            if self.match(TokenType.STAR):
                imports = ["*"]
            else:
                imports.append(self.consume(TokenType.IDENTIFIER, "Nome do símbolo esperado").value)
                while self.match(TokenType.COMMA):
                    imports.append(self.consume(TokenType.IDENTIFIER, "Nome do símbolo esperado").value)
        else:
            # Se não tem select, importa o nome do módulo (ex: use io -> import io)
            # Assume que o módulo exporta um símbolo com o mesmo nome
            module_name = module_path[-1]
            imports = [module_name]
        
        return UseStmt(module_path, imports, loc)
    
    def parse_assignment_or_expr(self, loc: SourceLocation) -> Stmt:
        """Parseia atribuição ou expressão."""
        expr = self.parse_expression()
        
        # Verifica se é atribuição
        if self.match(TokenType.ASSIGN):
            value = self.parse_expression()
            return AssignStmt(expr, value, loc)
        
        return ExprStmt(expr, loc)
    
    # =========================================================================
    # PROGRAMA
    # =========================================================================
    
    def parse(self) -> Program:
        """Parseia o programa completo."""
        statements = []
        
        while not self.is_at_end():
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        return Program(statements)


def parse(source: str, filename: str = "<stdin>") -> Program:
    """Função auxiliar para parsear código."""
    from lexer import tokenize
    tokens = tokenize(source, filename)
    parser = Parser(tokens)
    return parser.parse()


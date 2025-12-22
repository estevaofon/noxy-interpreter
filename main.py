"""
Noxy Interpreter - CLI Principal
Executa programas .nx via linha de comando.

Uso: uv run main.py arquivo.nx [--no-typecheck] [--debug]
"""

import sys
import argparse
from pathlib import Path

from lexer import tokenize
from parser import Parser
from noxy_types import check_types
from interpreter import Interpreter
from errors import NoxyError


def run_file(filepath: str, typecheck: bool = True, debug: bool = False):
    """Executa um arquivo Noxy."""
    path = Path(filepath).resolve()
    
    if not path.exists():
        print(f"Erro: Arquivo não encontrado: {filepath}", file=sys.stderr)
        sys.exit(1)
    
    if not path.suffix == ".nx":
        print(f"Aviso: Arquivo não tem extensão .nx: {filepath}", file=sys.stderr)
    
    source = path.read_text(encoding="utf-8")
    run_source(source, str(path), typecheck, debug, base_path=str(path.parent))


def run_source(source: str, filename: str = "<stdin>", typecheck: bool = True, debug: bool = False, base_path: str = "."):
    """Executa código fonte Noxy."""
    try:
        # Fase 1: Tokenização
        if debug:
            print("=== Tokenização ===")
        tokens = tokenize(source, filename)
        if debug:
            for token in tokens:
                print(f"  {token}")
            print()
        
        # Fase 2: Parsing
        if debug:
            print("=== Parsing ===")
        parser = Parser(tokens)
        program = parser.parse()
        if debug:
            print(f"  {len(program.statements)} statements")
            print()
        
        # Fase 3: Verificação de tipos (opcional)
        if typecheck:
            if debug:
                print("=== Type Checking ===")
            check_types(program, base_path=base_path)
            if debug:
                print("  OK")
                print()
        
        # Fase 4: Interpretação
        if debug:
            print("=== Execução ===")
        interpreter = Interpreter(base_path=base_path)
        interpreter.run(program)
        
    except NoxyError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro interno: {e}", file=sys.stderr)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_repl():
    """Executa REPL interativo."""
    from ast_nodes import StructDef, FuncDef, UseStmt
    
    print("Noxy Interpreter v0.1.0")
    print("Digite 'exit' ou Ctrl+C para sair.")
    print()
    
    interpreter = Interpreter()
    buffer = []
    
    while True:
        try:
            prompt = "... " if buffer else ">>> "
            line = input(prompt)
            
            if line.strip() == "exit":
                break
            
            buffer.append(line)
            source = "\n".join(buffer)
            
            # Tenta executar
            try:
                tokens = tokenize(source)
                parser = Parser(tokens)
                program = parser.parse()
                
                # Primeiro: processa imports
                for stmt in program.statements:
                    if isinstance(stmt, UseStmt):
                        interpreter.execute_use(stmt)
                
                # Segundo: registra structs e funções
                for stmt in program.statements:
                    if isinstance(stmt, StructDef):
                        interpreter.global_env.define_struct(stmt)
                    elif isinstance(stmt, FuncDef):
                        interpreter.global_env.define_function(stmt)
                
                # Terceiro: executa os outros statements
                for stmt in program.statements:
                    if not isinstance(stmt, (StructDef, FuncDef, UseStmt)):
                        interpreter.execute(stmt)
                
                buffer = []
            except NoxyError as e:
                # Se o erro indica código incompleto, continua lendo
                if "esperado" in str(e).lower() and ("end" in str(e) or "'" in str(e)):
                    continue
                print(f"Erro: {e}")
                buffer = []
            
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except EOFError:
            break


def main():
    """Ponto de entrada principal."""
    # Configura encoding para UTF-8 no stdout/stderr (importante para Windows)
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
            
    if sys.stderr.encoding.lower() != 'utf-8':
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

    parser = argparse.ArgumentParser(
        description="Interpretador Noxy - Linguagem de programação estaticamente tipada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  uv run main.py programa.nx          # Executa um programa
  uv run main.py programa.nx --debug  # Executa com debug
  uv run main.py                      # Inicia REPL interativo
        """
    )
    
    parser.add_argument(
        "file",
        nargs="?",
        help="Arquivo .nx para executar (opcional - sem arquivo inicia REPL)"
    )
    
    parser.add_argument(
        "--no-typecheck",
        action="store_true",
        help="Desabilita verificação de tipos"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostra informações de debug"
    )
    
    args = parser.parse_args()
    
    if args.file:
        run_file(args.file, typecheck=not args.no_typecheck, debug=args.debug)
    else:
        run_repl()


if __name__ == "__main__":
    main()


import sys
from pathlib import Path

# Add current directory to sys.path
sys.path.append(str(Path(".").resolve()))

from lexer import tokenize
from parser import Parser
from interpreter import Interpreter
from ast_nodes import StringLiteral, Stmt, UseStmt, StructDef, FuncDef, VarDecl

def check_globals():
    interpreter = Interpreter(base_path=".")
    
    filepath = Path("noxy_examples/web_app.nx")
    print(f"Loading {filepath}...")
    source = filepath.read_text(encoding="utf-8")
    
    tokens = tokenize(source, str(filepath))
    parser = Parser(tokens)
    program = parser.parse()
    
    # Simulate server.py loading logic
    print("Simulating server.py loading...")
    for stmt in program.statements:
        if isinstance(stmt, UseStmt):
            interpreter.execute_use(stmt)
            
    for stmt in program.statements:
        if isinstance(stmt, StructDef):
            interpreter.global_env.define_struct(stmt)
        elif isinstance(stmt, FuncDef):
            interpreter.global_env.define_function(stmt)
            
    # Now check if TYPE_NUMBER exists
    if interpreter.global_env.exists("TYPE_NUMBER"):
        val = interpreter.global_env.get("TYPE_NUMBER")
        print(f"SUCCESS: TYPE_NUMBER is defined as {val}")
    else:
        print("FAILURE: TYPE_NUMBER is NOT defined!")
        
        # Check if we missed VarDecl
        print("Checking what statements were skipped:")
        for stmt in program.statements:
            if not isinstance(stmt, (UseStmt, StructDef, FuncDef)):
                print(f"Skipped stmt type: {type(stmt).__name__}")

if __name__ == "__main__":
    try:
        check_globals()
    except Exception as e:
        print(f"Error: {e}")

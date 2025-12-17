import sys
from pathlib import Path
from flask import Flask, request, Response

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Add current directory to sys.path to import interpreter modules
#sys.path.append(str(Path(__file__).parent))

from lexer import tokenize
from parser import Parser
from interpreter import Interpreter
from ast_nodes import StringLiteral, Stmt, UseStmt, StructDef, FuncDef, GlobalStmt
import noxy_builtins

app = Flask(__name__)

# Global interpreter instance
interpreter = None

# Custom print to capture output
captured_output = []

def custom_print(*args):
    """Captures print output from Noxy."""
    output = []
    for arg in args:
        output.append(noxy_builtins.value_to_string(arg))
    line = " ".join(output)
    captured_output.append(line)
    # Also print to real stdout for debugging
    print(f"[NOXY] {line}")

# Redirect builtin print
noxy_builtins.BUILTINS["print"] = custom_print

def init_interpreter():
    global interpreter
    app_dir = Path(__file__).parent
    interpreter = Interpreter(base_path=str(app_dir))
    
    # Load the web app source
    filepath = app_dir / "app.nx"
    print(f"Loading {filepath}...")
    source = filepath.read_text(encoding="utf-8")
    
    # Parse
    tokens = tokenize(source, str(filepath))
    parser = Parser(tokens)
    program = parser.parse()
    
    # Initialize environment (process imports, structs, functions)
    # We do NOT run the top-level statements that are tests/examples
    # We only want to register definitions
    
    # Phase 1: Imports
    for stmt in program.statements:
        if isinstance(stmt, UseStmt):
            interpreter.execute_use(stmt)
            
    # Phase 2: Structs and Funcs
    for stmt in program.statements:
        if isinstance(stmt, StructDef):
            interpreter.global_env.define_struct(stmt)
        elif isinstance(stmt, FuncDef):
            interpreter.global_env.define_function(stmt)
    
    # Phase 3: Global variables (need to execute them to initialize values)
    for stmt in program.statements:
        if isinstance(stmt, GlobalStmt):
            interpreter.execute(stmt)

    print("Noxy Interpreter initialized successfully.")

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all(path):
    # Construct JSON request payload for Noxy
    path_fixed = f"/{path}"
    method = request.method
    
    # Parse body if JSON
    body_json = "null"
    if request.is_json:
        import json
        body_json = json.dumps(request.json)
    elif request.data:
        pass
        
    full_json_request = f'{{"method": "{method}", "path": "{path_fixed}", "body": {body_json}}}'
    
    print(f"Incoming Request: {full_json_request}")
    
    # Prepare arguments for Noxy function call
    arg_expr = StringLiteral(full_json_request)
    
    # Find function
    func_name = "handle_request"
    func_def = interpreter.global_env.get_function(func_name)
    
    if not func_def:
        return Response("Error: handle_request function not found in Noxy code.", status=500)
    
    try:
        # Execute - now returns a Response struct
        result = interpreter.call_function(func_def, [arg_expr])
        
        # Import NoxyStruct to check type
        from environment import NoxyStruct
        
        if isinstance(result, NoxyStruct) and result.type_name == "Response":
            # Extract fields from Response struct
            status_code = result.fields.get("status", 200)
            content_type = result.fields.get("content_type", "text/plain")
            body = result.fields.get("body", "")
            
            headers = {"Content-Type": content_type}
            return Response(body, status=status_code, headers=headers)
        else:
            # Fallback: return raw result as string
            return Response(str(result), status=200)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(f"Internal Noxy Error: {str(e)}", status=500)

if __name__ == '__main__':
    init_interpreter()
    app.run(debug=True, port=8000)

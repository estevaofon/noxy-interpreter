from typing import Any
from ast_nodes import PrimitiveType, ArrayType, StructType, RefType

# ============================================================================
# BUILTIN SIGNATURES (Type Checking)
# ============================================================================

BUILTIN_SIGNATURES = {
    "print": (None, [Any]), # Varargs treated specially
    "to_str": (PrimitiveType("string"), [Any]),
    "to_int": (PrimitiveType("int"), [Any]),
    "to_int": (PrimitiveType("int"), [Any]),
    "to_float": (PrimitiveType("float"), [Any]),
    "to_bytes": (PrimitiveType("bytes"), [Any]),
    "strlen": (PrimitiveType("int"), [PrimitiveType("string")]),
    "ord": (PrimitiveType("int"), [PrimitiveType("string")]),
    "length": (PrimitiveType("int"), [Any]),
    "zeros": (ArrayType(PrimitiveType("int"), None), [PrimitiveType("int")]),
    
    # IO Functions (mapped from io.func)
    "io_open": (StructType("File"), [PrimitiveType("string"), PrimitiveType("string")]),
    "io_close": (PrimitiveType("void"), [StructType("File")]),
    "io_read": (StructType("IOResult"), [StructType("File")]),
    "io_read_line": (StructType("IOResult"), [StructType("File")]),
    "io_read_lines": (StructType("IOResult"), [StructType("File")]), 
    "io_write": (PrimitiveType("void"), [StructType("File"), PrimitiveType("string")]),
    "io_exists": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "io_stat": (StructType("FileInfo"), [PrimitiveType("string")]),
    "io_remove": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "io_rename": (PrimitiveType("bool"), [PrimitiveType("string"), PrimitiveType("string")]),
    "io_mkdir": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "io_mkdir": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "io_list_dir": (StructType("IOResult"), [PrimitiveType("string")]),

    # Net Functions (mapped from net.func)
    "net_listen": (StructType("Socket"), [PrimitiveType("string"), PrimitiveType("int")]),
    "net_accept": (StructType("Socket"), [StructType("Socket")]),
    "net_connect": (StructType("Socket"), [PrimitiveType("string"), PrimitiveType("int")]),
    "net_recv": (StructType("NetResult"), [StructType("Socket"), Any]), # Any for optional size? No, builtins are strict. Let's make size optional or overload logic not supported. Interpreter passes all args to python. Python params have default. But TypeChecker needs to know.
    # We will enforce explicit size or use Any and handle in builtins or check manually.
    # In stdlib net wrapper we can set default.
    # Let's say recv takes socket. Size? net_recv has default.
    # But type checker validates against this signature. 
    # If we want optional args support in typechecker, we need to implement it.
    # For now, let's assume valid calls from stdlib will provide size or we relax here.
    # Let's demand size (int).
    "net_recv": (StructType("NetResult"), [StructType("Socket"), PrimitiveType("int")]),
    "net_send": (StructType("NetResult"), [StructType("Socket"), Any]), # bytes or string
    "net_close": (PrimitiveType("void"), [StructType("Socket")]),
}

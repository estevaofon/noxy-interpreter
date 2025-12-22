from typing import Any
from ast_nodes import PrimitiveType, ArrayType, StructType, RefType

# ============================================================================
# BUILTIN SIGNATURES (Type Checking)
# ============================================================================

BUILTIN_SIGNATURES = {
    "print": (None, [Any]), # Varargs treated specially
    "to_str": (PrimitiveType("string"), [Any]),
    "to_int": (PrimitiveType("int"), [Any]),
    "to_float": (PrimitiveType("float"), [Any]),
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
    "io_list_dir": (StructType("IOResult"), [PrimitiveType("string")]),
}

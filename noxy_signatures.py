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
    "ord": (PrimitiveType("int"), [PrimitiveType("string")]),
    "substring": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int"), PrimitiveType("int")]),
    "slice": (PrimitiveType("bytes"), [PrimitiveType("bytes"), PrimitiveType("int"), PrimitiveType("int")]),
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
    "net_setblocking": (PrimitiveType("void"), [StructType("Socket"), PrimitiveType("bool")]),
    "net_socket_set": (ArrayType(StructType("Socket"), 64), []),
    "net_select": (StructType("SelectResult"), [ArrayType(StructType("Socket"), 64), ArrayType(StructType("Socket"), 64), ArrayType(StructType("Socket"), 64), PrimitiveType("int")]),
    
    # Array Utils
    "remove": (PrimitiveType("void"), [Any, Any]), # array, item
    
    # New Array/Map Functions
    "append": (PrimitiveType("void"), [Any, Any]),
    "pop": (Any, [Any]),
    "keys": (ArrayType(Any, None), [Any]),
    "has_key": (PrimitiveType("bool"), [Any, Any]),
    "delete": (PrimitiveType("void"), [Any, Any]),
    "contains": (PrimitiveType("bool"), [Any, Any]),

    # Sys Functions
    "sys_exec": (StructType("SysResult"), [PrimitiveType("string")]),
    "sys_exec_output": (StructType("SysResult"), [PrimitiveType("string")]),
    "sys_getenv": (StructType("EnvResult"), [PrimitiveType("string")]),
    "sys_setenv": (PrimitiveType("bool"), [PrimitiveType("string"), PrimitiveType("string")]),
    "sys_getcwd": (PrimitiveType("string"), []),
    "sys_chdir": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "sys_exit": (PrimitiveType("void"), [PrimitiveType("int")]),
    "sys_argv": (ArrayType(PrimitiveType("string"), 100), []),
    "sys_sleep": (PrimitiveType("void"), [PrimitiveType("int")]),

    # Strings Functions
    "strings_contains": (PrimitiveType("bool"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_starts_with": (PrimitiveType("bool"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_ends_with": (PrimitiveType("bool"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_index_of": (PrimitiveType("int"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_last_index_of": (PrimitiveType("int"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_count": (PrimitiveType("int"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_to_upper": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_to_lower": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_trim": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_trim_left": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_trim_right": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_reverse": (PrimitiveType("string"), [PrimitiveType("string")]),
    "strings_repeat": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int")]),
    "strings_substring": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int"), PrimitiveType("int")]),
    "strings_replace": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("string"), PrimitiveType("string")]),
    "strings_replace_first": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("string"), PrimitiveType("string")]),
    "strings_pad_left": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int"), PrimitiveType("string")]),
    "strings_pad_right": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int"), PrimitiveType("string")]),
    "strings_split": (StructType("SplitResult"), [PrimitiveType("string"), PrimitiveType("string")]),
    "strings_join": (PrimitiveType("string"), [ArrayType(PrimitiveType("string"), None), PrimitiveType("string")]),
    "strings_join_count": (PrimitiveType("string"), [ArrayType(PrimitiveType("string"), None), PrimitiveType("string"), PrimitiveType("int")]),
    "strings_is_empty": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "strings_is_digit": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "strings_is_alpha": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "strings_is_alnum": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "strings_is_space": (PrimitiveType("bool"), [PrimitiveType("string")]),
    "strings_char_at": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int")]),
    "strings_char_at": (PrimitiveType("string"), [PrimitiveType("string"), PrimitiveType("int")]),
    "strings_from_char_code": (PrimitiveType("string"), [PrimitiveType("int")]),

    # SQLite Functions
    "sqlite_open": (StructType("Database"), [PrimitiveType("string")]),
    "sqlite_close": (PrimitiveType("void"), [StructType("Database")]),
    "sqlite_exec": (StructType("ExecResult"), [StructType("Database"), PrimitiveType("string")]),
    "sqlite_query": (StructType("QueryResult"), [StructType("Database"), PrimitiveType("string")]),
    "sqlite_prepare": (StructType("Statement"), [StructType("Database"), PrimitiveType("string")]),
    "sqlite_bind_int": (PrimitiveType("void"), [StructType("Statement"), PrimitiveType("int"), PrimitiveType("int")]),
    "sqlite_bind_float": (PrimitiveType("void"), [StructType("Statement"), PrimitiveType("int"), PrimitiveType("float")]),
    "sqlite_bind_text": (PrimitiveType("void"), [StructType("Statement"), PrimitiveType("int"), PrimitiveType("string")]),
    "sqlite_bind_null": (PrimitiveType("void"), [StructType("Statement"), PrimitiveType("int")]),
    "sqlite_step_exec": (StructType("ExecResult"), [StructType("Statement")]),
    "sqlite_step_query": (StructType("QueryResult"), [StructType("Statement")]),
    "sqlite_reset": (PrimitiveType("void"), [StructType("Statement")]),
    "sqlite_finalize": (PrimitiveType("void"), [StructType("Statement")]),
    "sqlite_begin": (PrimitiveType("bool"), [StructType("Database")]),
    "sqlite_commit": (PrimitiveType("bool"), [StructType("Database")]),
    "sqlite_rollback": (PrimitiveType("bool"), [StructType("Database")]),
    "sqlite_table_exists": (PrimitiveType("bool"), [StructType("Database"), PrimitiveType("string")]),
    "sqlite_escape": (PrimitiveType("string"), [PrimitiveType("string")]),

    # Time Functions
    "time_now": (PrimitiveType("int"), []),
    "time_now_datetime": (StructType("DateTime"), []),
    "time_now_ms": (PrimitiveType("int"), []),
    "time_from_timestamp": (StructType("DateTime"), [PrimitiveType("int")]),
    "time_to_timestamp": (PrimitiveType("int"), [StructType("DateTime")]),
    "time_make_datetime": (StructType("DateTime"), [PrimitiveType("int"), PrimitiveType("int"), PrimitiveType("int"), PrimitiveType("int"), PrimitiveType("int"), PrimitiveType("int")]),
    "time_format": (PrimitiveType("string"), [StructType("DateTime")]),
    "time_format_custom": (PrimitiveType("string"), [StructType("DateTime"), PrimitiveType("string")]),
    "time_format_date": (PrimitiveType("string"), [StructType("DateTime")]),
    "time_format_time": (PrimitiveType("string"), [StructType("DateTime")]),
    "time_parse": (StructType("DateTime"), [PrimitiveType("string")]),
    "time_parse_date": (StructType("DateTime"), [PrimitiveType("string")]),
    "time_add_seconds": (PrimitiveType("int"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_add_days": (PrimitiveType("int"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_diff": (PrimitiveType("int"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_diff_duration": (StructType("Duration"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_before": (PrimitiveType("bool"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_after": (PrimitiveType("bool"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_is_leap_year": (PrimitiveType("bool"), [PrimitiveType("int")]),
    "time_days_in_month": (PrimitiveType("int"), [PrimitiveType("int"), PrimitiveType("int")]),
    "time_weekday_name": (PrimitiveType("string"), [PrimitiveType("int")]),
    "time_month_name": (PrimitiveType("string"), [PrimitiveType("int")]),

}

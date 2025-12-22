"""
Noxy Interpreter - Funções Builtin
Implementação das funções nativas do Noxy.
"""

from typing import Any, Callable
from environment import NoxyStruct, NoxyRef, NoxyArray
from errors import NoxyRuntimeError
from ast_nodes import PrimitiveType, ArrayType, StructType, RefType
import os
import shutil


def noxy_print(*args) -> None:
    """Imprime valores no console."""
    output = []
    for arg in args:
        output.append(value_to_string(arg))
    print(" ".join(output))


def noxy_to_str(value: Any) -> str:
    """Converte qualquer valor para string."""
    return value_to_string(value)


def noxy_to_int(value: Any) -> int:
    """Converte float para int (trunca)."""
    if isinstance(value, float):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise NoxyRuntimeError(f"Não é possível converter '{value}' para int")
    raise NoxyRuntimeError(f"Não é possível converter {type(value).__name__} para int")


def noxy_to_float(value: Any) -> float:
    """Converte int para float."""
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise NoxyRuntimeError(f"Não é possível converter '{value}' para float")
    raise NoxyRuntimeError(f"Não é possível converter {type(value).__name__} para float")


def noxy_strlen(s: str) -> int:
    """Retorna o tamanho da string."""
    if not isinstance(s, str):
        raise NoxyRuntimeError(f"strlen() espera string, recebeu {type(s).__name__}")
    return len(s)


def noxy_ord(char: str) -> int:
    """Retorna o valor Unicode do caractere."""
    if not isinstance(char, str):
        raise NoxyRuntimeError(f"ord() espera string, recebeu {type(char).__name__}")
    if len(char) != 1:
        raise NoxyRuntimeError(f"ord() espera string de 1 caractere, recebeu '{char}'")
    return ord(char)


def noxy_length(arr: Any) -> int:
    """Retorna o tamanho do array."""
    if isinstance(arr, list):
        return len(arr)
    if isinstance(arr, NoxyArray):
        return len(arr)
    raise NoxyRuntimeError(f"length() espera array, recebeu {type(arr).__name__}")


MAX_ARRAY_SIZE = 100000  # Limite máximo de elementos

def noxy_zeros(n: int) -> list:
    """Cria um array de n zeros."""
    if not isinstance(n, int):
        raise NoxyRuntimeError(f"zeros() espera int, recebeu {type(n).__name__}")
    if n < 0:
        raise NoxyRuntimeError(f"zeros() não aceita tamanho negativo: {n}")
    if n > MAX_ARRAY_SIZE:
        raise NoxyRuntimeError(f"zeros() tamanho máximo é {MAX_ARRAY_SIZE}, solicitado: {n}")
    return [0] * n


def value_to_string(value: Any) -> str:
    """Converte um valor Noxy para string."""
    if value is None:
        return "null"
    
    if isinstance(value, bool):
        return "true" if value else "false"
    
    if isinstance(value, int):
        return str(value)
    
    if isinstance(value, float):
        # Formato padrão para floats
        return f"{value:f}"
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, list):
        elements = ", ".join(value_to_string(e) for e in value)
        return f"[{elements}]"
    
    if isinstance(value, NoxyArray):
        elements = ", ".join(value_to_string(e) for e in value.elements)
        return f"[{elements}]"
    
    if isinstance(value, NoxyStruct):
        fields = ", ".join(f"{k}: {value_to_string(v)}" for k, v in value.fields.items())
        return f"{value.type_name}({fields})"
    
    if isinstance(value, NoxyRef):
        if value.target is None and value.target_obj is None:
            return "null"
        return value_to_string(value.get_value())
    
    return str(value)


def format_value(value: Any, format_spec: str = None) -> str:
    """Formata um valor de acordo com o format spec."""
    if format_spec is None:
        return value_to_string(value)
    
    # Parse format spec: [width][.precision][type]
    # Exemplos: "5", "05", ".2f", ".2e", "x", "X", "o"
    
    if isinstance(value, int):
        # Formatos inteiros
        if format_spec == "x":
            return format(value, "x")
        elif format_spec == "X":
            return format(value, "X")
        elif format_spec == "o":
            return format(value, "o")
        elif format_spec.isdigit():
            width = int(format_spec)
            return f"{value:>{width}}"
        elif format_spec.startswith("0") and format_spec[1:].isdigit():
            width = int(format_spec[1:])
            return f"{value:0>{width}}"
        else:
            try:
                return format(value, format_spec)
            except ValueError:
                return str(value)
    
    elif isinstance(value, float):
        # Formatos float
        try:
            return format(value, format_spec)
        except ValueError:
            return str(value)
    
    else:
        # Outros tipos
        return value_to_string(value)



# ============================================================================
# IO MODULE BUILTINS
# ============================================================================

# Tabela de descritores de arquivo: fd -> file object
open_files: dict[int, Any] = {}
next_fd: int = 3  # 0, 1, 2 reservados (stdin, stdout, stderr)

def io_open(path: str, mode: str) -> NoxyStruct:
    """Abre um arquivo e retorna um struct File."""
    global next_fd
    
    if mode not in ("r", "w", "a"):
        raise NoxyRuntimeError(f"Modo de arquivo inválido: '{mode}'")
    
    try:
        f = open(path, mode, encoding="utf-8")
        fd = next_fd
        next_fd += 1
        open_files[fd] = f
        
        # Retorna struct File
        return NoxyStruct("File", {
            "fd": fd,
            "path": path,
            "mode": mode,
            "open": True
        })
    except Exception as e:
        return NoxyStruct("File", {
            "fd": -1,
            "path": path,
            "mode": mode,
            "open": False
        })

def io_close(file_struct: Any) -> None:
    """Fecha um arquivo."""
    if not isinstance(file_struct, NoxyStruct) and not isinstance(file_struct, dict):
         return 

    # Suporte a dict (retorno direto) ou NoxyStruct (se instanciado)
    if isinstance(file_struct, NoxyStruct):
        fd = file_struct.fields.get("fd")
        is_open = file_struct.fields.get("open")
    else:
        fd = file_struct.get("fd")
        is_open = file_struct.get("open")

    if not is_open:
        return

    if fd in open_files:
        try:
            open_files[fd].close()
        except:
            pass
        del open_files[fd]
    
    # Atualiza o estado do struct para open=false
    if isinstance(file_struct, NoxyStruct):
        file_struct.fields["open"] = False
    elif isinstance(file_struct, dict):
        file_struct["open"] = False

def io_read(file_struct: Any) -> NoxyStruct:
    """Lê todo o conteúdo do arquivo."""
    fd = _get_fd(file_struct)
    if fd is None or fd not in open_files:
         return NoxyStruct("IOResult", {"ok": False, "data": "", "error": "Arquivo fechado ou inválido"})
    
    try:
        content = open_files[fd].read()
        return NoxyStruct("IOResult", {"ok": True, "data": content, "error": ""})
    except Exception as e:
        return NoxyStruct("IOResult", {"ok": False, "data": "", "error": str(e)})

def io_read_line(file_struct: Any) -> NoxyStruct:
    """Lê uma linha do arquivo."""
    fd = _get_fd(file_struct)
    if fd is None or fd not in open_files:
         return NoxyStruct("IOResult", {"ok": False, "data": "", "error": "Arquivo fechado ou inválido"})
    
    try:
        line = open_files[fd].readline()
        return NoxyStruct("IOResult", {"ok": True, "data": line, "error": ""})
    except Exception as e:
        return NoxyStruct("IOResult", {"ok": False, "data": "", "error": str(e)})

def io_read_lines(file_struct: Any) -> NoxyStruct:
    """Lê todas as linhas como array."""
    fd = _get_fd(file_struct)
    if fd is None or fd not in open_files:
         return NoxyStruct("IOResult", {"ok": False, "data": [], "error": "Arquivo fechado"})

    try:
        lines = open_files[fd].readlines()
        return NoxyStruct("IOResult", {"ok": True, "data": lines, "error": ""}) 
    except Exception as e:
        return NoxyStruct("IOResult", {"ok": False, "data": [], "error": str(e)})

def io_write(file_struct: Any, content: str) -> None:
    """Escreve no arquivo."""
    fd = _get_fd(file_struct)
    if fd is None or fd not in open_files:
         return 
    
    try:
        open_files[fd].write(str(content))
        open_files[fd].flush()
    except:
        pass

def io_exists(path: str) -> bool:
    return os.path.exists(path)

def io_stat(path: str) -> NoxyStruct:
    try:
        st = os.stat(path)
        return NoxyStruct("FileInfo", {
            "exists": True,
            "size": st.st_size,
            "is_dir": os.path.isdir(path)
        })
    except:
        return NoxyStruct("FileInfo", {
            "exists": False,
            "size": 0,
            "is_dir": False
        })

def io_remove(path: str) -> bool:
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return True
    except:
        return False

def io_rename(src: str, dst: str) -> bool:
    try:
        os.rename(src, dst)
        return True
    except:
        return False

def io_mkdir(path: str) -> bool:
    try:
        os.mkdir(path)
        return True
    except:
        return False

def io_list_dir(path: str) -> NoxyStruct:
    try:
        entries = os.listdir(path)
        return NoxyStruct("IOResult", {"ok": True, "data": entries, "error": ""})
    except Exception as e:
        return NoxyStruct("IOResult", {"ok": False, "data": [], "error": str(e)})

def _get_fd(file_struct: Any) -> int | None:
    if isinstance(file_struct, NoxyStruct):
        return file_struct.fields.get("fd")
    elif isinstance(file_struct, dict):
        return file_struct.get("fd")
    return None


# Dicionário de funções builtin
BUILTINS: dict[str, Callable] = {
    "print": noxy_print,
    "to_str": noxy_to_str,
    "to_int": noxy_to_int,
    "to_float": noxy_to_float,
    "strlen": noxy_strlen,
    "ord": noxy_ord,
    "length": noxy_length,
    "zeros": noxy_zeros,
    # IO
    "io_open": io_open,
    "io_close": io_close,
    "io_read": io_read,
    "io_read_line": io_read_line,
    "io_read_lines": io_read_lines,
    "io_write": io_write,
    "io_exists": io_exists,
    "io_stat": io_stat,
    "io_remove": io_remove,
    "io_rename": io_rename,
    "io_mkdir": io_mkdir,
    "io_list_dir": io_list_dir,
}


def get_builtin(name: str) -> Callable | None:
    """Retorna uma função builtin por nome."""
    return BUILTINS.get(name)


def is_builtin(name: str) -> bool:
    """Verifica se é uma função builtin."""
    return name in BUILTINS


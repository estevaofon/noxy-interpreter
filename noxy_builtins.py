"""
Noxy Interpreter - Funções Builtin
Implementação das funções nativas do Noxy.
"""

from typing import Any, Callable
from environment import NoxyStruct, NoxyRef, NoxyArray
from errors import NoxyRuntimeError
from ast_nodes import PrimitiveType, ArrayType, StructType, RefType
import os
import os
import subprocess
import sys
import shutil
import socket
import select
import time
import sqlite3


def noxy_print(*args) -> None:
    """Imprime valores no console."""
    output = []
    for arg in args:
        output.append(value_to_string(arg))
    print(" ".join(output), flush=True)


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


def noxy_to_bytes(value: Any) -> bytes:
    """Converte valores para bytes."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode('utf-8')
    if isinstance(value, int):
        # Converte int para byte único? Ou representação de bytes?
        # Python bytes([int]) cria bytes com valor do int.
        # Python bytes(int) cria n bytes nulos.
        # Vamos assumir conversão de lista de ints ou int como byte único
        if 0 <= value <= 255:
            return bytes([value])
        raise NoxyRuntimeError(f"Inteiro {value} fora do range de byte (0-255)")
    if isinstance(value, list) or isinstance(value, NoxyArray):
        # Array de ints
        try:
            return bytes(value if isinstance(value, list) else value.elements)
        except ValueError:
             raise NoxyRuntimeError("Array deve conter apenas inteiros 0-255 para converter para bytes")
             
    raise NoxyRuntimeError(f"Não é possível converter {type(value).__name__} para bytes")


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


def noxy_substring(s: str, start: int, end: int) -> str:
    """Retorna substring."""
    if not isinstance(s, str):
        raise NoxyRuntimeError(f"substring() espera string, recebeu {type(s).__name__}")
    if not isinstance(start, int) or not isinstance(end, int):
        raise NoxyRuntimeError("substring() espera start/end inteiros")
    # Limita ranges? Python slice trata isso gracefully
    # Mas noxy specs talvez queira exceção? Vamos usar python slice
    return s[start:end]


def noxy_slice(data: bytes, start: int, end: int) -> bytes:
    """Retorna fatia de bytes."""
    if not isinstance(data, bytes):
        raise NoxyRuntimeError(f"slice() espera bytes, recebeu {type(data).__name__}")
    if not isinstance(start, int) or not isinstance(end, int):
        raise NoxyRuntimeError("slice() espera start/end inteiros")
    return data[start:end]
def noxy_length(obj: Any) -> int:
    """Retorna o tamanho de uma string, bytes, lista ou array."""
    if isinstance(obj, str) or isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, bytes):
        return len(obj)
    if isinstance(obj, NoxyArray):
        return len(obj.elements)
    if isinstance(obj, dict):
        return len(obj)
    raise NoxyRuntimeError(f"Tipo {type(obj)} não tem tamanho")


def noxy_remove(array: Any, item: Any) -> None:
    """Remove primeira ocorrência do item do array."""
    # NoxyStruct e outros não tem __eq__ fácil.
    # Vamos tentar remove direto.
    if isinstance(array, list):
        try:
            # Para structs (Socket), precisamos comparar por referência ou ID?
            # Se for o mesmo objeto Python, list.remove funciona.
            # net_select retorna novos objetos Socket ou os mesmos?
            # Minha implementação de net_select retorna os MESMOS objetos da tabela open_sockets.
            # Então remove deve funcionar se o objeto passado for o mesmo.
            if item in array:
                array.remove(item)
            else:
                 # Se não achar, procura por fd?
                 pass
        except ValueError:
            pass
    elif isinstance(array, NoxyArray):
        try:
             array.elements.remove(item)
        except ValueError:
             pass
    else:
        raise NoxyRuntimeError(f"remove requer array, recebido {type(array)}")



def noxy_append(array: Any, item: Any) -> None:
    """Adiciona item ao final do array dinâmico."""
    if isinstance(array, list):
        array.append(item)
    elif isinstance(array, NoxyArray):
        array.elements.append(item)
    else:
        raise NoxyRuntimeError(f"append() espera array, recebeu {type(array).__name__}")

def noxy_pop(array: Any) -> Any:
    """Remove e retorna o último item do array."""
    if isinstance(array, list):
        if not array:
             raise NoxyRuntimeError("pop() em array vazio")
        return array.pop()
    elif isinstance(array, NoxyArray):
        if not array.elements:
             raise NoxyRuntimeError("pop() em array vazio")
        return array.elements.pop()
    else:
        raise NoxyRuntimeError(f"pop() espera array, recebeu {type(array).__name__}")

def noxy_keys(mapping: Any) -> list:
    """Retorna chaves do mapa."""
    if not isinstance(mapping, dict):
        raise NoxyRuntimeError(f"keys() espera map, recebeu {type(mapping).__name__}")
    return list(mapping.keys())

def noxy_has_key(mapping: Any, key: Any) -> bool:
    """Verifica se chave existe no mapa."""
    if not isinstance(mapping, dict):
        raise NoxyRuntimeError(f"has_key() espera map, recebeu {type(mapping).__name__}")
    return key in mapping

def noxy_delete(mapping: Any, key: Any) -> None:
    """Remove chave do mapa."""
    if not isinstance(mapping, dict):
        raise NoxyRuntimeError(f"delete() espera map, recebeu {type(mapping).__name__}")
    if key in mapping:
        del mapping[key]

def noxy_contains(array: Any, item: Any) -> bool:
    """Verifica se item existe no array."""
    if isinstance(array, list):
        return item in array
    elif isinstance(array, NoxyArray):
        return item in array.elements
    else:
        raise NoxyRuntimeError(f"contains() espera array, recebeu {type(array).__name__}")


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
    
    if isinstance(value, bytes):
        return _decode_output(value)
    
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
# SYS MODULE BUILTINS
# ============================================================================

def _decode_output(data: bytes) -> str:
    """Decodifica output de bytes para string tentando várias codificações."""
    if not data:
        return ""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Tenta encoding do sistema (cp1252)
            import locale
            return data.decode(locale.getpreferredencoding(False))
        except:
            # Fallback final
            return data.decode('utf-8', errors='replace')

def sys_exec(command: str) -> NoxyStruct:
    """Executa comando do sistema - saída vai para terminal."""
    try:
        # Não forçamos encoding aqui para deixar o sistema decidir
        # Isso evita crash se o shell usar cp1252
        result = subprocess.run(
            command,
            shell=True,
            capture_output=False,
            text=False # Permite bytes/padrão
        )
        return NoxyStruct("SysResult", {
            "ok": result.returncode == 0,
            "output": "",
            "exit_code": result.returncode,
            "error": ""
        })
    except Exception as e:
        return NoxyStruct("SysResult", {
            "ok": False,
            "output": "",
            "exit_code": -1,
            "error": str(e)
        })

def sys_exec_output(command: str) -> NoxyStruct:
    """Executa comando e captura saída."""
    try:
        # Captura como bytes para decodificar manualmente
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=False, # Importante: capture bytes!
            timeout=30
        )
        return NoxyStruct("SysResult", {
            "ok": result.returncode == 0,
            "output": _decode_output(result.stdout),
            "exit_code": result.returncode,
            "error": _decode_output(result.stderr)
        })
    except subprocess.TimeoutExpired:
        return NoxyStruct("SysResult", {
            "ok": False,
            "output": "",
            "exit_code": -1,
            "error": "Command timeout"
        })
    except Exception as e:
        return NoxyStruct("SysResult", {
            "ok": False,
            "output": "",
            "exit_code": -1,
            "error": str(e)
        })

def sys_getenv(name: str) -> NoxyStruct:
    """Obtém variável de ambiente."""
    value = os.environ.get(name)
    if value is not None:
        return NoxyStruct("EnvResult", {
            "ok": True,
            "value": value,
            "error": ""
        })
    return NoxyStruct("EnvResult", {
        "ok": False,
        "value": "",
        "error": f"Variable '{name}' not found"
    })

def sys_setenv(name: str, value: str) -> bool:
    """Define variável de ambiente."""
    try:
        os.environ[name] = value
        return True
    except:
        return False

def sys_getcwd() -> str:
    """Obtém diretório atual."""
    return os.getcwd()

def sys_chdir(path: str) -> bool:
    """Muda diretório de trabalho."""
    try:
        os.chdir(path)
        return True
    except:
        return False

def sys_exit(code: int) -> None:
    """Termina programa."""
    sys.exit(code)

def sys_argv() -> list:
    """Retorna argumentos da linha de comando."""
    result = list(sys.argv)
    while len(result) < 100:
        result.append("")
    return result[:100]

def sys_sleep(ms: int) -> None:
    """Pausa execução."""
    time.sleep(ms / 1000.0)


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


# ============================================================================
# NET MODULE BUILTINS
# ============================================================================

# Tabela de sockets: fd -> socket object
open_sockets: dict[int, socket.socket] = {}
next_sock_fd: int = 1000

def net_listen(host: str, port: int) -> NoxyStruct:
    """Inicia um servidor TCP."""
    global next_sock_fd
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        s.setblocking(True)
        
        fd = next_sock_fd
        next_sock_fd += 1
        open_sockets[fd] = s
        
        return NoxyStruct("Socket", {
            "fd": fd,
            "addr": host,
            "port": port,
            "open": True
        })
    except Exception as e:
        # Em caso de erro, retorna socket fechado/inválido? 
        # Ou raises runtime error?
        # Noxy philosophy seems to be returning error structs or crashing for now.
        # Vamos lançar erro para ser mais visível, user pode tratar com try-catch (se tivesse).
        # Como não tem try-catch, vamos retornar socket com fd -1 e open=False?
        # É mais seguro.
        return NoxyStruct("Socket", {
            "fd": -1,
            "addr": host,
            "port": port,
            "open": False
        })

def net_accept(server_sock: Any) -> NoxyStruct:
    """Aceita uma conexão."""
    global next_sock_fd
    fd = _get_fd(server_sock)
    if fd is None or fd not in open_sockets:
        raise NoxyRuntimeError("Socket inválido ou fechado")
        
    s = open_sockets[fd]
    try:
        conn, addr = s.accept()
        conn.setblocking(True)
        
        client_fd = next_sock_fd
        next_sock_fd += 1
        open_sockets[client_fd] = conn
        
        return NoxyStruct("Socket", {
            "fd": client_fd,
            "addr": addr[0],
            "port": addr[1],
            "open": True
        })
    except Exception as e:
        raise NoxyRuntimeError(f"Erro no accept: {e}")

def net_connect(host: str, port: int) -> NoxyStruct:
    """Conecta a um servidor."""
    global next_sock_fd
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        
        fd = next_sock_fd
        next_sock_fd += 1
        open_sockets[fd] = s
        
        return NoxyStruct("Socket", {
            "fd": fd,
            "addr": host,
            "port": port,
            "open": True
        })
    except Exception as e:
        return NoxyStruct("Socket", {
            "fd": -1,
            "addr": host,
            "port": port,
            "open": False
        })

def net_recv(sock: Any, buf_size: int = 4096) -> NoxyStruct:
    """Recebe dados do socket."""
    fd = _get_fd(sock)
    if fd is None or fd not in open_sockets:
        return NoxyStruct("NetResult", {"ok": False, "data": b"", "count": 0, "error": "Socket fechado"})
    
    try:
        data = open_sockets[fd].recv(buf_size)
        return NoxyStruct("NetResult", {
            "ok": True, 
            "data": data, # retorna bytes
            "count": len(data),
            "error": ""
        })
    except Exception as e:
        return NoxyStruct("NetResult", {"ok": False, "data": b"", "count": 0, "error": str(e)})

def net_send(sock: Any, data: Any) -> NoxyStruct:
    """Envia dados para o socket."""
    fd = _get_fd(sock)
    if fd is None or fd not in open_sockets:
        return NoxyStruct("NetResult", {"ok": False, "data": b"", "bytes": 0, "error": "Socket fechado"})
    
    # Converte para bytes se necessário
    if isinstance(data, str):
        data_bytes = data.encode('utf-8')
    elif isinstance(data, bytes):
        data_bytes = data
    else:
        return NoxyStruct("NetResult", {"ok": False, "data": b"", "count": 0, "error": "Tipo de dados inválido para envio"})
        
    try:
        sent = open_sockets[fd].send(data_bytes)
        return NoxyStruct("NetResult", {
            "ok": True,
            "data": b"",
            "count": sent,
            "error": ""
        })
    except Exception as e:
        return NoxyStruct("NetResult", {"ok": False, "data": b"", "count": 0, "error": str(e)})

def net_close(sock: Any) -> None:
    """Fecha o socket."""
    if not isinstance(sock, NoxyStruct) and not isinstance(sock, dict):
         return 

    # Suporte a dict (retorno direto) ou NoxyStruct
    if isinstance(sock, NoxyStruct):
        fd = sock.fields.get("fd")
        is_open = sock.fields.get("open")
    else:
        fd = sock.get("fd")
        is_open = sock.get("open")

    if not is_open:
        return

    if fd in open_sockets:
        try:
            open_sockets[fd].close()
        except:
            pass
        del open_sockets[fd]
    
    # Atualiza o estado
        sock.fields["open"] = False
    elif isinstance(sock, dict):
        sock.fields["open"] = False

def net_setblocking(sock: Any, blocking: bool) -> None:
    """Define o modo de bloqueio do socket."""
    fd = _get_fd(sock)
    if fd is None or fd not in open_sockets:
        return
    try:
        open_sockets[fd].setblocking(blocking)
    except:
        pass

def net_socket_set() -> list[NoxyStruct]:
    """Cria um array de 64 sockets vazios/fechados."""
    # Cria 64 sockets "zerados"
    sockets = []
    for _ in range(64):
        sockets.append(NoxyStruct("Socket", {
            "fd": -1,
            "addr": "",
            "port": 0,
            "open": False
        }))
    return sockets

def net_select(read_list: list, write_list: list, error_list: list, timeout: int) -> NoxyStruct:
    """Monitora sockets."""
    # Mapeia input lists para FDs e para objetos originais
    r_map = {} # fd -> sock_obj
    w_map = {}
    e_map = {}
    
    # Helper para processar lista que pode conter sockets vazios (fd=-1)
    def process_list(in_list, mapping):
        fds = []
        if not isinstance(in_list, list) and not isinstance(in_list, NoxyArray):
             return []
        
        # Lidar com NoxyArray wrapper
        iterable = in_list.elements if isinstance(in_list, NoxyArray) else in_list
        
        for s in iterable:
            fd = _get_fd(s)
            # Ignora fd -1 (socket vazio/fechado)
            if fd is not None and fd != -1 and fd in open_sockets:
                mapping[fd] = s
                fds.append(open_sockets[fd])
        return fds

    r_sockets = process_list(read_list, r_map)
    w_sockets = process_list(write_list, w_map)
    e_sockets = process_list(error_list, e_map)
    
    try:
        # timeout em microssegundos no noxy? vamos assumir milissegundos
        t = timeout / 1000.0
        readable, writable, exceptional = select.select(r_sockets, w_sockets, e_sockets, t)
        
        # Reconstrói listas de retorno DE TAMANHO FIXO 64
        # Preenche com os sockets prontos e o resto com vazios
        
        def get_result_list(out_sockets, mapping):
            res = []
            count = 0
            
            # Adiciona os prontos
            for s in out_sockets:
                found_fd = None
                for fd, sock_obj in open_sockets.items():
                    if sock_obj is s:
                        found_fd = fd
                        break
                
                if found_fd is not None and found_fd in mapping:
                    res.append(mapping[found_fd])
                    count += 1
            
            # Preenche o resto com sockets vazios até 64
            empty_sock = NoxyStruct("Socket", {"fd": -1, "addr": "", "port": 0, "open": False})
            while len(res) < 64:
                res.append(empty_sock) # Mesma instância ou nova? Nova por segurança, mas noxy structs são ref?
                                       # Interpreter usa deepcopy em atribuição? Não, assignments são ref.
                                       # Então cuidado se user modificar.
                                       # Vamos criar novos.
                # res.append(NoxyStruct("Socket", ...)) - caro?
                # Vamos usar a mesma instância de vazio.
                # Se o user modificar um socket fechado, problema dele?
                res.append(empty_sock)
                
            return res, count

        r_list, r_count = get_result_list(readable, r_map)
        w_list, w_count = get_result_list(writable, w_map)
        e_list, e_count = get_result_list(exceptional, e_map)

        return NoxyStruct("SelectResult", {
            "read": r_list,
            "read_count": r_count,
            "write": w_list,
            "write_count": w_count,
            "error": e_list,
            "error_count": e_count
        })
        
    except Exception as e:
        print(f"Select error: {e}")
        # Retorna tudo vazio
        empty = net_socket_set()
        return NoxyStruct("SelectResult", {
            "read": empty, "read_count": 0,
            "write": empty, "write_count": 0,
            "error": empty, "error_count": 0
        })



# ============================================================================
# STRINGS MODULE BUILTINS
# ============================================================================

def strings_contains(s: str, sub: str) -> bool:
    """Verifica se 'sub' existe em 's'."""
    if not isinstance(s, str) or not isinstance(sub, str):
        raise NoxyRuntimeError("contains() espera dois argumentos string")
    return sub in s


def strings_starts_with(s: str, prefix: str) -> bool:
    """Verifica se 's' começa com 'prefix'."""
    if not isinstance(s, str) or not isinstance(prefix, str):
        raise NoxyRuntimeError("starts_with() espera dois argumentos string")
    return s.startswith(prefix)


def strings_ends_with(s: str, suffix: str) -> bool:
    """Verifica se 's' termina com 'suffix'."""
    if not isinstance(s, str) or not isinstance(suffix, str):
        raise NoxyRuntimeError("ends_with() espera dois argumentos string")
    return s.endswith(suffix)


def strings_index_of(s: str, sub: str) -> int:
    """Retorna índice da primeira ocorrência de 'sub' em 's'. Retorna -1 se não encontrar."""
    if not isinstance(s, str) or not isinstance(sub, str):
        raise NoxyRuntimeError("index_of() espera dois argumentos string")
    return s.find(sub)


def strings_last_index_of(s: str, sub: str) -> int:
    """Retorna índice da última ocorrência de 'sub' em 's'. Retorna -1 se não encontrar."""
    if not isinstance(s, str) or not isinstance(sub, str):
        raise NoxyRuntimeError("last_index_of() espera dois argumentos string")
    return s.rfind(sub)


def strings_count(s: str, sub: str) -> int:
    """Conta quantas vezes 'sub' aparece em 's'."""
    if not isinstance(s, str) or not isinstance(sub, str):
        raise NoxyRuntimeError("count() espera dois argumentos string")
    if sub == "":
        return 0  # Evita comportamento confuso do Python com string vazia
    return s.count(sub)


def strings_to_upper(s: str) -> str:
    """Converte string para maiúsculas."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("to_upper() espera argumento string")
    return s.upper()


def strings_to_lower(s: str) -> str:
    """Converte string para minúsculas."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("to_lower() espera argumento string")
    return s.lower()


def strings_trim(s: str) -> str:
    """Remove espaços em branco do início e fim da string."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("trim() espera argumento string")
    return s.strip()


def strings_trim_left(s: str) -> str:
    """Remove espaços em branco do início da string."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("trim_left() espera argumento string")
    return s.lstrip()


def strings_trim_right(s: str) -> str:
    """Remove espaços em branco do fim da string."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("trim_right() espera argumento string")
    return s.rstrip()


def strings_reverse(s: str) -> str:
    """Inverte a string."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("reverse() espera argumento string")
    return s[::-1]


def strings_repeat(s: str, n: int) -> str:
    """Repete a string 'n' vezes."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("repeat() espera string como primeiro argumento")
    if not isinstance(n, int):
        raise NoxyRuntimeError("repeat() espera int como segundo argumento")
    if n < 0:
        raise NoxyRuntimeError("repeat() não aceita valor negativo")
    if n > 10000:
        raise NoxyRuntimeError("repeat() limite máximo é 10000 repetições")
    return s * n


def strings_substring(s: str, start: int, end: int) -> str:
    """Extrai substring de 'start' até 'end' (exclusivo)."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("substring() espera string como primeiro argumento")
    if not isinstance(start, int) or not isinstance(end, int):
        raise NoxyRuntimeError("substring() espera int para start e end")
    
    length = len(s)
    
    # Normaliza índices negativos
    if start < 0:
        start = 0
    if end < 0:
        end = 0
    if start > length:
        start = length
    if end > length:
        end = length
    if start > end:
        return ""
    
    return s[start:end]


def strings_replace(s: str, old: str, new: str) -> str:
    """Substitui todas as ocorrências de 'old' por 'new'."""
    if not isinstance(s, str) or not isinstance(old, str) or not isinstance(new, str):
        raise NoxyRuntimeError("replace() espera três argumentos string")
    if old == "":
        return s  # Evita comportamento confuso
    return s.replace(old, new)


def strings_replace_first(s: str, old: str, new: str) -> str:
    """Substitui apenas a primeira ocorrência de 'old' por 'new'."""
    if not isinstance(s, str) or not isinstance(old, str) or not isinstance(new, str):
        raise NoxyRuntimeError("replace_first() espera três argumentos string")
    if old == "":
        return s
    return s.replace(old, new, 1)


def strings_pad_left(s: str, width: int, char: str) -> str:
    """Preenche a string à esquerda com 'char' até atingir 'width'."""
    if not isinstance(s, str) or not isinstance(char, str):
        raise NoxyRuntimeError("pad_left() espera string para s e char")
    if not isinstance(width, int):
        raise NoxyRuntimeError("pad_left() espera int para width")
    if len(char) != 1:
        raise NoxyRuntimeError("pad_left() char deve ter exatamente 1 caractere")
    if width < 0:
        width = 0
    if width > 10000:
        raise NoxyRuntimeError("pad_left() width máximo é 10000")
    return s.rjust(width, char)


def strings_pad_right(s: str, width: int, char: str) -> str:
    """Preenche a string à direita com 'char' até atingir 'width'."""
    if not isinstance(s, str) or not isinstance(char, str):
        raise NoxyRuntimeError("pad_right() espera string para s e char")
    if not isinstance(width, int):
        raise NoxyRuntimeError("pad_right() espera int para width")
    if len(char) != 1:
        raise NoxyRuntimeError("pad_right() char deve ter exatamente 1 caractere")
    if width < 0:
        width = 0
    if width > 10000:
        raise NoxyRuntimeError("pad_right() width máximo é 10000")
    return s.ljust(width, char)


def strings_split(s: str, sep: str) -> NoxyStruct:
    """Divide string pelo separador. Retorna SplitResult com array e count."""
    if not isinstance(s, str) or not isinstance(sep, str):
        raise NoxyRuntimeError("split() espera dois argumentos string")
    
    if sep == "":
        # Split por caractere
        parts = list(s)
    else:
        parts = s.split(sep)
    
    # Limita a 100 partes (tamanho fixo do array em Noxy)
    MAX_PARTS = 100
    count = min(len(parts), MAX_PARTS)
    
    # Preenche array até 100 elementos
    result_parts = parts[:MAX_PARTS]
    while len(result_parts) < MAX_PARTS:
        result_parts.append("")
    
    return NoxyStruct("SplitResult", {
        "parts": result_parts,
        "count": count
    })


def strings_join(arr: Any, sep: str) -> str:
    """Junta elementos do array usando o separador."""
    if not isinstance(sep, str):
        raise NoxyRuntimeError("join() espera string como separador")
    
    # Suporta list Python ou NoxyArray
    if isinstance(arr, list):
        elements = arr
    elif isinstance(arr, NoxyArray):
        elements = arr.elements
    else:
        raise NoxyRuntimeError("join() espera array como primeiro argumento")
    
    # Filtra elementos vazios no final (padrão Noxy de arrays fixos)
    str_elements = []
    for elem in elements:
        if isinstance(elem, str):
            if elem == "" and len(str_elements) > 0:
                # Para quando encontrar string vazia após conteúdo (fim do array lógico)
                # Na verdade, melhor juntar tudo e deixar o usuário controlar
                pass
            str_elements.append(elem)
        else:
            str_elements.append(str(elem))
    
    return sep.join(str_elements)


def strings_join_count(arr: Any, sep: str, count: int) -> str:
    """Junta os primeiros 'count' elementos do array usando o separador."""
    if not isinstance(sep, str):
        raise NoxyRuntimeError("join_count() espera string como separador")
    if not isinstance(count, int):
        raise NoxyRuntimeError("join_count() espera int como count")
    
    if isinstance(arr, list):
        elements = arr
    elif isinstance(arr, NoxyArray):
        elements = arr.elements
    else:
        raise NoxyRuntimeError("join_count() espera array como primeiro argumento")
    
    # Pega apenas os primeiros 'count' elementos
    str_elements = []
    for i, elem in enumerate(elements):
        if i >= count:
            break
        if isinstance(elem, str):
            str_elements.append(elem)
        else:
            str_elements.append(str(elem))
    
    return sep.join(str_elements)


def strings_is_empty(s: str) -> bool:
    """Verifica se a string está vazia."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("is_empty() espera argumento string")
    return len(s) == 0


def strings_is_digit(s: str) -> bool:
    """Verifica se todos os caracteres são dígitos (0-9)."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("is_digit() espera argumento string")
    if len(s) == 0:
        return False
    return s.isdigit()


def strings_is_alpha(s: str) -> bool:
    """Verifica se todos os caracteres são letras."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("is_alpha() espera argumento string")
    if len(s) == 0:
        return False
    return s.isalpha()


def strings_is_alnum(s: str) -> bool:
    """Verifica se todos os caracteres são alfanuméricos."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("is_alnum() espera argumento string")
    if len(s) == 0:
        return False
    return s.isalnum()


def strings_is_space(s: str) -> bool:
    """Verifica se todos os caracteres são espaços em branco."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("is_space() espera argumento string")
    if len(s) == 0:
        return False
    return s.isspace()


def strings_char_at(s: str, index: int) -> str:
    """Retorna o caractere na posição especificada."""
    if not isinstance(s, str):
        raise NoxyRuntimeError("char_at() espera string como primeiro argumento")
    if not isinstance(index, int):
        raise NoxyRuntimeError("char_at() espera int como índice")
    if index < 0 or index >= len(s):
        raise NoxyRuntimeError(f"char_at() índice {index} fora dos limites [0, {len(s)})")
    return s[index]


def strings_from_char_code(code: int) -> str:
    """Cria uma string de um único caractere a partir do código Unicode."""
    if not isinstance(code, int):
        raise NoxyRuntimeError("from_char_code() espera argumento int")
    if code < 0 or code > 0x10FFFF:
        raise NoxyRuntimeError(f"from_char_code() código {code} fora do range Unicode válido")
    return chr(code)



# ============================================================================
# SQLITE MODULE BUILTINS
# ============================================================================

# Tabela de conexões: handle -> connection
open_databases: dict[int, sqlite3.Connection] = {}
next_db_handle: int = 1

# Tabela de statements: handle -> cursor info
open_statements: dict[int, dict] = {}
next_stmt_handle: int = 1


def sqlite_open(path: str) -> NoxyStruct:
    """Abre ou cria um banco de dados SQLite."""
    global next_db_handle
    try:
        conn = sqlite3.connect(path, isolation_level=None)
        handle = next_db_handle
        next_db_handle += 1
        open_databases[handle] = conn
        return NoxyStruct("Database", {
            "handle": handle,
            "path": path,
            "open": True
        })
    except Exception as e:
        return NoxyStruct("Database", {
            "handle": -1,
            "path": path,
            "open": False
        })


def sqlite_close(db: Any) -> None:
    """Fecha uma conexão com o banco de dados."""
    handle = _get_db_handle(db)
    if handle and handle in open_databases:
        try:
            open_databases[handle].close()
        except:
            pass
        del open_databases[handle]


def sqlite_exec(db: Any, sql: str) -> NoxyStruct:
    """Executa SQL sem retorno de dados (CREATE, INSERT, UPDATE, DELETE)."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return NoxyStruct("ExecResult", {
            "ok": False,
            "rows_affected": 0,
            "last_insert_id": 0,
            "error": "Database not open"
        })
    
    try:
        conn = open_databases[handle]
        cursor = conn.cursor()
        cursor.execute(sql)
        # Em isolation_level=None, autocommit é o padrão, a menos que haja BEGIN explícito.
        # Não chamamos conn.commit().
        return NoxyStruct("ExecResult", {
            "ok": True,
            "rows_affected": cursor.rowcount,
            "last_insert_id": cursor.lastrowid or 0,
            "error": ""
        })
    except Exception as e:
        return NoxyStruct("ExecResult", {
            "ok": False,
            "rows_affected": 0,
            "last_insert_id": 0,
            "error": str(e)
        })


def sqlite_query(db: Any, sql: str) -> NoxyStruct:
    """Executa uma query SELECT e retorna os resultados."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return _empty_query_result("Database not open")
    
    try:
        conn = open_databases[handle]
        cursor = conn.cursor()
        cursor.execute(sql)
        
        # Obtém nomes das colunas
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        column_count = len(columns)
        
        # Preenche array de colunas (tamanho fixo 32)
        columns_array = columns[:32] + [""] * (32 - min(len(columns), 32))
        
        # Obtém linhas (máximo 100)
        rows_data = cursor.fetchmany(100)
        row_count = len(rows_data)
        
        # Converte para structs Row
        rows = []
        for row in rows_data:
            values = []
            types = []
            for val in row:
                if val is None:
                    values.append("")
                    types.append(0)  # NULL
                elif isinstance(val, int):
                    values.append(str(val))
                    types.append(1)  # INT
                elif isinstance(val, float):
                    values.append(str(val))
                    types.append(2)  # FLOAT
                elif isinstance(val, str):
                    values.append(val)
                    types.append(3)  # TEXT
                elif isinstance(val, bytes):
                    values.append(val.hex())
                    types.append(4)  # BLOB
                else:
                    values.append(str(val))
                    types.append(3)
            
            # Preenche até 32 elementos
            values = values[:32] + [""] * (32 - min(len(values), 32))
            types = types[:32] + [0] * (32 - min(len(types), 32))
            
            rows.append(NoxyStruct("Row", {
                "values": values,
                "types": types
            }))
        
        # Preenche rows até 100
        empty_row = NoxyStruct("Row", {
            "values": [""] * 32,
            "types": [0] * 32
        })
        while len(rows) < 100:
            rows.append(empty_row)
        
        return NoxyStruct("QueryResult", {
            "ok": True,
            "rows": rows,
            "row_count": row_count,
            "columns": columns_array,
            "column_count": column_count,
            "error": ""
        })
    except Exception as e:
        return _empty_query_result(str(e))


def sqlite_prepare(db: Any, sql: str) -> NoxyStruct:
    """Prepara um statement para execução."""
    global next_stmt_handle
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return NoxyStruct("Statement", {
            "handle": -1,
            "sql": sql,
            "param_count": 0,
            "ready": False
        })
    
    try:
        conn = open_databases[handle]
        cursor = conn.cursor()
        # Conta placeholders (?)
        param_count = sql.count("?")
        
        stmt_handle = next_stmt_handle
        next_stmt_handle += 1
        
        # Armazena cursor e info
        open_statements[stmt_handle] = {
            "cursor": cursor,
            "sql": sql,
            "conn": conn,
            "params": {}
        }
        
        return NoxyStruct("Statement", {
            "handle": stmt_handle,
            "sql": sql,
            "param_count": param_count,
            "ready": True
        })
    except Exception as e:
        return NoxyStruct("Statement", {
            "handle": -1,
            "sql": sql,
            "param_count": 0,
            "ready": False
        })


def sqlite_bind_int(stmt: Any, pos: int, val: int) -> None:
    """Bind de valor inteiro a um placeholder."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        open_statements[handle]["params"][pos] = val


def sqlite_bind_float(stmt: Any, pos: int, val: float) -> None:
    """Bind de valor float a um placeholder."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        open_statements[handle]["params"][pos] = val


def sqlite_bind_text(stmt: Any, pos: int, val: str) -> None:
    """Bind de valor string a um placeholder."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        open_statements[handle]["params"][pos] = val


def sqlite_bind_null(stmt: Any, pos: int) -> None:
    """Bind de NULL a um placeholder."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        open_statements[handle]["params"][pos] = None


def sqlite_step_exec(stmt: Any) -> NoxyStruct:
    """Executa um prepared statement (INSERT/UPDATE/DELETE)."""
    handle = _get_stmt_handle(stmt)
    if handle is None or handle not in open_statements:
        return NoxyStruct("ExecResult", {
            "ok": False,
            "rows_affected": 0,
            "last_insert_id": 0,
            "error": "Statement not ready"
        })
    
    try:
        stmt_data = open_statements[handle]
        cursor = stmt_data["cursor"]
        sql = stmt_data["sql"]
        conn = stmt_data["conn"]
        
        # Monta tupla de parâmetros ordenados
        params = stmt_data["params"]
        max_pos = max(params.keys()) if params else 0
        param_tuple = tuple(params.get(i, None) for i in range(1, max_pos + 1))
        
        cursor.execute(sql, param_tuple)
        
        return NoxyStruct("ExecResult", {
            "ok": True,
            "rows_affected": cursor.rowcount,
            "last_insert_id": cursor.lastrowid or 0,
            "error": ""
        })
    except Exception as e:
        return NoxyStruct("ExecResult", {
            "ok": False,
            "rows_affected": 0,
            "last_insert_id": 0,
            "error": str(e)
        })


def sqlite_step_query(stmt: Any) -> NoxyStruct:
    """Executa um prepared statement SELECT."""
    handle = _get_stmt_handle(stmt)
    if handle is None or handle not in open_statements:
        return _empty_query_result("Statement not ready")
    
    try:
        stmt_data = open_statements[handle]
        cursor = stmt_data["cursor"]
        sql = stmt_data["sql"]
        
        # Monta tupla de parâmetros
        params = stmt_data["params"]
        max_pos = max(params.keys()) if params else 0
        param_tuple = tuple(params.get(i, None) for i in range(1, max_pos + 1))
        
        cursor.execute(sql, param_tuple)
        
        # Processa resultados
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        column_count = len(columns)
        columns_array = columns[:32] + [""] * (32 - min(len(columns), 32))
        
        rows_data = cursor.fetchmany(100)
        row_count = len(rows_data)
        
        rows = []
        for row in rows_data:
            values = []
            types = []
            for val in row:
                if val is None:
                    values.append("")
                    types.append(0)
                elif isinstance(val, int):
                    values.append(str(val))
                    types.append(1)
                elif isinstance(val, float):
                    values.append(str(val))
                    types.append(2)
                elif isinstance(val, str):
                    values.append(val)
                    types.append(3)
                elif isinstance(val, bytes):
                    values.append(val.hex())
                    types.append(4)
                else:
                    values.append(str(val))
                    types.append(3)
            
            values = values[:32] + [""] * (32 - min(len(values), 32))
            types = types[:32] + [0] * (32 - min(len(types), 32))
            
            rows.append(NoxyStruct("Row", {"values": values, "types": types}))
        
        empty_row = NoxyStruct("Row", {"values": [""] * 32, "types": [0] * 32})
        while len(rows) < 100:
            rows.append(empty_row)
        
        return NoxyStruct("QueryResult", {
            "ok": True,
            "rows": rows,
            "row_count": row_count,
            "columns": columns_array,
            "column_count": column_count,
            "error": ""
        })
    except Exception as e:
        return _empty_query_result(str(e))


def sqlite_reset(stmt: Any) -> None:
    """Reseta um statement para reutilização."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        open_statements[handle]["params"] = {}


def sqlite_finalize(stmt: Any) -> None:
    """Libera recursos de um statement."""
    handle = _get_stmt_handle(stmt)
    if handle and handle in open_statements:
        try:
            open_statements[handle]["cursor"].close()
        except:
            pass
        del open_statements[handle]


def sqlite_begin(db: Any) -> bool:
    """Inicia uma transação."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return False
    try:
        open_databases[handle].execute("BEGIN")
        return True
    except:
        return False


def sqlite_commit(db: Any) -> bool:
    """Confirma uma transação."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return False
    try:
        open_databases[handle].execute("COMMIT")
        return True
    except:
        return False


def sqlite_rollback(db: Any) -> bool:
    """Cancela uma transação."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return False
    try:
        open_databases[handle].execute("ROLLBACK")
        return True
    except:
        return False


def sqlite_table_exists(db: Any, name: str) -> bool:
    """Verifica se uma tabela existe."""
    handle = _get_db_handle(db)
    if handle is None or handle not in open_databases:
        return False
    try:
        cursor = open_databases[handle].cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,)
        )
        return cursor.fetchone() is not None
    except:
        return False


def sqlite_escape(val: str) -> str:
    """Escapa uma string para uso seguro em SQL."""
    if not isinstance(val, str):
        return str(val)
    return val.replace("'", "''")


# ============================================
# Helpers internos para SQLite
# ============================================

def _get_db_handle(db: Any) -> int | None:
    """Extrai handle de um Database struct."""
    if isinstance(db, NoxyStruct):
        return db.fields.get("handle")
    elif isinstance(db, dict):
        return db.get("handle")
    return None


def _get_stmt_handle(stmt: Any) -> int | None:
    """Extrai handle de um Statement struct."""
    if isinstance(stmt, NoxyStruct):
        return stmt.fields.get("handle")
    elif isinstance(stmt, dict):
        return stmt.get("handle")
    return None


def _empty_query_result(error: str) -> NoxyStruct:
    """Cria um QueryResult vazio com erro."""
    empty_row = NoxyStruct("Row", {"values": [""] * 32, "types": [0] * 32})
    return NoxyStruct("QueryResult", {
        "ok": False,
        "rows": [empty_row] * 100,
        "row_count": 0,
        "columns": [""] * 32,
        "column_count": 0,
        "error": error
    })


# Dicionário de funções builtin
BUILTINS: dict[str, Callable] = {
    "print": noxy_print,
    "to_str": noxy_to_str,
    "to_int": noxy_to_int,
    "to_float": noxy_to_float,
    "to_bytes": noxy_to_bytes,
    "strlen": noxy_strlen,
    "ord": noxy_ord,
    "substring": noxy_substring,
    "slice": noxy_slice,
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
    # Net
    "net_listen": net_listen,
    "net_accept": net_accept,
    "net_connect": net_connect,
    "net_recv": net_recv,
    "net_send": net_send,
    "net_close": net_close,
    "net_setblocking": net_setblocking,
    "net_select": net_select,
    "net_socket_set": net_socket_set,
    
    # Array utils
    "remove": noxy_remove,
    "append": noxy_append,
    "pop": noxy_pop,
    "keys": noxy_keys,
    "has_key": noxy_has_key,
    "delete": noxy_delete,
    "contains": noxy_contains,
    # Sys Functions
    "sys_exec": sys_exec,
    "sys_exec_output": sys_exec_output,
    "sys_getenv": sys_getenv,
    "sys_setenv": sys_setenv,
    "sys_getcwd": sys_getcwd,
    "sys_chdir": sys_chdir,
    "sys_exit": sys_exit,
    "sys_argv": sys_argv,
    "sys_sleep": sys_sleep,
    
    # Strings Functions
    "strings_contains": strings_contains,
    "strings_starts_with": strings_starts_with,
    "strings_ends_with": strings_ends_with,
    "strings_index_of": strings_index_of,
    "strings_last_index_of": strings_last_index_of,
    "strings_count": strings_count,
    "strings_to_upper": strings_to_upper,
    "strings_to_lower": strings_to_lower,
    "strings_trim": strings_trim,
    "strings_trim_left": strings_trim_left,
    "strings_trim_right": strings_trim_right,
    "strings_reverse": strings_reverse,
    "strings_repeat": strings_repeat,
    "strings_substring": strings_substring,
    "strings_replace": strings_replace,
    "strings_replace_first": strings_replace_first,
    "strings_pad_left": strings_pad_left,
    "strings_pad_right": strings_pad_right,
    "strings_split": strings_split,
    "strings_join": strings_join,
    "strings_join_count": strings_join_count,
    "strings_is_empty": strings_is_empty,
    "strings_is_digit": strings_is_digit,
    "strings_is_alpha": strings_is_alpha,
    "strings_is_alnum": strings_is_alnum,
    "strings_is_space": strings_is_space,
    "strings_char_at": strings_char_at,
    "strings_from_char_code": strings_from_char_code,
    
    # SQLite Functions
    "sqlite_open": sqlite_open,
    "sqlite_close": sqlite_close,
    "sqlite_exec": sqlite_exec,
    "sqlite_query": sqlite_query,
    "sqlite_prepare": sqlite_prepare,
    "sqlite_bind_int": sqlite_bind_int,
    "sqlite_bind_float": sqlite_bind_float,
    "sqlite_bind_text": sqlite_bind_text,
    "sqlite_bind_null": sqlite_bind_null,
    "sqlite_step_exec": sqlite_step_exec,
    "sqlite_step_query": sqlite_step_query,
    "sqlite_reset": sqlite_reset,
    "sqlite_finalize": sqlite_finalize,
    "sqlite_begin": sqlite_begin,
    "sqlite_commit": sqlite_commit,
    "sqlite_rollback": sqlite_rollback,
    "sqlite_table_exists": sqlite_table_exists,
    "sqlite_escape": sqlite_escape,
}


def get_builtin(name: str) -> Callable | None:
    """Retorna uma função builtin por nome."""
    return BUILTINS.get(name)


def is_builtin(name: str) -> bool:
    """Verifica se é uma função builtin."""
    return name in BUILTINS


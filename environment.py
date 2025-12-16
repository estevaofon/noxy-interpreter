"""
Noxy Interpreter - Environment
Gerenciamento de escopos e tabela de símbolos.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from copy import deepcopy
from ast_nodes import NoxyType, FuncDef, StructDef
from errors import NoxyNameError, NoxyRuntimeError


@dataclass
class Variable:
    """Representa uma variável no ambiente."""
    name: str
    var_type: NoxyType
    value: Any
    is_global: bool = False


class Environment:
    """Ambiente de execução com escopos aninhados."""
    
    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.variables: dict[str, Variable] = {}
        self.functions: dict[str, FuncDef] = {}
        self.structs: dict[str, StructDef] = {}
    
    def define(self, name: str, var_type: NoxyType, value: Any, is_global: bool = False):
        """Define uma nova variável no escopo atual."""
        self.variables[name] = Variable(name, var_type, value, is_global)
    
    def get(self, name: str) -> Variable:
        """Obtém uma variável por nome."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise NoxyNameError(f"Variável '{name}' não definida")
    
    def get_value(self, name: str) -> Any:
        """Obtém o valor de uma variável."""
        return self.get(name).value
    
    def set(self, name: str, value: Any):
        """Atribui valor a uma variável existente."""
        if name in self.variables:
            self.variables[name].value = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise NoxyNameError(f"Variável '{name}' não definida")
    
    def exists(self, name: str) -> bool:
        """Verifica se variável existe."""
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.exists(name)
        return False
    
    def define_function(self, func: FuncDef):
        """Define uma função."""
        self.functions[func.name] = func
    
    def get_function(self, name: str) -> Optional[FuncDef]:
        """Obtém uma função por nome."""
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name)
        return None
    
    def define_struct(self, struct: StructDef):
        """Define um struct."""
        self.structs[struct.name] = struct
    
    def get_struct(self, name: str) -> Optional[StructDef]:
        """Obtém um struct por nome."""
        if name in self.structs:
            return self.structs[name]
        if self.parent:
            return self.parent.get_struct(name)
        return None
    
    def new_child(self) -> "Environment":
        """Cria um novo escopo filho."""
        return Environment(parent=self)


@dataclass
class NoxyStruct:
    """Representa uma instância de struct em runtime."""
    type_name: str
    fields: dict[str, Any]
    
    def get_field(self, name: str) -> Any:
        """Obtém valor de um campo."""
        if name not in self.fields:
            raise NoxyRuntimeError(f"Struct '{self.type_name}' não tem campo '{name}'")
        return self.fields[name]
    
    def set_field(self, name: str, value: Any):
        """Define valor de um campo."""
        if name not in self.fields:
            raise NoxyRuntimeError(f"Struct '{self.type_name}' não tem campo '{name}'")
        self.fields[name] = value
    
    def deep_copy(self) -> "NoxyStruct":
        """Cria uma cópia profunda do struct."""
        new_fields = {}
        for name, value in self.fields.items():
            if isinstance(value, NoxyStruct):
                new_fields[name] = value.deep_copy()
            elif isinstance(value, list):
                new_fields[name] = deep_copy_array(value)
            elif isinstance(value, NoxyRef):
                # Referências não são copiadas profundamente
                new_fields[name] = value
            else:
                new_fields[name] = value
        return NoxyStruct(self.type_name, new_fields)
    
    def __repr__(self):
        return f"{self.type_name}({self.fields})"


@dataclass
class NoxyRef:
    """Representa uma referência (ponteiro) para um valor."""
    target: Any = None
    target_obj: Any = None  # Objeto que contém o campo
    target_field: str = None  # Nome do campo, se for campo de struct
    target_index: int = None  # Índice, se for elemento de array
    
    def get_value(self) -> Any:
        """Obtém o valor referenciado."""
        if self.target_obj is not None:
            if self.target_field is not None:
                if isinstance(self.target_obj, NoxyStruct):
                    return self.target_obj.get_field(self.target_field)
                elif isinstance(self.target_obj, dict):
                    return self.target_obj.get(self.target_field)
            elif self.target_index is not None:
                return self.target_obj[self.target_index]
        return self.target
    
    def set_value(self, value: Any):
        """Define o valor referenciado."""
        if self.target_obj is not None:
            if self.target_field is not None:
                if isinstance(self.target_obj, NoxyStruct):
                    self.target_obj.set_field(self.target_field, value)
                elif isinstance(self.target_obj, dict):
                    self.target_obj[self.target_field] = value
            elif self.target_index is not None:
                self.target_obj[self.target_index] = value
        else:
            self.target = value
    
    @staticmethod
    def create_from_variable(env: Environment, name: str) -> "NoxyRef":
        """Cria uma referência para uma variável."""
        var = env.get(name)
        return NoxyRef(target=var.value)
    
    @staticmethod
    def create_from_field(obj: Any, field_name: str) -> "NoxyRef":
        """Cria uma referência para um campo de struct."""
        return NoxyRef(target_obj=obj, target_field=field_name)
    
    @staticmethod
    def create_from_index(arr: list, index: int) -> "NoxyRef":
        """Cria uma referência para um elemento de array."""
        return NoxyRef(target_obj=arr, target_index=index)
    
    def __repr__(self):
        if self.target is None and self.target_obj is None:
            return "ref(null)"
        return f"ref({self.get_value()})"


@dataclass
class NoxyArray:
    """Representa um array em runtime."""
    elements: list[Any]
    element_type: NoxyType
    
    def __len__(self):
        return len(self.elements)
    
    def __getitem__(self, index: int):
        if index < 0 or index >= len(self.elements):
            raise NoxyRuntimeError(f"Índice {index} fora dos limites [0, {len(self.elements)})")
        return self.elements[index]
    
    def __setitem__(self, index: int, value: Any):
        if index < 0 or index >= len(self.elements):
            raise NoxyRuntimeError(f"Índice {index} fora dos limites [0, {len(self.elements)})")
        self.elements[index] = value
    
    def __repr__(self):
        return f"[{', '.join(repr(e) for e in self.elements)}]"


def deep_copy_array(arr: list) -> list:
    """Cria cópia profunda de um array."""
    result = []
    for elem in arr:
        if isinstance(elem, NoxyStruct):
            result.append(elem.deep_copy())
        elif isinstance(elem, list):
            result.append(deep_copy_array(elem))
        else:
            result.append(elem)
    return result


def deep_copy_value(value: Any) -> Any:
    """Cria cópia profunda de qualquer valor."""
    if isinstance(value, NoxyStruct):
        return value.deep_copy()
    elif isinstance(value, list):
        return deep_copy_array(value)
    elif isinstance(value, NoxyRef):
        # Referências não são copiadas profundamente
        return value
    else:
        return value





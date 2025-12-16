# Noxy Interpreter 🚀

Um interpretador tree-walking completo para a linguagem de programação **Noxy**, escrito em Python.

<p align="center">
<img width="300" height="300 alt="481382230-8af825b7-fc42-4e0b-8aab-da9bba99b6e0" src="https://github.com/user-attachments/assets/cd9c70be-e01f-4d29-a703-c394c9d62531" />
</p>

## O que é Noxy?

Noxy é uma linguagem de programação **estaticamente tipada** com:

- ✅ Tipos primitivos: `int`, `float`, `string`, `bool`
- ✅ Structs com campos tipados
- ✅ Arrays de tamanho fixo
- ✅ Funções com recursão
- ✅ Sistema de referências (`ref`) para mutação controlada
- ✅ F-strings para interpolação
- ✅ Sistema de módulos

## Instalação

```bash
# Clone o repositório
git clone <repo-url>
cd noxy_interpreter

# Execute com uv (recomendado)
uv run main.py arquivo.nx
```

## Uso

```bash
# Executar um programa Noxy
uv run main.py programa.nx

# Executar com debug (mostra tokens, AST, etc.)
uv run main.py programa.nx --debug

# Executar sem verificação de tipos
uv run main.py programa.nx --no-typecheck

# REPL interativo
uv run main.py
```

## Exemplo Rápido

```noxy
// exemplo.nx
let x: int = 10
let y: int = 20
print(f"Soma: {x + y}")

struct Pessoa
    nome: string,
    idade: int
end

let p: Pessoa = Pessoa("Ana", 25)
print(p.nome)

func dobrar(n: int) -> int
    return n * 2
end

print(to_str(dobrar(x)))
```

Saída:
```
Soma: 30
Ana
20
```

## Arquitetura

```
noxy_interpreter/
├── main.py           # CLI principal
├── lexer.py          # Tokenização
├── parser.py         # Parser recursive descent → AST
├── ast_nodes.py      # Dataclasses para nós da AST
├── interpreter.py    # Tree-walking interpreter
├── environment.py    # Escopos e tabela de símbolos
├── noxy_types.py     # Sistema de tipos estático
├── noxy_builtins.py  # Funções nativas (print, to_str, etc.)
├── errors.py         # Exceções do interpretador
└── noxy_examples/    # Exemplos de programas Noxy
```

## Funcionalidades

### Variáveis

```noxy
let x: int = 42
let nome: string = "Noxy"
let ativo: bool = true
let pi: float = 3.14159

global contador: int = 0  // Variável global
```

### Structs

```noxy
struct Pessoa
    nome: string,
    idade: int
end

let p: Pessoa = Pessoa("João", 30)
print(p.nome)
p.idade = 31
```

### Structs Aninhados

```noxy
struct Endereco
    rua: string,
    numero: int
end

struct Funcionario
    dados: Pessoa,
    endereco: Endereco
end

let f: Funcionario = Funcionario(
    Pessoa("Ana", 25),
    Endereco("Rua A", 100)
)
print(f.dados.nome)  // Ana
```

### Funções

```noxy
func somar(a: int, b: int) -> int
    return a + b
end

func fatorial(n: int) -> int
    if n <= 1 then
        return 1
    else
        return n * fatorial(n - 1)
    end
end
```

### Passagem por Valor vs Referência

```noxy
// Por VALOR - struct é copiado, original não muda
func incrementar_copia(c: Contador) -> void
    c.valor = c.valor + 1  // Modifica apenas a cópia
end

// Por REFERÊNCIA - modifica o original
func incrementar_ref(c: ref Contador) -> void
    c.valor = c.valor + 1  // Modifica o original!
end
```

### Arrays

```noxy
let nums: int[5] = [1, 2, 3, 4, 5]
let primeiro: int = nums[0]
nums[0] = 100

let zeros_arr: int[10] = zeros(10)
```

### Controle de Fluxo

```noxy
// If-then-else
if x > 10 then
    print("Grande")
else
    print("Pequeno")
end

// While loop
let i: int = 0
while i < 10 do
    print(to_str(i))
    i = i + 1
end

// Break
while true do
    if condicao then
        break
    end
end
```

### F-Strings

```noxy
let nome: string = "Noxy"
let versao: int = 1
print(f"Linguagem: {nome}, Versão: {versao}")
print(f"2 + 2 = {2 + 2}")
```

### Sistema de Módulos

```noxy
// math.nx
func add(a: int, b: int) -> int
    return a + b
end

// main.nx
use math select add, multiply
// ou
use math select *

print(to_str(add(5, 3)))
```

## Funções Builtin

| Função | Descrição | Exemplo |
|--------|-----------|---------|
| `print(expr)` | Imprime valor | `print("Hello")` |
| `to_str(val)` | Converte para string | `to_str(42)` → `"42"` |
| `to_int(val)` | Converte para int | `to_int(3.7)` → `3` |
| `to_float(val)` | Converte para float | `to_float(42)` → `42.0` |
| `strlen(s)` | Tamanho da string | `strlen("abc")` → `3` |
| `ord(c)` | Código Unicode | `ord("A")` → `65` |
| `length(arr)` | Tamanho do array | `length([1,2,3])` → `3` |
| `zeros(n)` | Array de n zeros | `zeros(5)` → `[0,0,0,0,0]` |

## Operadores

| Tipo | Operadores |
|------|------------|
| Aritméticos | `+`, `-`, `*`, `/`, `%` |
| Comparação | `>`, `<`, `>=`, `<=`, `==`, `!=` |
| Lógicos | `&` (AND), `\|` (OR), `!` (NOT) |
| String | `+` (concatenação) |

## Exemplos Incluídos

- `noxy_examples/exemplo.nx` - Exemplo básico
- `noxy_examples/dijkstra.nx` - Algoritmo de Dijkstra
- `noxy_examples/structs_aninhados.nx` - Structs complexos
- `noxy_examples/test_ref_vs_valor.nx` - Demonstração ref vs valor

## Especificação Completa

Veja `NOXY_LANGUAGE_SPEC.md` para a especificação completa da linguagem.

## Licença

MIT License

---

*Desenvolvido como interpretador educacional para a linguagem Noxy.*


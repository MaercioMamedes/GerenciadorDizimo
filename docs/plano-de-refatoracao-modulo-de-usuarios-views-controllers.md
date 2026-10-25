# Plano de Refatoração — Módulo de Usuários

## 1. Objetivo

Reduzir a complexidade do módulo de usuários, separar responsabilidades e adotar nomenclatura mais alinhada ao padrão do FastAPI. O arquivo `src/app/views/usuarios_views.py` acumula validação, parsing, consultas, transações, renderização e coordenação de serviços. Este plano propõe:

- Dividir o módulo em unidades menores e de responsabilidade única.
- Renomear o pacote `app.views` para `app.controllers`.
- Preservar o comportamento atual e os testes existentes.

---

## 2. Requisitos

### RQ01 — Responsabilidade única por módulo
Cada novo arquivo deve ter uma única responsabilidade clara:

| Módulo | Responsabilidade |
|---|---|
| `controllers/usuarios/handlers.py` | Definir os endpoints FastAPI (receber request, chamar serviços, devolver response). |
| `controllers/usuarios/forms.py` | Fazer parsing dos dados brutos do formulário (`request.form()`) para objetos tipados. |
| `controllers/usuarios/validators.py` | Aplicar validações de negócio específicas do formulário web. |
| `controllers/usuarios/context.py` | Carregar dados auxiliares (paróquias, igrejas) e montar o contexto dos templates. |
| `controllers/usuarios/router.py` | Criar e exportar o `APIRouter`, registrando os handlers. |
| `services/usuario_service.py` | Receber `UsuarioCreate`/`UsuarioUpdate` e orquestrar a criação/atualização do usuário e perfil. |
| `services/usuario_query_service.py` | Centralizar queries complexas de listagem/filtro de usuários. |

### RQ02 — Renomear pacote `views` para `controllers`
- Renomear `src/app/views/` para `src/app/controllers/`.
- Renomear referências em `src/app/main.py`.
- Renomear referências nos testes (`src/tests/test_usuarios_views.py` e Selenium, se houver imports diretos).
- Renomear `app.views.deps` para `app.controllers.deps`.

### RQ03 — Preservar comportamento atual
Manter as regras já implementadas e testadas:

- Autocadastro público força perfil `DIZIMISTA`, usuário inativo, status `PENDENTE` e ignora `numero_registro`.
- Administrador pode criar/editar administradores e dizimistas.
- Alterações apenas no `PerfilDizimista` atualizam `Usuario.atualizado_em`.
- Validação de unicidade do número de registro respeita o perfil em edição.

### RQ04 — Facilitar testes unitários
A separação deve permitir testar validações e parsing sem subir a aplicação FastAPI e sem banco de dados.

### RQ05 — Corrigir avisos de depreciação
Aproveitar a refatoração para substituir `HTTP_422_UNPROCESSABLE_ENTITY` por `HTTP_422_UNPROCESSABLE_CONTENT` nos status code de retorno.

---

## 3. Estrutura de arquivos proposta

```
src/app/
├── controllers/
│   ├── __init__.py
│   ├── deps.py                 # exatamente app.views.deps, renomeado
│   ├── auth_views.py           # renomear para auth_controller.py
│   ├── paroquias_views.py      # renomear para paroquias_controller.py
│   └── usuarios/
│       ├── __init__.py
│       ├── router.py
│       ├── handlers.py
│       ├── forms.py
│       ├── validators.py
│       └── context.py
```

> **Nota**: para consistência, todos os arquivos do pacote `views` devem ser renomeados de `*_views.py` para `*_controller.py`.

---

## 4. Mapeamento das funções atuais

### 4.1. Funções que vão para `controllers/usuarios/context.py`

| Função atual | Responsabilidade |
|---|---|
| `_carregar_paroquias` | Query de paróquias com `selectinload(Paroquia.igrejas)`. |
| `_carregar_igrejas` | Query de igrejas ordenadas por nome. |
| `_render_formulario` | Montar `TemplateResponse` para `usuarios/formulario.html`. |

### 4.2. Funções que vão para `controllers/usuarios/forms.py`

| Função atual | Responsabilidade |
|---|---|
| Parâmetros `Form(...)` do POST `/novo` e POST `/{id}/editar` | Fazer `await request.form()` e converter para dataclass tipada. |
| `_parse_numero_registro` | Converter string do formulário em `int` ou mensagem de erro. |

### 4.3. Funções que vão para `controllers/usuarios/validators.py`

| Lógica atual | Responsabilidade |
|---|---|
| Validação de e-mail/senha obrigatórios por perfil | Regras de preenchimento do formulário. |
| Validação de `confirmar_senha` | Garantir igualdade entre senha e confirmação. |
| Validação de `paroquia_id` para administrador | Regra de negócio específica. |
| Validação de `igreja_id` para dizimista | Regra de negócio específica. |
| Validação de unicidade do número de registro | Chamar `perfil_dizimista_service` e traduzir exceção em mensagem. |

### 4.4. Funções que vão para `controllers/usuarios/handlers.py`

| Endpoint atual | Handler |
|---|---|
| `GET /usuarios/novo` | `formulario_cadastro_usuario` |
| `POST /usuarios/novo` | `cadastrar_usuario_via_formulario` |
| `GET /usuarios` | `listar_usuarios_view` |
| `GET /usuarios/{id}` | `detalhes_usuario_view` |
| `GET /usuarios/{id}/editar` | `formulario_editar_usuario` |
| `POST /usuarios/{id}/editar` | `editar_usuario_via_formulario` |
| `POST /usuarios/{id}/excluir` | `excluir_usuario_via_formulario` |

### 4.5. Funções que vão para `services/`

| Função atual | Novo local | Motivo |
|---|---|---|
| `listar_usuarios_paginado` | `services/usuario_query_service.py` | É uma query de domínio, não de apresentação. |
| Criação de `PerfilDizimista` junto com `Usuario` | `services/usuario_service.py` | A lógica de "criar usuário + perfil" deve ser atômica e testável independentemente da interface web. |
| Atualização de `PerfilDizimista` com atualização de `Usuario.atualizado_em` | `services/usuario_service.py` | Regra de negócio que não depende do formulário. |

---

## 5. Passo a passo da refatoração

### Passo 1 — Criar novo pacote `controllers`
- Criar `src/app/controllers/`.
- Copiar o conteúdo de `src/app/views/` para `src/app/controllers/`.
- Renomear arquivos:
  - `auth_views.py` → `auth_controller.py`
  - `paroquias_views.py` → `paroquias_controller.py`
  - `usuarios_views.py` → `usuarios/router.py`, `usuarios/handlers.py`, etc.

### Passo 2 — Atualizar imports internos
Substituir todos os imports de `app.views.*` para `app.controllers.*` dentro dos próprios controllers e em:

- `src/app/main.py`
- `src/tests/test_usuarios_views.py`
- `src/tests/selenium/*` (se houver imports diretos)

### Passo 3 — Extrair validação e parsing
- Criar `UsuarioCreateForm` e `UsuarioUpdateForm` em `controllers/usuarios/forms.py`.
- Mover `_parse_numero_registro` para `forms.py`.
- Criar função `validar_formulario_usuario(...)` em `validators.py`.

### Passo 4 — Extrair contexto de template
- Mover `_carregar_paroquias`, `_carregar_igrejas` e `_render_formulario` para `context.py`.
- Tornar `renderizar_formulario_usuario(...)` a interface pública.

### Passo 5 — Mover queries para services
- Mover `listar_usuarios_paginado` para `services/usuario_query_service.py`.
- Importá-lo em `controllers/usuarios/handlers.py`.

### Passo 6 — Simplificar os handlers
Cada handler deve ter no máximo:

1. Receber request + dependências.
2. Carregar dados do formulário (via forms.py).
3. Validar (via validators.py).
4. Chamar service de domínio.
5. Renderizar/redirect (via context.py).

### Passo 7 — Remover pacote `views`
Após confirmar que todos os imports foram atualizados:
- Remover `src/app/views/`.

### Passo 8 — Ajustar testes
- Renomear `test_usuarios_views.py` para `test_usuarios_controller.py`.
- Atualizar imports.
- Garantir cobertura das validações extraídas.

### Passo 9 — Corrigir depreciação
- Substituir `status.HTTP_422_UNPROCESSABLE_ENTITY` por `status.HTTP_422_UNPROCESSABLE_CONTENT`.

### Passo 10 — Executar suite completa
```bash
pytest
```

---

## 6. Impactos do renomeio de `views` para `controllers`

| Arquivo / local | Impacto | Ação |
|---|---|---|
| `src/app/main.py` | Importa `usuario_views` e `auth_views` | Atualizar para `app.controllers.usuarios.router` e `app.controllers.auth_controller`. |
| `src/app/views/deps.py` | Nome do pacote muda | Mover para `src/app/controllers/deps.py`. |
| `src/tests/test_usuarios_views.py` | Nome e imports | Renomear e atualizar. |
| Templates e static | Não referenciam o pacote Python | Sem impacto. |
| `alembic`, `models`, `schemas`, `services` | Não dependem do pacote views | Sem impacto. |
| Docker / Makefile | Não referenciam pacote views | Sem impacto. |

---

## 7. Decisões pendentes a confirmar

Antes de gerar o código, preciso confirmar com você:

1. **Scope do renomeio**: quer renomear **apenas** `usuarios_views.py` para controllers, ou **todos** os arquivos do pacote `views` (`auth_views.py`, `paroquias_views.py`) para manter consistência?
2. **Class Based Views**: descartamos CBV e seguimos com funções separadas em módulos, conforme discutido?
3. **Novo service para queries**: aceita criar `services/usuario_query_service.py` para `listar_usuarios_paginado`, ou prefere mantê-lo em `services/usuario_service.py`?
4. **Form como dataclass ou Pydantic**: prefere `dataclass` simples ou um model Pydantic para representar os dados do formulário web?

---

## 8. Recomendação de execução

Aplicar a refatoração em duas entregas:

1. **Entrega 1 — reestruturação interna do módulo de usuários**: dividir `usuarios_views.py` em handlers/forms/validators/context, sem renomear o pacote.
2. **Entrega 2 — renomear `views` para `controllers`**: mover arquivos e atualizar imports em toda a base.

Isso facilita a revisão e torna mais fácil identificar onde algo quebrou.

---

## 9. Critérios de aceitação

- [ ] `usuarios_views.py` não existe mais ou tem menos de 80 linhas.
- [ ] Todo código de validação está em `validators.py` e é testável sem subir a aplicação.
- [ ] Todo código de parsing está em `forms.py`.
- [ ] Todo código de montagem de contexto/template está em `context.py`.
- [ ] `app.views` foi renomeado para `app.controllers`.
- [ ] Todos os testes unitários e Selenium continuam passando.
- [ ] Nenhum `HTTP_422_UNPROCESSABLE_ENTITY` permanece no módulo.
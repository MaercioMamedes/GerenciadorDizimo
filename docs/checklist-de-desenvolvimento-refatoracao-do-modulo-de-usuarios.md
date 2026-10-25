# Checklist de Desenvolvimento — Refatoração do Módulo de Usuários

> **Sprint atual**: refatoração estrutural do módulo de usuários.
> **Fora do escopo**: busca, filtros avançados e novas funcionalidades (próximo sprint).

---

## Entrega 1 — Reestruturação interna do módulo de usuários

### 1. Criar estrutura do novo pacote

- [x] Criar diretório `src/app/controllers/usuarios/`
- [x] Criar `src/app/controllers/usuarios/__init__.py`
- [x] Criar `src/app/controllers/usuarios/router.py`
- [x] Criar `src/app/controllers/usuarios/handlers.py`
- [x] Criar `src/app/controllers/usuarios/forms.py`
- [x] Criar `src/app/controllers/usuarios/validators.py`
- [x] Criar `src/app/controllers/usuarios/context.py`

### 2. Extrair parsing de formulários (`forms.py`)

- [x] Criar dataclass/Pydantic `UsuarioCreateForm`
- [x] Criar dataclass/Pydantic `UsuarioUpdateForm`
- [x] Mover `_parse_numero_registro` para `forms.py`
- [x] Implementar função `parse_formulario_criacao(request)` → `UsuarioCreateForm`
- [x] Implementar função `parse_formulario_edicao(request)` → `UsuarioUpdateForm`

### 3. Extrair validações (`validators.py`)

- [x] Criar `validar_formulario_criacao(form, eh_admin)`
- [x] Criar `validar_formulario_edicao(form)`
- [x] Validar obrigatoriedade de e-mail/senha por perfil
- [x] Validar igualdade de senha e confirmação
- [x] Validar `paroquia_id` obrigatória para administrador
- [x] Validar `igreja_id` obrigatória para dizimista
- [x] Validar unicidade de `numero_registro` respeitando o perfil em edição
- [x] Retornar lista de mensagens de erro em vez de levantar exceção de template

### 4. Extrair contexto de templates (`context.py`)

- [x] Mover `_carregar_paroquias` para `context.py`
- [x] Mover `_carregar_igrejas` para `context.py`
- [x] Mover `_render_formulario` para `context.py` como `renderizar_formulario_usuario(...)`
- [x] Manter carregamento eager de `Paroquia.igrejas` para a property `nome` funcionar

### 5. Criar handlers enxutos (`handlers.py`)

- [ ] Implementar `GET /usuarios/novo`
- [ ] Implementar `POST /usuarios/novo`
- [ ] Implementar `GET /usuarios`
- [ ] Implementar `GET /usuarios/{id}`
- [ ] Implementar `GET /usuarios/{id}/editar`
- [ ] Implementar `POST /usuarios/{id}/editar`
- [ ] Implementar `POST /usuarios/{id}/excluir`
- [ ] Garantir que cada handler tenha no máximo: receber request, parse, validar, chamar service, responder

### 6. Criar/exportar router (`router.py`)

- [x] Importar todos os handlers
- [x] Criar `APIRouter(prefix="/usuarios", tags=["Controllers - Usuários"])`
- [x] Registrar todas as rotas mantendo a ordem correta (`/{id}` antes de `/{id}/editar`)

### 7. Refatorar serviços

- [x] Criar `src/app/services/usuario_query_service.py`
- [x] Mover `listar_usuarios_paginado` para `usuario_query_service.py`
- [x] Ajustar `services/usuario_service.py` para orquestrar `Usuario` + `PerfilDizimista`
- [x] Garantir que alterações apenas em `PerfilDizimista` atualizem `Usuario.atualizado_em`
- [x] Preservar lógica de exclusão com soft delete ou hard delete (conforme implementado)

### 8. Ajustar `src/app/main.py`

- [x] Substituir import de `app.views.usuarios_views` por `app.controllers.usuarios.router`
- [x] Substituir import de `app.views.auth_views` por `app.controllers.auth_views` (provavelmente mantido temporariamente)
- [x] Substituir import de `app.views.paroquias_views` por `app.controllers.paroquias_views` (provavelmente mantido temporariamente)

### 9. Corrigir status code depreciado

- [x] Substituir `status.HTTP_422_UNPROCESSABLE_ENTITY` por `status.HTTP_422_UNPROCESSABLE_CONTENT`
- [x] Verificar que não restam referências ao status antigo no módulo de usuários

### 10. Testes da Entrega 1

- [x] Garantir que `pytest` unitário passa
- [x] Garantir que `pytest -m selenium` passa
- [x] Verificar que não há warnings de depreciação restantes

---

## Entrega 2 — Renomear pacote `views` para `controllers`

### 1. Renomear arquivos existentes

- [x] Copiar/mover `src/app/views/deps.py` → `src/app/controllers/deps.py`
- [x] Renomear `src/app/views/auth_views.py` → `src/app/controllers/auth_controller.py`
- [x] Renomear `src/app/views/paroquias_views.py` → `src/app/controllers/paroquias_controller.py`

### 2. Atualizar imports em toda a base

- [x] Atualizar `src/app/main.py`
- [x] Atualizar `src/app/controllers/auth_controller.py`
- [x] Atualizar `src/app/controllers/paroquias_controller.py`
- [x] Atualizar `src/app/controllers/usuarios/handlers.py`
- [x] Atualizar `src/app/services/*` (se houver imports de `app.views.deps`)

### 3. Ajustar testes

- [x] Renomear `src/tests/test_usuarios_views.py` → `src/tests/test_usuarios_controller.py`
- [x] Atualizar imports nos testes unitários
- [x] Atualizar imports nos testes Selenium (se houver)
- [x] Garantir cobertura das novas funções de `forms.py` e `validators.py`

### 4. Remover pacote antigo

- [x] Remover diretório `src/app/views/`
- [x] Verificar que não restam imports quebrados

### 5. Testes da Entrega 2

- [x] Executar `pytest` completo
- [x] Executar `pytest -m selenium`
- [x] Verificar que todos os testes passam

---

## Validação final

- [x] `usuarios_views.py` não existe mais
- [x] Código de validação está em `validators.py` e é testável sem FastAPI/banco
- [x] Código de parsing está em `forms.py`
- [x] Código de contexto/template está em `context.py`
- [x] `app.views` foi renomeado para `app.controllers`
- [x] Nenhum `HTTP_422_UNPROCESSABLE_ENTITY` restante
- [x] Todos os testes unitários passam
- [x] Todos os testes Selenium passam
- [x] Comportamentos preservados:
  - [x] Autocadastro público força perfil `DIZIMISTA`, inativo, `PENDENTE`, sem `numero_registro`
  - [x] Admin pode criar/editar admin e dizimista
  - [x] Mudanças apenas no `PerfilDizimista` atualizam `Usuario.atualizado_em`
  - [x] Unicidade de `numero_registro` respeita o perfil em edição

---

## Pós-refatoração (backlog próximo sprint)

- [ ] Implementar busca por nome parcial na listagem
- [ ] Implementar filtros por perfil, igreja, status de cadastro e período
- [ ] Adicionar ordenação por colunas na tabela
- [ ] Avaliar extração de lógica de filtros complexos para `usuario_query_service.py`

---

## Comandos úteis

```bash
# Testes unitários
pytest -m "not selenium" -v

# Testes Selenium
pytest -m selenium -v

# Verificar referências residuais a app.views
grep -r "app.views" src/

# Verificar status depreciado
grep -r "HTTP_422_UNPROCESSABLE_ENTITY" src/
```
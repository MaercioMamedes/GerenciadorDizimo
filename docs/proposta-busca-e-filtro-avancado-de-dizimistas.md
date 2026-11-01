# Proposta Técnica — Busca e Filtro Avançado de Dizimistas

## Objetivo

Implementar na tela **Usuários Cadastrados** um mecanismo de busca e filtro que permita:

- **Busca textual:** nome parcial ou completo do dizimista.
- **Busca por número de registro.**
- **Busca por data de nascimento.**
- **Filtros rápidos:** Ativo/Inativo, Aprovado/Pendente/Rejeitado.
- **Preparação futura:** filtros temporais de contribuição (30, 90, 180 dias) e não-contribuição em range definido.

---

## 1. Entrada de Dados no Frontend

Adicionar na parte superior da listagem (`usuarios/lista.html`) um painel compacto de busca com os seguintes campos:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `q` | text | Nome parcial ou completo |
| `numero_registro` | text | Número de registro do dizimista |
| `data_nascimento` | date | Data de nascimento exata |
| `ativo` | select | Todos / Ativo / Inativo |
| `status_cadastro` | select | Todos / Pendente / Aprovado / Rejeitado |
| `contribuicao` | select *(preparado)* | Todos / Contribuiu nos últimos 30 dias / 90 dias / 180 dias / Não contribuiu em período |

A seleção de "Não contribuiu em período" pode, em uma segunda etapa, abrir um datepicker para range (`data_inicio`, `data_fim`).

---

## 2. Contrato do Endpoint

O endpoint de listagem deve aceitar query parameters opcionais:

```http
GET /usuarios?q=Maria&numero_registro=123&data_nascimento=1985-06-15&ativo=true&status_cadastro=aprovado&contribuicao=ultimos_30_dias
```

### Mapeamento dos parâmetros

```python
from datetime import date
from typing import Literal

class FiltroListagemUsuarios:
    q: str | None                    # nome parcial/completo
    numero_registro: int | None
    data_nascimento: date | None
    ativo: bool | None
    status_cadastro: Literal["pendente", "aprovado", "rejeitado"] | None
    contribuicao: Literal[
        "todos",
        "ultimos_30_dias",
        "ultimos_90_dias",
        "ultimos_180_dias",
        "nao_contribuiu_periodo",
    ] | None
    contribuicao_inicio: date | None   # usado com nao_contribuiu_periodo
    contribuicao_fim: date | None
```

---

## 3. Camada de Query Service

Criar ou estender `app/services/usuario_query_service.py` com uma função dedicada:

```python
async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
    filtros: FiltroListagemUsuarios | None = None,
) -> dict:
    ...
```

A função deve:

1. Montar a query base com joins opcionais em `perfil_dizimista`.
2. Aplicar cada filtro de forma condicional.
3. Adicionar o filtro de contribuição por subquery quando solicitado.

### Exemplo de aplicação dos filtros

```python
from datetime import date, timedelta
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.models.contribuicao import Contribuicao
from app.models.perfil_dizimista import PerfilDizimista, StatusCadastro
from app.models.usuario import PerfilUsuario, Usuario


async def listar_usuarios_paginado(
    db: AsyncSession,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: PerfilUsuario | None = None,
    filtros: FiltroListagemUsuarios | None = None,
):
    filtros = filtros or FiltroListagemUsuarios()

    stmt = (
        select(Usuario)
        .outerjoin(Usuario.perfil_dizimista)
        .options(selectinload(Usuario.perfil_dizimista))
    )

    # Filtro por perfil
    if perfil:
        stmt = stmt.where(Usuario.perfil == perfil)

    # Filtro textual no nome
    if filtros.q:
        stmt = stmt.where(Usuario.nome.ilike(f"%{filtros.q}%"))

    # Filtro por número de registro
    if filtros.numero_registro:
        stmt = stmt.where(PerfilDizimista.numero_registro == filtros.numero_registro)

    # Filtro por data de nascimento
    if filtros.data_nascimento:
        stmt = stmt.where(Usuario.data_nascimento == filtros.data_nascimento)

    # Filtro por ativo/inativo
    if filtros.ativo is not None:
        stmt = stmt.where(Usuario.ativo == filtros.ativo)

    # Filtro por status de cadastro
    if filtros.status_cadastro:
        stmt = stmt.where(
            PerfilDizimista.status_cadastro == StatusCadastro(filtros.status_cadastro)
        )

    # Filtro temporal de contribuição
    stmt = _aplicar_filtro_contribuicao(stmt, filtros)

    # Ordenação padrão
    stmt = stmt.order_by(Usuario.nome)

    # Paginação
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    resultado = await db.execute(
        stmt.offset((pagina - 1) * tamanho_pagina).limit(tamanho_pagina)
    )
    usuarios = resultado.scalars().unique().all()

    return {
        "usuarios": usuarios,
        "total": total,
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "total_paginas": (total + tamanho_pagina - 1) // tamanho_pagina if total else 1,
    }
```

---

## 4. Filtro Temporal de Contribuição

A função `_aplicar_filtro_contribuicao` deve ser extensível para os cenários futuros:

```python
def _aplicar_filtro_contribuicao(stmt, filtros):
    if not filtros.contribuicao or filtros.contribuicao == "todos":
        return stmt

    hoje = date.today()

    if filtros.contribuicao == "ultimos_30_dias":
        return _com_contribuicao_no_periodo(stmt, hoje - timedelta(days=30), hoje)

    if filtros.contribuicao == "ultimos_90_dias":
        return _com_contribuicao_no_periodo(stmt, hoje - timedelta(days=90), hoje)

    if filtros.contribuicao == "ultimos_180_dias":
        return _com_contribuicao_no_periodo(stmt, hoje - timedelta(days=180), hoje)

    if filtros.contribuicao == "nao_contribuiu_periodo":
        inicio = filtros.contribuicao_inicio or hoje - timedelta(days=180)
        fim = filtros.contribuicao_fim or hoje
        return _sem_contribuicao_no_periodo(stmt, inicio, fim)

    return stmt
```

### Contribuiu no período

```python
def _com_contribuicao_no_periodo(stmt, data_inicio, data_fim):
    subquery = (
        select(Contribuicao.usuario_id)
        .where(
            Contribuicao.data_contribuicao >= data_inicio,
            Contribuicao.data_contribuicao <= data_fim,
        )
        .distinct()
        .subquery()
    )
    return stmt.where(Usuario.id.in_(subquery))
```

### Não contribuiu no período

```python
def _sem_contribuicao_no_periodo(stmt, data_inicio, data_fim):
    subquery = (
        select(Contribuicao.usuario_id)
        .where(
            Contribuicao.data_contribuicao >= data_inicio,
            Contribuicao.data_contribuicao <= data_fim,
        )
        .distinct()
        .subquery()
    )
    return stmt.where(~Usuario.id.in_(subquery))
```

> **Nota:** O modelo `Contribuicao` e a coluna `data_contribuicao` presumem-se já existentes no projeto. Se o nome for diferente, ajustar conforme a modelagem real.

---

## 5. Controller

Atualizar `app/controllers/usuarios/listagem.py` para receber os novos parâmetros:

```python
from dataclasses import dataclass
from datetime import date

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.deps import require_admin_view
from app.core.templates import templates
from app.db.session import get_db
from app.services.usuario_query_service import (
    FiltroListagemUsuarios,
    listar_usuarios_paginado,
)


@dataclass
class FiltroListagemUsuarios:
    q: str | None = None
    numero_registro: int | None = None
    data_nascimento: date | None = None
    ativo: bool | None = None
    status_cadastro: str | None = None
    contribuicao: str | None = None
    contribuicao_inicio: date | None = None
    contribuicao_fim: date | None = None


async def listar_usuarios_view(
    request: Request,
    pagina: int = 1,
    tamanho_pagina: int = 10,
    perfil: str | None = None,
    q: str | None = None,
    numero_registro: int | None = None,
    data_nascimento: date | None = None,
    ativo: str | None = None,            # "true", "false" ou None
    status_cadastro: str | None = None,
    contribuicao: str | None = None,
    contribuicao_inicio: date | None = None,
    contribuicao_fim: date | None = None,
    usuario_atual=Depends(require_admin_view),
    db: AsyncSession = Depends(get_db),
):
    from app.models.usuario import PerfilUsuario

    perfil_enum = None
    if perfil:
        try:
            perfil_enum = PerfilUsuario(perfil)
        except ValueError:
            perfil_enum = None

    ativo_bool = None
    if ativo is not None:
        ativo_bool = ativo.lower() == "true"

    filtros = FiltroListagemUsuarios(
        q=q,
        numero_registro=numero_registro,
        data_nascimento=data_nascimento,
        ativo=ativo_bool,
        status_cadastro=status_cadastro,
        contribuicao=contribuicao,
        contribuicao_inicio=contribuicao_inicio,
        contribuicao_fim=contribuicao_fim,
    )

    resultado = await listar_usuarios_paginado(
        db,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
        perfil=perfil_enum,
        filtros=filtros,
    )

    return templates.TemplateResponse(
        request,
        "usuarios/lista.html",
        {
            "usuario_atual": usuario_atual,
            "perfil_filtro": perfil_enum.value if perfil_enum else "",
            "filtros": filtros,
            **resultado,
        },
    )
```

---

## 6. Template HTML

Alterar `templates/usuarios/lista.html` para incluir o painel de busca acima da tabela:

```html
<form method="get" action="/usuarios" class="row g-3 mb-4">
  <input type="hidden" name="perfil" value="{{ perfil_filtro }}">

  <div class="col-md-3">
    <label for="q" class="form-label">Nome</label>
    <input type="text" class="form-control" id="q" name="q" value="{{ filtros.q or '' }}">
  </div>

  <div class="col-md-2">
    <label for="numero_registro" class="form-label">Nº Registro</label>
    <input type="text" class="form-control" id="numero_registro" name="numero_registro" value="{{ filtros.numero_registro or '' }}">
  </div>

  <div class="col-md-2">
    <label for="data_nascimento" class="form-label">Nascimento</label>
    <input type="date" class="form-control" id="data_nascimento" name="data_nascimento" value="{{ filtros.data_nascimento or '' }}">
  </div>

  <div class="col-md-2">
    <label for="ativo" class="form-label">Status</label>
    <select class="form-select" id="ativo" name="ativo">
      <option value="">Todos</option>
      <option value="true" {% if filtros.ativo is true %}selected{% endif %}>Ativo</option>
      <option value="false" {% if filtros.ativo is false %}selected{% endif %}>Inativo</option>
    </select>
  </div>

  <div class="col-md-2">
    <label for="status_cadastro" class="form-label">Cadastro</label>
    <select class="form-select" id="status_cadastro" name="status_cadastro">
      <option value="">Todos</option>
      <option value="pendente" {% if filtros.status_cadastro == 'pendente' %}selected{% endif %}>Pendente</option>
      <option value="aprovado" {% if filtros.status_cadastro == 'aprovado' %}selected{% endif %}>Aprovado</option>
      <option value="rejeitado" {% if filtros.status_cadastro == 'rejeitado' %}selected{% endif %}>Rejeitado</option>
    </select>
  </div>

  <div class="col-md-2">
    <label for="contribuicao" class="form-label">Contribuição</label>
    <select class="form-select" id="contribuicao" name="contribuicao">
      <option value="todos">Todos</option>
      <option value="ultimos_30_dias" {% if filtros.contribuicao == 'ultimos_30_dias' %}selected{% endif %}>Contribuiu nos últimos 30 dias</option>
      <option value="ultimos_90_dias" {% if filtros.contribuicao == 'ultimos_90_dias' %}selected{% endif %}>Contribuiu nos últimos 90 dias</option>
      <option value="ultimos_180_dias" {% if filtros.contribuicao == 'ultimos_180_dias' %}selected{% endif %}>Contribuiu nos últimos 180 dias</option>
      <option value="nao_contribuiu_periodo" {% if filtros.contribuicao == 'nao_contribuiu_periodo' %}selected{% endif %}>Não contribuiu no período</option>
    </select>
  </div>

  <div class="col-md-2 d-flex align-items-end">
    <button type="submit" class="btn btn-primary w-100">Buscar</button>
  </div>
</form>
```

---

## 7. Considerações de UX

- Preservar os filtros ao navegar entre páginas: os links de paginação devem replicar os query parameters atuais.
- Limpar filtros: adicionar botão secundário "Limpar" que redireciona para `/usuarios`.
- Se o usuário não tiver `perfil_dizimista`, os filtros de `numero_registro`, `status_cadastro` e `contribuicao` devem ser ignorados na query (a modelagem já lida com isso via `outerjoin`).

---

## 8. Testes Recomendados

| Teste | Tipo |
|-------|------|
| Busca por nome parcial retorna resultados corretos | Unitário/Integração |
| Busca por número de registro | Integração |
| Busca por data de nascimento | Integração |
| Filtro ativo/inativo | Integração |
| Filtro aprovado/pendente/rejeitado | Integração |
| Filtro de contribuição nos últimos 30/90/180 dias | Integração |
| Filtro de não contribuição em range | Integração |
| Preservação de filtros na paginação | Selenium |

---

## 9. Próximos Passos

1. Validar se a modelagem de `Contribuicao` está alinhada com os nomes de coluna usados aqui.
2. Implementar `FiltroListagemUsuarios` e atualizar `usuario_query_service.py`.
3. Ajustar `listagem.py` para receber os parâmetros.
4. Atualizar o template `usuarios/lista.html`.
5. Adicionar testes de integração e Selenium.
6. _(Futuro)_ Habilitar o datepicker de range quando o filtro "Não contribuiu no período" for selecionado.
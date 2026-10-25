"""Parsing dos formulários web de criação e edição de usuários."""

from dataclasses import dataclass
from typing import Optional

from fastapi import Request


@dataclass
class UsuarioCreateForm:
    """Representa os campos brutos enviados no POST /usuarios/novo."""

    nome: str
    email: Optional[str]
    senha: Optional[str]
    confirmar_senha: Optional[str]
    telefone: Optional[str]
    data_nascimento: Optional[str]
    perfil: str
    paroquia_id: Optional[str]
    ativo: bool
    tambem_dizimista: bool
    igreja_id: Optional[str]
    numero_registro: Optional[str]
    endereco: Optional[str]
    bairro: Optional[str]
    cidade: Optional[str]
    status_cadastro: str


@dataclass
class UsuarioUpdateForm:
    """Representa os campos brutos enviados no POST /usuarios/{id}/editar."""

    nome: str
    email: Optional[str]
    telefone: Optional[str]
    data_nascimento: Optional[str]
    perfil: str
    paroquia_id: Optional[str]
    ativo: bool
    tambem_dizimista: bool
    igreja_id: Optional[str]
    numero_registro: Optional[str]
    endereco: Optional[str]
    bairro: Optional[str]
    cidade: Optional[str]
    status_cadastro: Optional[str]


def parse_numero_registro(valor: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    """Converte o valor do formulário em int ou retorna mensagem de erro."""
    if not valor or not valor.strip():
        return None, None
    try:
        numero = int(valor.strip())
        if numero < 1:
            return None, "Número de registro deve ser maior que zero."
        return numero, None
    except ValueError:
        return None, "Número de registro deve ser um número inteiro positivo."


async def parse_formulario_criacao(request: Request) -> UsuarioCreateForm:
    """Faz parsing dos dados brutos do formulário de criação."""
    form = await request.form()
    return UsuarioCreateForm(
        nome=_obter_str(form, "nome", default=""),
        email=_obter_str(form, "email"),
        senha=_obter_str(form, "senha"),
        confirmar_senha=_obter_str(form, "confirmar_senha"),
        telefone=_obter_str(form, "telefone"),
        data_nascimento=_obter_str(form, "data_nascimento"),
        perfil=_obter_str(form, "perfil", default="dizimista"),
        paroquia_id=_obter_str(form, "paroquia_id"),
        ativo=_obter_bool(form, "ativo"),
        tambem_dizimista=_obter_bool(form, "tambem_dizimista"),
        igreja_id=_obter_str(form, "igreja_id"),
        numero_registro=_obter_str(form, "numero_registro"),
        endereco=_obter_str(form, "endereco"),
        bairro=_obter_str(form, "bairro"),
        cidade=_obter_str(form, "cidade"),
        status_cadastro=_obter_str(form, "status_cadastro", default="pendente"),
    )


async def parse_formulario_edicao(request: Request) -> UsuarioUpdateForm:
    """Faz parsing dos dados brutos do formulário de edição."""
    form = await request.form()
    return UsuarioUpdateForm(
        nome=_obter_str(form, "nome", default=""),
        email=_obter_str(form, "email"),
        telefone=_obter_str(form, "telefone"),
        data_nascimento=_obter_str(form, "data_nascimento"),
        perfil=_obter_str(form, "perfil", default="dizimista"),
        paroquia_id=_obter_str(form, "paroquia_id"),
        ativo=_obter_bool(form, "ativo"),
        tambem_dizimista=_obter_bool(form, "tambem_dizimista"),
        igreja_id=_obter_str(form, "igreja_id"),
        numero_registro=_obter_str(form, "numero_registro"),
        endereco=_obter_str(form, "endereco"),
        bairro=_obter_str(form, "bairro"),
        cidade=_obter_str(form, "cidade"),
        status_cadastro=_obter_str(form, "status_cadastro"),
    )


def _obter_str(form, campo: str, default: Optional[str] = None) -> Optional[str]:
    valor = form.get(campo)
    if valor is None:
        return default
    valor_limpo = str(valor).strip()
    return valor_limpo if valor_limpo else default


def _obter_bool(form, campo: str) -> bool:
    """Interpreta checkbox do HTML: presente = True, ausente = False."""
    return form.get(campo) is not None

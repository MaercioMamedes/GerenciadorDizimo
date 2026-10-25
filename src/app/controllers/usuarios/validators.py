"""Validações dos formulários web de criação e edição de usuários."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.usuarios.forms import (
    UsuarioCreateForm,
    UsuarioUpdateForm,
    parse_numero_registro,
)
from app.models.usuario import PerfilUsuario
from app.services.perfil_dizimista_service import validar_numero_registro_unico


async def validar_formulario_criacao(
    form: UsuarioCreateForm,
    eh_admin: bool,
    db: AsyncSession,
) -> tuple[list[str], Optional[int]]:
    """Valida o formulário de criação e retorna (erros, numero_registro_int).

    A validação de unicidade de número de registro só ocorre quando o
    perfil resultante for de dizimista.
    """
    erros: list[str] = []

    perfil_enum = _parse_perfil(form.perfil)
    eh_dizimista = _eh_dizimista(perfil_enum, form.tambem_dizimista)

    # Obrigatoriedade de e-mail/senha conforme o contexto/perfil
    if perfil_enum == PerfilUsuario.ADMINISTRADOR:
        if not form.email:
            erros.append("E-mail é obrigatório para o perfil Administrador.")
        if not form.senha:
            erros.append("Senha é obrigatória para o perfil Administrador.")
        if not form.paroquia_id:
            erros.append("Paróquia é obrigatória para o perfil Administrador.")
    elif not eh_admin:
        # Autocadastro público exige e-mail/senha para criação da conta
        if not form.email:
            erros.append("E-mail é obrigatório para o cadastro.")
        if not form.senha:
            erros.append("Senha é obrigatória para o cadastro.")

    # Confirmação de senha
    if form.senha and form.confirmar_senha and form.senha != form.confirmar_senha:
        erros.append("As senhas informadas não coincidem.")

    # Igreja obrigatória quando o resultado for dizimista
    if eh_dizimista and not form.igreja_id:
        erros.append("Selecione a igreja para o perfil de Dizimista.")

    # Número de registro: parsing e unicidade
    numero_registro_int, erro_numero = parse_numero_registro(form.numero_registro)
    if erro_numero:
        erros.append(erro_numero)

    if numero_registro_int and eh_dizimista:
        try:
            await validar_numero_registro_unico(db, numero_registro_int)
        except Exception as exc:
            erros.append(str(exc))

    return erros, numero_registro_int


async def validar_formulario_edicao(
    form: UsuarioUpdateForm,
    db: AsyncSession,
    perfil_dizimista_id: Optional[int] = None,
) -> tuple[list[str], Optional[int]]:
    """Valida o formulário de edição e retorna (erros, numero_registro_int).

    O `perfil_dizimista_id` deve ser o id do `PerfilDizimista` existente, quando
    houver, para que a validação de unicidade desconsidere o próprio registro.
    """
    erros: list[str] = []

    perfil_enum = _parse_perfil(form.perfil)
    eh_dizimista = _eh_dizimista(perfil_enum, form.tambem_dizimista)

    if perfil_enum == PerfilUsuario.ADMINISTRADOR and not form.paroquia_id:
        erros.append("Paróquia é obrigatória para o perfil Administrador.")

    if eh_dizimista and not form.igreja_id:
        erros.append("Selecione a igreja para o perfil de Dizimista.")

    numero_registro_int, erro_numero = parse_numero_registro(form.numero_registro)
    if erro_numero:
        erros.append(erro_numero)

    if numero_registro_int and eh_dizimista:
        try:
            await validar_numero_registro_unico(
                db, numero_registro_int, perfil_id=perfil_dizimista_id
            )
        except Exception as exc:
            erros.append(str(exc))

    return erros, numero_registro_int


def _parse_perfil(valor: str) -> PerfilUsuario:
    """Converte a string do formulário no enum de perfil, com fallback seguro."""
    try:
        return PerfilUsuario(valor)
    except ValueError:
        return PerfilUsuario.DIZIMISTA


def _eh_dizimista(perfil: PerfilUsuario, tambem_dizimista: bool) -> bool:
    """Determina se o usuário resultante terá perfil de dizimista."""
    return perfil == PerfilUsuario.DIZIMISTA or (
        perfil == PerfilUsuario.ADMINISTRADOR and tambem_dizimista
    )

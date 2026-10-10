# src/app/cli/criar_admin.py
"""
Script para criar o usuário administrador inicial.

Uso:
    python -m app.cli.criar_admin
"""
import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_senha
from app.db.session import AsyncSessionLocal
from app.models.usuario import PerfilUsuario, Usuario


async def criar_admin():
    async with AsyncSessionLocal() as db:
        print("=== Criação do Administrador Inicial ===")
        nome = input("Nome completo: ").strip()
        email = input("Email: ").strip().lower()

        # Verifica se já existe algum admin (idempotência / segurança)
        resultado = await db.execute(
            select(Usuario).where(Usuario.perfil == PerfilUsuario.ADMINISTRADOR)
        )
        if resultado.scalars().first():
            print("⚠️  Já existe um administrador cadastrado. Operação cancelada.")
            return

        senha = getpass.getpass("Senha: ")
        confirmar = getpass.getpass("Confirme a senha: ")

        if senha != confirmar:
            print("❌ As senhas não coincidem.")
            return

        if len(senha) < 8:
            print("❌ A senha deve ter no mínimo 8 caracteres.")
            return

        admin = Usuario(
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            perfil=PerfilUsuario.ADMINISTRADOR,
            ativo=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ Administrador '{nome}' ({email}) criado com sucesso.")


if __name__ == "__main__":
    asyncio.run(criar_admin())

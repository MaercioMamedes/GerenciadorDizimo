# src/app/cli/criar_paroquia.py
"""
Script para cadastrar uma Paróquia junto com sua Igreja Matriz.

Toda Paróquia é obrigatoriamente criada já vinculada a uma Igreja Matriz
(is_matriz=True). O nome e o endereço da Paróquia são, na prática, o nome
e o endereço da Igreja Matriz (não existem campos próprios na Paróquia).

Campos obrigatórios: nome da matriz, endereço da matriz.
Campos opcionais: CNPJ da paróquia (ENTER para pular).

Uso:
    python -m app.cli.criar_paroquia
"""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.igreja import Igreja
from app.models.paroquia import Paroquia


async def criar_paroquia():
    async with AsyncSessionLocal() as db:
        print("=== Cadastro de Paróquia + Igreja Matriz ===")

        nome_matriz = input("Nome da Igreja Matriz (obrigatório): ").strip()
        while not nome_matriz:
            print("❌ O nome da Igreja Matriz é obrigatório.")
            nome_matriz = input("Nome da Igreja Matriz (obrigatório): ").strip()

        endereco_matriz = input("Endereço da Igreja Matriz (obrigatório): ").strip()
        while not endereco_matriz:
            print("❌ O endereço da Igreja Matriz é obrigatório.")
            endereco_matriz = input("Endereço da Igreja Matriz (obrigatório): ").strip()

        cnpj = input("CNPJ da Paróquia (opcional, ENTER para pular): ").strip() or None

        if cnpj:
            resultado = await db.execute(select(Paroquia).where(Paroquia.cnpj == cnpj))
            if resultado.scalar_one_or_none() is not None:
                print(f"""❌ Já existe uma paróquia cadastrada com o CNPJ '{cnpj}'.
                  Operação cancelada.""")
                return

        paroquia = Paroquia(cnpj=cnpj)
        db.add(paroquia)
        await db.flush()  # garante paroquia.id antes de criar a igreja

        matriz = Igreja(
            nome=nome_matriz,
            endereco=endereco_matriz,
            is_matriz=True,
            paroquia_id=paroquia.id,
        )
        db.add(matriz)

        await db.commit()

        print(
            f"✅ Paróquia criada com sucesso!\n"
            f"   ID da Paróquia: {paroquia.id}\n"
            f"   CNPJ: {cnpj or 'não informado'}\n"
            f"   Igreja Matriz: {nome_matriz} ({endereco_matriz})"
        )


if __name__ == "__main__":
    asyncio.run(criar_paroquia())

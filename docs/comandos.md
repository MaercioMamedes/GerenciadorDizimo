### Execução de testes

#### Toda suíte de testes:
``` bash 
docker compose exec app pytest -v
```

#### Teste específico( exemplo home):
```bash
docker compose exec app pytest src/tests/test_home.py -v
```
### Subir imagens Docker

### subir imagem da aplicação no modo produção
```bash
docker compose dev up -d
```

#### subir imagem da aplicação no modo de desenvolvimento
```bash
docker compose --profile dev up -d
```

### Realizar alterarção no banco

#### realizar arquivo de migration

```bash
docker compose exec app alembic revision --autogenerate -m "MENSAGEM DE MIGRAÇÃO"
```

#### implantar migração no banco

```bash
docker compose exec app alembic upgrade head
```
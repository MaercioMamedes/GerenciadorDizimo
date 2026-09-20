### Execução de testes

#### Toda suíte de testes:
``` bash 
docker compose exec app pytest -v
```

#### Teste específico( exemplo home):

```bash
docker compose exec app pytest src/tests/test_home.py -v
```

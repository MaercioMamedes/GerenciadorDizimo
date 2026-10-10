# Resumo: Diagnóstico de Problemas nos Testes Selenium

Data: 09/10/2026

## Contexto

Ao configurar os testes E2E com Selenium (navegador Chrome real, via container `selenium/standalone-chrome`) para validar as views de cadastro, login e logout (UC03, UC04, UC13), todos os testes que dependiam de `driver.get(...)` falhavam com:

```
selenium.common.exceptions.WebDriverException: Message: unknown error: net::ERR_SSL_PROTOCOL_ERROR
```

mesmo a aplicação respondendo corretamente via HTTP puro (confirmado com `curl` dentro do próprio container Selenium).

---

## Hipóteses investigadas (e descartadas)

### 1. Enterprise policy do Chrome bloqueando HTTP
- **Hipótese**: o Chrome, por padrão, poderia estar com HTTPS-Only Mode ou HTTPS-First Mode forçado via policy.
- **Verificação**: inspecionado `/etc/opt/chrome/policies/managed/policy.json` e `chrome://policy` dentro do container `selenium`.
- **Resultado**: a policy já estava corretamente configurada:
  ```json
  {
    "DnsOverHttpsMode": "off",
    "HttpsUpgradesEnabled": false,
    "HttpsOnlyMode": "disallowed"
  }
  ```
- **Conclusão**: policy não era a causa. **Descartada.**

### 2. Redirect HTTP→HTTPS feito pelo próprio backend (FastAPI/uvicorn)
- **Hipótese**: algum middleware (`HTTPSRedirectMiddleware`) ou proxy headers mal configurados poderiam gerar um redirect 301 para HTTPS.
- **Verificação**: `curl -v` direto no `app.local:8000` e depois no IP puro do container, a partir do container Selenium.
- **Resultado**: resposta `HTTP/1.1 200 OK`, sem nenhum header de `Location` ou `Strict-Transport-Security`. Servidor respondendo HTTP puro corretamente.
- **Conclusão**: backend não era a causa. **Descartada.**

### 3. Sufixo `.local` no hostname (`app.local`) disparando heurística de mDNS
- **Hipótese**: o Chrome trata hostnames terminados em `.local` de forma especial (reservado para mDNS/Bonjour), o que poderia acionar comportamentos de segurança peculiares.
- **Verificação**: teste de diagnóstico (`driver.get` direto no IP, ex. `http://172.19.0.4:8000/...`) passou sem erro de SSL.
- **Conclusão**: confirmou que o problema estava ligado ao **hostname usado**, não à infraestrutura em si. Levou à hipótese correta a seguir.

---

## Causa raiz real (confirmada)

**O hostname `app` (nome do serviço Docker) colide com o gTLD público `.app`, que está na lista de HSTS Preload embutida no binário do Chrome.**

- Em 2015, o Google registrou o gTLD `.app` e o cadastrou na [lista de HSTS Preload](https://hstspreload.org/) dos principais navegadores — uma lista **hardcoded no próprio binário**, não configurável via policy, flag de linha de comando ou certificado.
- O Chrome resolve qualquer hostname cujo último label (rótulo) seja `app` como pertencente a esse TLD, e **força HTTPS incondicionalmente**, antes mesmo de qualquer requisição de rede ser feita.
- Isso explica por que nenhuma das tentativas abaixo resolveu o problema:
  - `--ignore-certificate-errors`
  - `--unsafely-treat-insecure-origin-as-secure=...`
  - `acceptInsecureCerts=True`
  - Enterprise policy `HttpsUpgradesEnabled: false`
  - Trocar `app.local` por `app` puro (sem `.local`) — **ainda falhava**, pois o problema nunca foi o `.local`, e sim o label `app` isoladamente.
- Esse é um problema **documentado e conhecido** desde 2019 (ver [Stack Overflow: "Prevent Chrome-Headless from enforcing ssl"](https://stackoverflow.com/questions/54736772/)), com relato de outro desenvolvedor enfrentando exatamente o mesmo cenário (serviço Docker chamado `app`, mesmo erro `ERR_SSL_PROTOCOL_ERROR`).

---

## Solução aplicada

Renomear o alias de rede do serviço `app` para algo que **não termine com o label `app`**, evitando a colisão com o gTLD.

### 1. `docker-compose.yml` — adicionado alias de rede

```yaml
services:
  app:
    container_name: dizimo_app
    networks:
      default:
        aliases:
          - webserver
```

### 2. Variável de ambiente dos testes

```bash
APP_BASE_URL=http://webserver:8000
```

### 3. Validação

```bash
docker exec dizimo_selenium curl -s http://webserver:8000/usuarios/novo -o /dev/null -w "%{http_code}\n"
# 200
```

```bash
make test-selenium
```

Resultado: **o erro `ERR_SSL_PROTOCOL_ERROR` desapareceu completamente** em todos os 7 testes da suíte. Os testes agora falham (ou passam) por motivos de lógica/seletor de aplicação — não mais por infraestrutura/rede.

---

## Lição aprendida (para o time / documentação do projeto)

> **Nunca nomear um serviço Docker (ou qualquer alias de rede) terminando em `app`, `dev`, `page`, `new`, `android`, `google`, `chrome`, `bank`, `insurance`, `foo`** ou qualquer outro gTLD presente na lista de HSTS Preload do Chrome, caso esse serviço precise ser acessado via HTTP puro por um navegador Chrome/Chromium (testes E2E, Selenium, Playwright com Chromium, etc.). A lista completa de gTLDs afetados pode ser consultada no arquivo `transport_security_state_static.json` do código-fonte do Chromium.

---

## Próximos passos (pendente de investigação)

Com o problema de SSL resolvido, a suíte agora apresenta falhas de outra natureza — a investigar:

1. `test_cadastro_dizimista_com_dados_validos`: timeout aguardando mudança de URL após submit do formulário de cadastro.
2. `test_cadastro_com_senhas_diferentes_mostra_erro`: timeout aguardando elemento `.alert-danger`.
3. `test_login_com_credenciais_validas_redireciona_para_home`: timeout no fluxo de criação/aprovação de dizimista (reusa o mesmo fluxo de cadastro do item 1).
4. `test_login_com_credenciais_invalidas_mostra_erro`: `NoSuchElementException` — elemento `id="email"` não encontrado na página `/auth/login`.
5. `test_logout_remove_sessao_e_redireciona`: mesmo problema do item 3 (depende do cadastro).

Hipótese inicial: a causa raiz pode ser única — um problema no fluxo de submit do formulário de `/usuarios/novo` (item 1) que também afeta os testes 3 e 5 (que dependem dele), e um problema separado nos seletores/estrutura da página `/auth/login` (item 4). Investigação em andamento via `curl` do HTML real das páginas e teste de debug pós-submit.
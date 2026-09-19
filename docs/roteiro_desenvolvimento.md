# Roteiro de Desenvolvimento - Sistema de Gestão de Dízimo Paroquial

## Stack Tecnológica
- **Linguagem/Framework**: Python + FastAPI
- **Banco de dados**: PostgreSQL
- **Gerenciamento de ambiente**: pyenv + Poetry
- **Containerização**: Docker
- **Arquitetura**: Monolito fullstack inicial, com estrutura preparada para evoluir para API desacoplada

---

## Fase 0 - Setup de Ambiente e Infraestrutura Base

- Configurar pyenv com versão fixa do Python.
- Inicializar projeto com Poetry, definindo estrutura de pastas (ex: `app/`, `app/routers/`, `app/models/`, `app/schemas/`, `app/services/`, `app/core/`, `tests/`).
- Configurar Docker e docker-compose com serviços: aplicação FastAPI e PostgreSQL.
- Configurar variáveis de ambiente (`.env`) para conexão com banco, segredos de autenticação (JWT), etc.
- Configurar ferramenta de migração de banco (ex: Alembic).
- Estruturar camada de configuração (`app/core/config.py`) para preparar futura extração como API pura (separação clara entre lógica de negócio e camada de apresentação).
- Definir estrutura base de testes (pytest).

**Entregável**: ambiente rodando via `docker-compose up`, com FastAPI respondendo em rota de health-check e conexão validada com Postgres.

---

## Fase 1 - Modelagem de Dados e Estrutura Base do Banco

- Modelar entidades principais a partir das premissas e RF01-RF03:
  - `paroquia`
  - `igreja` (vinculada a `paroquia`, com flag indicando se é matriz)
  - `usuario` (com perfil: administrador ou dizimista; vinculado a uma `igreja` no caso de dizimista, e a uma `paroquia` no caso de administrador)
  - `contribuicao` (vinculada a `usuario` dizimista, `igreja`, mês de referência, valor, data de registro)
- Modelar tabelas de segurança e auditoria (RF06, RF11):
  - `audit_log` (tabela genérica, com `tabela`, `operacao`, `registro_id`, `dados_anteriores`, `dados_novos`, `usuario_id`, `executado_em`)
  - `security_log` (login, logout, tentativas falhas, bloqueios de conta - RF11.1 a RF11.5)
- Modelar tabela de consentimento LGPD (RF07.3), vinculada ao cadastro do dizimista.
- Modelar tabela/campo de notificação (RF09), vinculada ao cadastro do dizimista.
- Criar migrações iniciais via Alembic.
- Implementar constraint de unicidade (dizimista + mês de referência) na tabela `contribuicao`, considerando o fluxo de correção/complemento (RF10) em vez de bloqueio simples.

**Entregável**: schema de banco criado e versionado via migrações, cobrindo UC01 a UC06 e infraestrutura de log (UC14).

---

## Fase 2 - Autenticação, Autorização e Segurança (UC13, RF08, RF11)

- Implementar cadastro de credenciais e hash de senha.
- Implementar geração/validação de token de sessão (JWT ou sessão equivalente).
- Implementar dependency de autenticação no FastAPI, propagando `usuario_id` para a sessão do Postgres via `SET LOCAL` (necessário para os triggers de auditoria da Fase 3).
- Implementar middleware/dependency de autorização por perfil (administrador/dizimista), bloqueando rotas conforme RF08.2.
- Implementar fluxo de login com registro em `security_log` (sucesso e falha) - RF11.1.
- Implementar contador de tentativas falhas e bloqueio temporário de conta - RF11.3, RF11.4.
- Implementar fluxo de logout com registro em `security_log` - RF11.2.
- Garantir, via permissões de banco, que `security_log` e `audit_log` não aceitem `UPDATE`/`DELETE` pela role da aplicação (RF06.3, RF11.5).

**Entregável**: sistema de login/logout funcional, com bloqueio por tentativas falhas e logs de segurança imutáveis. Cobre UC13.

---

## Fase 3 - Auditoria de Dados (UC14, RF06, RF12)

- Implementar função de trigger genérica `fn_audit_log` no PostgreSQL, capturando estado completo antes/depois via `row_to_json`.
- Aplicar triggers `AFTER INSERT/UPDATE/DELETE` nas tabelas monitoradas: `paroquia`, `igreja`, `usuario`, `contribuicao`.
- Revogar `DELETE`/`UPDATE` na tabela `audit_log` para a role da aplicação.
- Implementar mecanismo de fallback para falha de gravação de log (RF12.1): a operação de negócio não deve ser bloqueada por indisponibilidade do log.
- Implementar notificação visual permanente nas telas de alteração de dados quando o log estiver indisponível (RF12.2).
- Implementar registro de evento de reconciliação quando o log for restabelecido (RF12.3).

**Entregável**: qualquer escrita nas tabelas de negócio gera log de auditoria automaticamente, com garantia de imutabilidade e resiliência a falhas do subsistema de log.

---

## Fase 4 - Gestão de Paróquia, Igrejas e Usuários (UC01, UC02, UC03, UC04, UC05)

- Implementar CRUD de paróquia (RF01.1) - UC01.
- Implementar CRUD de igreja, vinculada à paróquia, com flag de matriz (RF01.2, RF01.3) - UC02.
- Implementar autocadastro de dizimista, com:
  - Seleção de igreja (RF02.5)
  - Registro de consentimento LGPD (RF07.3)
  - Status inicial "pendente" (RF02.7) - UC03
- Implementar cadastro de dizimista pelo administrador, já validado (RF02.2) - UC05.
- Implementar tela/rota de listagem de cadastros pendentes e ação de aprovar/rejeitar (RF02.3) - UC04.
- Implementar disparo de notificação ao dizimista após validação (RF09.1, RF09.2, RF09.3) - integrar com UC04.

**Entregável**: fluxo completo de estruturação organizacional (paróquia → igreja) e ciclo de vida de cadastro de dizimista, do autocadastro à validação com notificação.

---

## Fase 5 - Contribuições de Dízimo (UC06, UC07, UC08)

- Implementar registro de contribuição pelo administrador, vinculando dizimista, igreja, mês de referência e data de registro (RF03.1, RF03.2) - UC06.
- Implementar lógica de verificação de existência de contribuição no mês de referência; se existir, direcionar para fluxo de correção/complemento em vez de bloqueio (RF10.1, RF10.2) - UC06.
- Implementar exibição de histórico de alterações de uma contribuição antes de nova correção (RF10.3) - UC06.
- Implementar visualização de contribuições pelo próprio dizimista, com filtro por mês/ano (RF04.1) - UC07.
- Implementar visualização de contribuições de qualquer dizimista pelo administrador, restrito à paróquia vinculada (RF04.2) - UC08.

**Entregável**: ciclo completo de lançamento, correção e consulta de contribuições, com histórico auditável.

---

## Fase 6 - Relatórios (UC09, RF05)

- Implementar geração de relatório mensal/anual por dizimista (RF05.1, RF05.2).
- Implementar geração de relatório mensal/anual por igreja (RF05.3, RF05.4).
- Implementar geração de relatório mensal/anual geral da paróquia (RF05.5, RF05.6).
- Restringir geração/visualização de relatórios ao perfil administrador (RF05.7).
- Registrar explicitamente evento de geração de relatório em log (via aplicação, não trigger), conforme UC09.

**Entregável**: módulo de relatórios funcional, com registro de quem gerou cada relatório e quais filtros foram usados.

---

## Fase 7 - Conformidade LGPD (UC11, UC12, RF07)

- Implementar rota de consulta de dados pessoais pelo próprio dizimista (RF07.2) - UC11.
- Implementar rota de solicitação de exclusão/anonimização de dados pessoais, com anonimização via `UPDATE` nos campos pessoais e preservação do log de auditoria intacto (RF07.4) - UC12.
- Revisar todos os pontos de acesso a dados pessoais para garantir controle de acesso restrito por perfil (RF07.1).

**Entregável**: mecanismos de atendimento a direitos do titular de dados (consulta e exclusão/anonimização) implementados e auditáveis.

---

## Fase 8 - Consulta de Logs (UC10)

- Implementar tela/rota restrita a administrador para consulta de `audit_log`, com filtros por usuário, tipo de ação e período (RF06.1, RF06.2).
- Garantir que a interface não exponha opção de exclusão de logs, reforçando RF06.3 tanto na camada de aplicação quanto de banco (já implementada na Fase 3).

**Entregável**: painel de auditoria funcional para o administrador.

---

## Fase 9 - Testes e Hardening

- Testes unitários para regras de negócio críticas: bloqueio de conta, correção de contribuição, anonimização de dados.
- Testes de integração para os triggers de auditoria (garantir captura correta de `dados_anteriores`/`dados_novos`).
- Testes de carga/resiliência simulando indisponibilidade do log de auditoria (validar RF12.1 e RF12.2).
- Revisão de segurança: proteção contra SQL Injection, validação de entrada em todas as rotas, rate limiting no endpoint de login (complementar ao RF11.3).
- Revisão de conformidade LGPD com checklist final (consentimento, anonimização, controle de acesso).

**Entregável**: sistema testado e validado contra os requisitos funcionais e de segurança definidos.

---

## Fase 10 - Preparação para Evolução para API

- Revisar separação entre camada de apresentação (templates/frontend, se aplicável no monolito) e camada de serviço/domínio, garantindo que toda lógica de negócio esteja isolada em `services/`, sem acoplamento a request/response do FastAPI.
- Documentar endpoints via OpenAPI (gerado automaticamente pelo FastAPI) como base para futura exposição de API pública/mobile.

**Entregável**: base de código organizada para permitir extração futura de um front-end separado consumindo a mesma API, sem retrabalho estrutural.

---

## Backlog de Pontos Ainda Não Detalhados (a refinar antes ou durante a implementação)
- Definição do canal exato de notificação (RF09.3): e-mail, notificação interna, ou ambos.
- Definição de parâmetros configuráveis de segurança (RF11.3): número de tentativas e tempo de bloqueio.
- Definição do mecanismo de fallback de log (RF12.1): arquivo local, fila (ex: Redis/RabbitMQ) ou tabela de staging no mesmo banco.

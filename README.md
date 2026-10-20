# Gerenciador Dízimo

Sistema web para gestão de arrecadação de dízimo em paróquias católicas, com suporte a múltiplas igrejas/comunidades vinculadas a uma mesma paróquia, controle de acesso por perfil, geração de relatórios, auditoria completa e conformidade com a LGPD.

## Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades Principais](#funcionalidades-principais)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Perfis de Usuário](#perfis-de-usuário)
- [Fluxo de Criação e Gestão de Usuários](#fluxo-de-criação-e-gestão-de-usuários)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Migrações de Banco de Dados](#migrações-de-banco-de-dados)
- [Testes](#testes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Auditoria e Segurança](#auditoria-e-segurança)
- [Conformidade com a LGPD](#conformidade-com-a-lgpd)
- [Roadmap de Desenvolvimento](#roadmap-de-desenvolvimento)
- [Documentação Adicional](#documentação-adicional)
- [Licença](#licença)

## Sobre o Projeto

Uma paróquia é composta por várias igrejas/comunidades, incluindo a matriz. Cada igreja mantém sua própria arrecadação e registros de contribuições de forma individualizada, ainda que vinculada à mesma paróquia. O sistema permite que administradores cadastrem paróquias, igrejas e dizimistas, registrem e corrijam contribuições, gerem relatórios de arrecadação e consultem logs de auditoria, enquanto dizimistas podem se autocadastrar (mediante validação) e consultar apenas as próprias contribuições.

## Funcionalidades Principais

- Cadastro de paróquias e igrejas/comunidades (com identificação da matriz).
- Cadastro e validação de usuários dizimistas, incluindo autocadastro com consentimento LGPD.
- Notificação ao dizimista sobre aprovação ou rejeição do cadastro.
- Registro de contribuições de dízimo, com suporte a correção/complemento de lançamentos existentes (sem bloqueio automático por duplicidade).
- Visualização de contribuições, com filtros por mês e ano.
- Geração de relatórios de arrecadação mensal e anual, por dizimista, por igreja e geral da paróquia.
- Log de auditoria completo (estado antes/depois) para todas as operações de escrita, com garantia de imutabilidade.
- Log de segurança para login, logout e tentativas de autenticação falhas, com bloqueio temporário de conta.
- Mecanismos de conformidade com a LGPD: consulta e anonimização de dados pessoais, preservando o histórico de auditoria.

## Stack Tecnológica

- **Linguagem/Framework**: Python + FastAPI
- **Banco de dados**: PostgreSQL
- **ORM/Migrações**: SQLAlchemy (assíncrono) + Alembic
- **Gerenciamento de ambiente**: pyenv + Poetry
- **Containerização**: Docker + docker-compose
- **Testes**: pytest + httpx
- **Arquitetura**: monolito fullstack, com estrutura preparada para evoluir para API desacoplada

## Arquitetura

O projeto segue arquitetura em camadas, separando responsabilidades para permitir futura extração de um frontend desacoplado sem retrabalho estrutural:

- `app/routers/`: definição de rotas HTTP (camada de apresentação).
- `app/schemas/`: modelos Pydantic de entrada/saída (contratos de API).
- `app/models/`: modelos SQLAlchemy (persistência).
- `app/services/`: regras de negócio, isoladas de request/response do FastAPI.
- `app/dependencies/`: dependências reutilizáveis (autenticação, autorização, contexto de auditoria).
- `app/core/`: configuração, conexão com banco e segurança transversal.

A auditoria de dados é implementada via **triggers no PostgreSQL**, que capturam o estado completo (antes/depois) de qualquer alteração em tabelas monitoradas, complementada por registros explícitos da aplicação para ações de leitura sensíveis (ex: geração de relatórios).

## Perfis de Usuário

- **Administrador**: vinculado a uma paróquia, com acesso irrestrito aos dados dessa paróquia. Cadastra igrejas, valida e cadastra dizimistas, registra e corrige contribuições, gera relatórios e consulta logs de auditoria.
- **Dizimista**: vinculado a exatamente uma igreja dentro da paróquia. Pode se autocadastrar (ficando pendente de validação), visualizar apenas as próprias contribuições e solicitar consulta/anonimização dos próprios dados pessoais.

## Fluxo de Criação e Gestão de Usuários

O sistema possui três formas de criação de usuário. A edição e exclusão são operações restritas ao perfil **administrador**.

### 1. Criação do primeiro administrador via CLI

Para bootstrap inicial do sistema, o primeiro usuário administrador é criado por linha de comando, sem depender de outro usuário logado.

```bash
python -m app.commands.criar_admin
```

O comando solicita interativamente nome, e-mail, senha e confirmação. O administrador criado fica automaticamente ativo e vinculado a uma paróquia (informada no fluxo do comando, quando aplicável).

### 2. Autocadastro de Dizimista

Qualquer pessoa pode acessar a tela de cadastro público (`/usuarios/novo`) para solicitar participação como dizimista.

| Campo | Obrigatoriedade | Observação |
|---|---|---|
| Nome | Obrigatório | — |
| E-mail | Obrigatório | Será usado para login. |
| Senha | Obrigatória | Mínimo de segurança definido na validação. |
| Confirmar senha | Obrigatória | Deve ser idêntica à senha. |
| Igreja | Obrigatória | Dizimista deve ser vinculado a uma única igreja. |
| Telefone | Facultativo | — |
| Data de nascimento | Facultativo | — |
| Número de registro | **Não disponível** | Campo reservado à criação por administrador. Se enviado manualmente na requisição, o valor é ignorado. |

Ao concluir, o cadastro é criado com:
- Perfil: **dizimista**
- Status: **pendente de validação**
- Acesso: **inativo** até aprovação de um administrador

### 3. Criação de Usuários por Administrador

Administradores autenticados podem cadastrar novos usuários em `/usuarios/novo`, escolhendo o perfil e preenchendo os dados conforme a tabela abaixo.

#### 3.1 Cadastro de Dizimista pelo Administrador

| Campo | Obrigatoriedade | Observação |
|---|---|---|
| Nome | Obrigatório | — |
| Igreja | Obrigatória | Vínculo obrigatório para perfil dizimista. |
| E-mail | Facultativo | Se omitido, o dizimista não poderá fazer login sozinho. |
| Senha | Facultativa | Obrigatória apenas se e-mail for informado. |
| Confirmar senha | Facultativa | Obrigatória apenas se senha for informada. |
| Telefone | Facultativo | — |
| Data de nascimento | Facultativo | — |
| Endereço / Bairro / Cidade | Facultativos | Dados complementares do perfil. |
| Número de registro | Facultativo | Deve ser único no sistema. Deixe em branco para não atribuir. |
| Ativo | Facultativo | Define se o cadastro já nasce aprovado. Padrão: inativo. |

#### 3.2 Cadastro de Administrador pelo Administrador

| Campo | Obrigatoriedade | Observação |
|---|---|---|
| Nome | Obrigatório | — |
| E-mail | Obrigatório | Será usado para login. |
| Senha | Obrigatória | — |
| Confirmar senha | Obrigatória | Deve ser idêntica à senha. |
| Paróquia | Obrigatória | Administrador deve estar vinculado a uma paróquia. |
| Telefone | Facultativo | — |
| Data de nascimento | Facultativo | — |
| Também é dizimista | Facultativo | Quando marcado, exibe os campos de dizimista e exige uma igreja. |

### 4. Edição e Exclusão

- **Edição**: disponível apenas para administradores, através da rota `/usuarios/{id}/editar`. Permite alterar nome, e-mail, telefone, data de nascimento, perfil, paróquia, igreja, status de ativação e número de registro, respeitando as mesmas regras de obrigatoriedade do cadastro.
- **Exclusão**: disponível apenas para administradores, através da tela de detalhes do usuário (`/usuarios/{id}`). O administrador excluído permanece autenticado na sessão atual, exceto se tentar excluir a si mesmo (cenário a ser tratado conforme política da aplicação).

Todas as operações de escrita (criação, edição, exclusão) geram log de auditoria automaticamente via trigger no banco de dados.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/)
- [pyenv](https://github.com/pyenv/pyenv) (para desenvolvimento local fora do container)
- [Poetry](https://python-poetry.org/docs/#installation)

## Instalação e Execução

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd gerenciador-dizimo
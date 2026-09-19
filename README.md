# Gerenciador Dízimo

Sistema web para gestão de arrecadação de dízimo em paróquias católicas, com suporte a múltiplas igrejas/comunidades vinculadas a uma mesma paróquia, controle de acesso por perfil, geração de relatórios, auditoria completa e conformidade com a LGPD.

## Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades Principais](#funcionalidades-principais)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Perfis de Usuário](#perfis-de-usuário)
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

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/)
- [pyenv](https://github.com/pyenv/pyenv) (para desenvolvimento local fora do container)
- [Poetry](https://python-poetry.org/docs/#installation)

## Instalação e Execução

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd gerenciador-dizimo

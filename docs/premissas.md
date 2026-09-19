# Premissas para desenvolvimento do projeto


## premissas de contexto e tecnologia de desenvolvimento

* Uma paróquia é formada por várias igrejas/comunidades incluindo a matriz

* Dízimo gerenciado pela paróquia é formado por várias igrejas, incluindo a matriz, mas cada igreja tem a sua arrecadação e registros individualizados. 

* a aplicação deve desenvolvida, inicialmente de forma monolítica e fullstack, mas com estrutura base preparada para API

* linguagem deve ser desenvolvida em python e fastapi, banco de dados postgres, e docker, as dependências e o ambiente virtual serão gerenciados com pyenv e poetry.

* Todas as  transações devem ser registrada em logs para auditoria

* registros de logs não podem ser apagados pelo sistema

* Requisitos de seguranças regidos pela LGPD devem ser implementados

## Princípio básico de funcionamento

### tipos de usuários:

* usuário administrador: Cadastra novos usuários, registra contribuição de dízimo, gera relatórios, valida cadastro de usuários dizimista. Acesso irrestrito aos dados da paróquia a qual é vinculado
* usuário dizimista: visualiza suas contribuições, apenas. Este é vinculado apenas uma igreja da paróquia.

### contribuição do dizimista

* Cada contribuição de dizimista deve ser vinculada ao seu ID, mês referente à sua contribuição e mês da sua contribuição.

### relatórios

O sistema deve gerar relatórios de arrecadação mensal e anual, por dizimista, igreja e geral.






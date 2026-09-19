# Requisitos Funcionais - Sistema de Gestão de Dízimo Paroquial

## RF01 - Gestão de Paróquia e Igrejas
- RF01.1: O sistema deve permitir o cadastro de uma paróquia.
- RF01.2: O sistema deve permitir o cadastro de várias igrejas/comunidades vinculadas a uma paróquia, incluindo a matriz.
- RF01.3: Cada igreja deve manter arrecadação e registros de contribuições individualizados, mesmo estando vinculada à mesma paróquia.

## RF02 - Gestão de Usuários
- RF02.1: O sistema deve permitir dois tipos de perfil de usuário: **administrador** e **dizimista**.
- RF02.2: O usuário administrador deve poder cadastrar novos usuários no sistema.
- RF02.3: O usuário administrador deve poder validar o cadastro de usuários dizimistas antes que estes tenham acesso ao sistema.
- RF02.4: O usuário administrador deve ter acesso irrestrito aos dados da paróquia à qual está vinculado.
- RF02.5: O usuário dizimista deve ser vinculado a exatamente uma igreja dentro da paróquia.
- RF02.6: O usuário dizimista deve ter acesso restrito à visualização apenas das suas próprias contribuições.
- RF02.7: o usuário dizimista pode fazer o próprio cadastro, mas fica pendente de validação de um usuário administrador

## RF03 - Registro de Contribuições
- RF03.1: O usuário administrador deve poder registrar contribuições de dízimo em nome de um dizimista.
- RF03.2: Cada contribuição registrada deve ser vinculada ao ID do dizimista, à igreja correspondente, ao mês de referência da contribuição e à data em que o registro foi efetuado.
- RF03.3: O sistema deve impedir a duplicidade de registro de contribuição para o mesmo dizimista no mesmo mês de referência (assumindo regra de negócio; confirmar com o usuário se duplicidade é permitida em casos de correção ou complemento).

## RF04 - Visualização de Contribuições
- RF04.1: O usuário dizimista deve poder visualizar o histórico das suas próprias contribuições, filtrando por mês e/ou ano.
- RF04.2: O usuário administrador deve poder visualizar as contribuições de qualquer dizimista vinculado à sua paróquia.

## RF05 - Relatórios
- RF05.1: O sistema deve gerar relatório de arrecadação mensal por dizimista.
- RF05.2: O sistema deve gerar relatório de arrecadação anual por dizimista.
- RF05.3: O sistema deve gerar relatório de arrecadação mensal por igreja.
- RF05.4: O sistema deve gerar relatório de arrecadação anual por igreja.
- RF05.5: O sistema deve gerar relatório de arrecadação mensal geral (somatório de todas as igrejas da paróquia).
- RF05.6: O sistema deve gerar relatório de arrecadação anual geral (somatório de todas as igrejas da paróquia).
- RF05.7: Apenas o usuário administrador deve poder gerar e visualizar relatórios.

## RF06 - Auditoria e Logs
- RF06.1: Toda transação realizada no sistema (cadastro, edição, registro de contribuição, geração de relatório, validação de usuário) deve ser registrada em log de auditoria.
- RF06.2: Os registros de log devem conter, no mínimo: usuário responsável pela ação, tipo de ação, data/hora e entidade afetada.
- RF06.3: O sistema não deve permitir a exclusão de registros de log por nenhum tipo de usuário, incluindo administrador.

## RF07 - Conformidade com LGPD
- RF07.1: O sistema deve implementar controles de acesso que garantam que dados pessoais sejam acessados apenas por usuários autorizados.
- RF07.2: O sistema deve permitir que o dizimista solicite a consulta dos seus próprios dados pessoais armazenados.
- RF07.3: O sistema deve registrar consentimento do usuário dizimista para o tratamento de seus dados pessoais no momento do cadastro.
- RF07.4: O sistema deve prever mecanismo de anonimização ou tratamento adequado de dados pessoais em caso de solicitação de exclusão, respeitando a restrição de não exclusão de logs de auditoria (RF06.3).

## RF08 - Autenticação e Autorização
- RF08.1: O sistema deve exigir autenticação para acesso a qualquer funcionalidade.
- RF08.2: O sistema deve aplicar controle de autorização por perfil (administrador/dizimista) em todas as rotas e funcionalidades.

---


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

## RF09 - Notificação de Cadastro
- RF09.1: O sistema deve notificar o dizimista sobre a aprovação do seu cadastro após validação pelo administrador.
- RF09.2: O sistema deve notificar o dizimista sobre a rejeição do seu cadastro após validação pelo administrador, informando o motivo, quando fornecido.
- RF09.3: A notificação deve ser registrada no sistema (ex: e-mail e/ou notificação interna na aplicação; canal exato a definir na modelagem técnica).

## RF10 - Correção/Complemento de Contribuição (revisão de RF03.3)
- RF10.1: O sistema deve permitir a correção ou complemento de uma contribuição já registrada para o mesmo dizimista e mesmo mês de referência, em vez de bloquear o novo lançamento.
- RF10.2: Toda correção/complemento deve gerar um novo registro de alteração (UPDATE), preservando o histórico completo via log de auditoria (estado anterior e novo).
- RF10.3: O sistema deve exibir ao administrador o histórico de alterações de uma contribuição antes de permitir nova correção, para evitar lançamentos duplicados por engano.

## RF11 - Segurança de Autenticação e Log de Acesso
- RF11.1: O sistema deve registrar em log toda tentativa de login, com sucesso ou falha, contendo usuário informado, data/hora, resultado (sucesso/falha) e origem da requisição (IP, quando disponível).
- RF11.2: O sistema deve registrar em log todo evento de logout, contendo usuário, data/hora.
- RF11.3: O sistema deve bloquear temporariamente a conta após um número configurável de tentativas de login sem sucesso consecutivas (ex: 5 tentativas), impedindo novas tentativas por um período determinado (ex: 15 minutos).
- RF11.4: O sistema deve registrar em log o evento de bloqueio de conta por tentativas sucessivas de autenticação falhas.
- RF11.5: O log de tentativas de autenticação (RF11.1, RF11.2, RF11.4) é um log de segurança, distinto do log de auditoria de dados (RF06), mas segue a mesma regra de imutabilidade: não pode ser apagado pelo sistema nem por nenhum usuário.

## RF12 - Disponibilidade do Sistema em Caso de Falha do Log de Auditoria
- RF12.1: O sistema não deve ficar indisponível para operações de escrita caso o mecanismo de log de auditoria esteja temporariamente indisponível.
- RF12.2: Enquanto o log de auditoria estiver indisponível, o sistema deve exibir uma notificação permanente e visível em todas as telas de alteração de dados (criação, edição, exclusão), alertando o usuário sobre a indisponibilidade do log de auditoria.
- RF12.3: O sistema deve registrar, tão logo o log de auditoria seja restabelecido, um evento indicando o período de indisponibilidade, para fins de rastreabilidade da própria falha.


---


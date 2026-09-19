# Casos de Uso - Sistema de Gestão de Dízimo Paroquial

## Atores
- **Administrador**: usuário vinculado a uma paróquia, com acesso irrestrito aos dados dessa paróquia.
- **Dizimista**: usuário vinculado a uma única igreja dentro da paróquia, com acesso restrito às próprias informações.

## Observação sobre registro de log
Todos os casos de uso que envolvem escrita (INSERT, UPDATE ou DELETE) em tabelas do banco geram registro automático em log de auditoria através de trigger no PostgreSQL, capturando o estado completo antes e depois da alteração. O passo "Sistema registra a ação em log de auditoria" descrito nos fluxos abaixo ocorre de forma automática e transparente, disparado pelo trigger no momento do commit da transação, e não depende de lógica explícita da aplicação além de propagar o `usuario_id` autenticado para a sessão do banco. Casos de uso somente leitura (visualização e consulta) não geram log de auditoria, pois não alteram dados, exceto quando indicado o contrário.

---

## UC01 - Cadastrar Paróquia
- **Ator**: Administrador
- **Pré-condição**: Nenhuma.
- **Fluxo principal**:
  1. Administrador acessa a funcionalidade de cadastro de paróquia.
  2. Informa os dados da paróquia.
  3. Sistema valida e registra a paróquia (INSERT).
  4. Trigger de auditoria captura o registro criado (`dados_anteriores` nulo, `dados_novos` com o registro completo) e grava no log automaticamente.
- **Pós-condição**: Paróquia cadastrada e disponível para vinculação de igrejas. Log de criação disponível para consulta.
- **Requisitos relacionados**: RF01.1, RF06.1, RF06.2

## UC02 - Cadastrar Igreja/Comunidade
- **Ator**: Administrador
- **Pré-condição**: Paróquia já cadastrada.
- **Fluxo principal**:
  1. Administrador seleciona a paróquia.
  2. Informa os dados da igreja/comunidade (incluindo se é a matriz).
  3. Sistema valida e vincula a igreja à paróquia (INSERT).
  4. Trigger de auditoria captura o registro criado e grava no log automaticamente.
- **Pós-condição**: Igreja cadastrada e vinculada à paróquia, com registros de arrecadação individualizados. Log de criação disponível para consulta.
- **Requisitos relacionados**: RF01.2, RF01.3, RF06.1, RF06.2

## UC03 - Autocadastro de Dizimista
- **Ator**: Dizimista
- **Pré-condição**: Igreja e paróquia já cadastradas.
- **Fluxo principal**:
  1. Dizimista acessa a funcionalidade de autocadastro.
  2. Informa dados pessoais e seleciona a igreja à qual deseja se vincular.
  3. Sistema registra o consentimento para tratamento de dados pessoais (LGPD).
  4. Sistema salva o cadastro com status "pendente de validação" (INSERT).
  5. Trigger de auditoria captura o registro criado, incluindo o consentimento registrado, e grava no log automaticamente com o `usuario_id` do próprio dizimista recém-cadastrado.
- **Pós-condição**: Cadastro criado, aguardando validação de um administrador. Dizimista não possui acesso às funcionalidades até validação. Log de criação disponível para consulta.
- **Requisitos relacionados**: RF02.5, RF02.7, RF07.3, RF06.1, RF06.2

## UC04 - Validar Cadastro de Dizimista
- **Ator**: Administrador
- **Pré-condição**: Existir cadastro de dizimista com status "pendente".
- **Fluxo principal**:
  1. Administrador acessa a lista de cadastros pendentes.
  2. Seleciona um cadastro e analisa os dados.
  3. Administrador aprova ou rejeita o cadastro (UPDATE no status).
  4. Sistema atualiza o status do dizimista.
  5. Trigger de auditoria captura o estado anterior e o novo estado, gravando `usuario_id` do administrador responsável.
  6. Sistema envia notificação ao dizimista informando aprovação ou rejeição do cadastro (e motivo, se rejeitado).
- **Pós-condição**: Dizimista habilitado a acessar o sistema (se aprovado) ou cadastro rejeitado, com notificação enviada em ambos os casos. Log de alteração de status disponível para consulta.
- **Requisitos relacionados**: RF02.3, RF06.1, RF06.2, RF09.1, RF09.2, RF09.3

## UC05 - Cadastrar Usuário (Administrador cadastra Dizimista)
- **Ator**: Administrador
- **Pré-condição**: Igreja já cadastrada.
- **Fluxo principal**:
  1. Administrador acessa a funcionalidade de cadastro de usuário.
  2. Informa dados do dizimista e seleciona a igreja de vínculo.
  3. Sistema salva o cadastro (já validado, pois foi feito pelo administrador) (INSERT).
  4. Trigger de auditoria captura o registro criado, com o `usuario_id` do administrador responsável, e grava no log automaticamente.
- **Pós-condição**: Dizimista cadastrado e habilitado a acessar o sistema. Log de criação disponível para consulta.
- **Requisitos relacionados**: RF02.2, RF02.5, RF06.1, RF06.2

## UC06 - Registrar/Corrigir Contribuição de Dízimo
- **Ator**: Administrador
- **Pré-condição**: Dizimista cadastrado e validado.
- **Fluxo principal**:
  1. Administrador seleciona o dizimista.
  2. Informa valor, mês de referência e igreja correspondente.
  3. Sistema verifica se já existe contribuição para o mesmo dizimista no mesmo mês de referência.
  4. Se não existir, sistema registra a contribuição (INSERT), com data do registro.
  5. Se já existir, sistema exibe o histórico de contribuições/alterações daquele mês e permite ao administrador optar por corrigir ou complementar o registro existente (UPDATE), em vez de bloquear.
  6. Trigger de auditoria captura o registro criado ou o diff completo (estado anterior/novo) da correção, com `usuario_id` do administrador responsável.
- **Pós-condição**: Contribuição registrada, corrigida ou complementada, disponível para consulta e relatórios, com histórico completo preservado no log de auditoria.
- **Requisitos relacionados**: RF03.1, RF03.2, RF10.1, RF10.2, RF10.3, RF06.1, RF06.2

## UC07 - Visualizar Próprias Contribuições
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado e validado.
- **Fluxo principal**:
  1. Dizimista acessa a área de contribuições.
  2. Aplica filtro por mês e/ou ano (opcional).
  3. Sistema exibe o histórico de contribuições do dizimista autenticado.
- **Pós-condição**: Nenhuma alteração de dados; apenas leitura. Nenhum log de auditoria é gerado, pois não há escrita em tabela monitorada.
- **Requisitos relacionados**: RF04.1

## UC08 - Visualizar Contribuições de Dizimistas (Administrador)
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador seleciona um dizimista vinculado à sua paróquia.
  2. Sistema exibe o histórico de contribuições do dizimista selecionado.
- **Pós-condição**: Nenhuma alteração de dados; apenas leitura. Nenhum log de auditoria é gerado.
- **Requisitos relacionados**: RF04.2

## UC09 - Gerar Relatório de Arrecadação
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador seleciona o tipo de relatório (por dizimista, por igreja ou geral).
  2. Seleciona o período (mensal ou anual) e os filtros aplicáveis.
  3. Sistema processa e exibe/exporta o relatório.
  4. Sistema registra explicitamente, via aplicação, um evento de "geração de relatório" na tabela de auditoria, já que essa ação é apenas leitura de dados e não passaria por nenhum trigger de escrita; o registro inclui `usuario_id`, tipo de relatório e filtros utilizados, sem `dados_anteriores`/`dados_novos` (não se aplica a uma consulta).
- **Pós-condição**: Relatório gerado e disponível para visualização/exportação. Log de geração disponível para consulta, permitindo auditar quem acessou quais dados agregados e quando.
- **Requisitos relacionados**: RF05.1 a RF05.7, RF06.1, RF06.2

## UC10 - Consultar Log de Auditoria
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador acessa a área de logs de auditoria.
  2. Aplica filtros (usuário, tipo de ação, período).
  3. Sistema exibe os registros correspondentes.
- **Pós-condição**: Nenhuma alteração de dados; logs são somente leitura e não podem ser excluídos. Nenhum log adicional é gerado para esta consulta, exceto se a política de segurança exigir auditar quem consultou os próprios logs (ponto a confirmar caso necessário).
- **Requisitos relacionados**: RF06.1, RF06.2, RF06.3

## UC11 - Solicitar Consulta de Dados Pessoais (LGPD)
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado.
- **Fluxo principal**:
  1. Dizimista acessa a funcionalidade de consulta de dados pessoais.
  2. Sistema exibe todos os dados pessoais armazenados referentes ao dizimista.
  3. Sistema registra explicitamente, via aplicação, um evento de "consulta de dados pessoais" na tabela de auditoria, com `usuario_id` do próprio dizimista, já que essa ação é apenas leitura e não dispara trigger de escrita.
- **Pós-condição**: Nenhuma alteração de dados de negócio; apenas leitura. Log de consulta disponível, relevante para comprovar conformidade com solicitações de titular de dados sob a LGPD.
- **Requisitos relacionados**: RF07.1, RF07.2, RF06.1, RF06.2

## UC12 - Solicitar Exclusão/Anonimização de Dados Pessoais (LGPD)
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado.
- **Fluxo principal**:
  1. Dizimista solicita a exclusão dos seus dados pessoais.
  2. Sistema avalia a solicitação, aplicando anonimização nos dados pessoais (UPDATE nos campos pessoais, substituindo por valores anonimizados) e preservando os logs de auditoria intactos.
  3. Trigger de auditoria captura o estado anterior (dados pessoais originais) e o novo estado (dados anonimizados), gravando o `usuario_id` do dizimista solicitante.
- **Pós-condição**: Dados pessoais anonimizados; logs de auditoria preservados sem exclusão, incluindo o próprio histórico de dados anteriores à anonimização (mantido no log conforme RF06.3, ainda que os dados na tabela principal já estejam anonimizados).
- **Requisitos relacionados**: RF07.4, RF06.3, RF06.1, RF06.2

## UC13 - Autenticar no Sistema (
- **Ator**: Administrador, Dizimista
- **Pré-condição**: Usuário previamente cadastrado e validado.
- **Fluxo principal**:
  1. Usuário informa credenciais.
  2. Sistema valida credenciais e perfil de acesso.
  3. Sistema registra em log de segurança a tentativa de login (sucesso), com usuário, data/hora e origem.
  4. Sistema concede acesso às funcionalidades permitidas para o perfil e propaga o `usuario_id` autenticado para a sessão do banco.
- **Fluxo alternativo 1 (credenciais inválidas)**:
  1. Sistema registra em log de segurança a tentativa de login (falha), com usuário informado, data/hora e origem.
  2. Sistema incrementa contador de tentativas falhas consecutivas para o usuário.
  3. Se o contador atingir o limite configurado, sistema bloqueia temporariamente a conta e registra o evento de bloqueio em log de segurança.
  4. Sistema retorna mensagem de erro ao usuário, sem detalhar se o bloqueio foi acionado (para não expor informação sensível de segurança).
- **Fluxo alternativo 2 (logout)**:
  1. Usuário autenticado solicita logout.
  2. Sistema encerra a sessão e registra o evento de logout em log de segurança, com usuário e data/hora.
- **Pós-condição**: Sessão autenticada iniciada, com autorização aplicada por perfil; ou conta temporariamente bloqueada após tentativas sucessivas sem sucesso. Log de segurança completo (login, logout, tentativas falhas, bloqueios) disponível para consulta e imutável.
- **Requisitos relacionados**: RF08.1, RF08.2, RF11.1, RF11.2, RF11.3, RF11.4, RF11.5

## UC14 - Registrar Log de Auditoria (revisão do fluxo de exceção)

### Fluxo de exceção (falha na gravação do log) — revisado
1. Se a gravação do log de auditoria falhar por qualquer motivo (ex: indisponibilidade momentânea do banco/serviço de log), a operação de negócio é executada e confirmada normalmente, sem ser bloqueada pela falha do log.
2. O sistema registra internamente (ex: em arquivo de fallback ou fila de reprocessamento) a ocorrência da falha, para posterior reconciliação quando o log for restabelecido.
3. Enquanto o log de auditoria estiver indisponível, o sistema exibe uma notificação permanente e visível em todas as telas de alteração de dados (criação, edição, exclusão), alertando o usuário sobre a indisponibilidade temporária do log de auditoria.
4. Quando o log de auditoria for restabelecido, o sistema registra um evento indicando o período de indisponibilidade, para rastreabilidade da própria falha (RF12.3).

### Pós-condição (revisada)
Registro de log criado normalmente em condições regulares. Em caso de indisponibilidade do log, a operação de negócio não é bloqueada, mas o usuário é alertado visualmente durante o período de indisponibilidade, e o incidente é registrado para reconciliação posterior.

### Requisitos relacionados
RF06.1, RF06.2, RF06.3, RF12.1, RF12.2, RF12.3

---

**Nota de coerência**: essa revisão do fluxo de exceção do UC14 substitui o comportamento anterior (bloqueio total da operação em caso de falha do log), removendo a característica de atomicidade estrita entre dado e log que dependia do trigger estar na mesma transação. Isso implica uma decisão de arquitetura a formalizar depois: se o log continuar via trigger no mesmo banco Postgres, uma falha no log praticamente nunca ocorrerá isoladamente (é o mesmo banco da operação), então esse cenário de exceção só se torna relevante de fato se, no futuro, o log de auditoria for migrado para uma tabela em outro banco/serviço, quebrando a atomicidade transacional. Vale ter isso em mente na modelagem de dados, pois trigger e log fora de transação são incompatíveis por natureza — se um dia essa migração ocorrer, o mecanismo de gravação do log precisará mudar de trigger de banco para chamada assíncrona da aplicação.



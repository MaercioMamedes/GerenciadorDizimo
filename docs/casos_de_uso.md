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
  5. Trigger de auditoria captura o estado anterior (status "pendente") e o novo estado (status "aprovado" ou "rejeitado"), gravando `usuario_id` do administrador responsável pela ação.
- **Fluxo alternativo**: Se rejeitado, o dizimista permanece sem acesso e pode ser notificado (funcionalidade de notificação não coberta pelas premissas atuais; sinalizo como ponto a confirmar).
- **Pós-condição**: Dizimista habilitado a acessar o sistema (se aprovado) ou cadastro rejeitado. Log de alteração de status disponível para consulta, permitindo reconstruir quem validou e quando.
- **Requisitos relacionados**: RF02.3, RF06.1, RF06.2

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

## UC06 - Registrar Contribuição de Dízimo
- **Ator**: Administrador
- **Pré-condição**: Dizimista cadastrado e validado.
- **Fluxo principal**:
  1. Administrador seleciona o dizimista.
  2. Informa valor, mês de referência e igreja correspondente.
  3. Sistema verifica se já existe contribuição para o mesmo dizimista no mesmo mês de referência.
  4. Sistema registra a contribuição com a data do registro (INSERT).
  5. Trigger de auditoria captura o registro criado, com o `usuario_id` do administrador responsável pelo lançamento, e grava no log automaticamente.
- **Fluxo alternativo**: Se já existir contribuição para o mês de referência, sistema bloqueia o registro e informa o administrador (regra sujeita à confirmação, conforme RF03.3). Nesse caso, nenhuma escrita ocorre e, portanto, nenhum log é gerado.
- **Pós-condição**: Contribuição registrada e disponível para consulta e relatórios. Log de criação disponível para consulta e reconstrução de histórico.
- **Requisitos relacionados**: RF03.1, RF03.2, RF03.3, RF06.1, RF06.2

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

## UC13 - Autenticar no Sistema
- **Ator**: Administrador, Dizimista
- **Pré-condição**: Usuário previamente cadastrado e validado.
- **Fluxo principal**:
  1. Usuário informa credenciais.
  2. Sistema valida credenciais e perfil de acesso.
  3. Sistema concede acesso às funcionalidades permitidas para o perfil e propaga o `usuario_id` autenticado para a sessão do banco, a ser utilizado pelos triggers de auditoria em ações subsequentes na mesma sessão.
- **Fluxo alternativo**: Credenciais inválidas resultam em bloqueio de acesso e mensagem de erro. Recomenda-se registrar tentativas de autenticação falhas em log de segurança (distinto do log de auditoria de dados), útil para detecção de força bruta; funcionalidade não coberta pelos requisitos atuais, sinalizo como ponto a confirmar.
- **Pós-condição**: Sessão autenticada iniciada, com autorização aplicada por perfil.
- **Requisitos relacionados**: RF08.1, RF08.2

## UC14 - Registrar Log de Auditoria (Processo Interno de Gravação)

- **Ator**: Sistema (processo interno, disparado indiretamente por Administrador ou Dizimista através de qualquer ação de escrita)
- **Tipo**: Caso de uso de infraestrutura, não acionado diretamente pelo usuário final; ocorre como consequência automática de UC01, UC02, UC03, UC04, UC05, UC06 e UC12, e de forma explícita via aplicação em UC09 e UC11.
- **Pré-condição**: Usuário autenticado no sistema, com sessão válida iniciada conforme UC13.

### Fluxo principal (ações de escrita monitoradas por trigger)

1. Usuário autenticado envia requisição para uma rota de escrita (criação, atualização ou exclusão) em uma tabela monitorada (ex: `usuarios`, `contribuicoes`, `igrejas`, `paroquias`).
2. A camada de aplicação (FastAPI), antes de executar a operação de negócio, define na sessão do banco de dados a variável `app.current_user_id` com o ID do usuário autenticado, usando `SET LOCAL`, garantindo que o valor esteja restrito à transação corrente.
3. A aplicação executa a operação de negócio (INSERT, UPDATE ou DELETE) dentro da mesma transação.
4. O trigger `fn_audit_log`, associado à tabela afetada, é disparado automaticamente pelo PostgreSQL imediatamente após a operação (AFTER INSERT/UPDATE/DELETE).
5. O trigger lê a variável `app.current_user_id` da sessão; se não estiver definida (ex: script executado diretamente no banco, fora do fluxo da aplicação), grava o campo `usuario_id` como nulo.
6. O trigger monta o registro de auditoria com:
   - `tabela`: nome da tabela afetada (obtido automaticamente via `TG_TABLE_NAME`).
   - `operacao`: tipo da operação (`INSERT`, `UPDATE` ou `DELETE`, obtido via `TG_OP`).
   - `registro_id`: identificador do registro afetado.
   - `dados_anteriores`: estado completo do registro antes da alteração, em JSON (nulo em caso de INSERT).
   - `dados_novos`: estado completo do registro após a alteração, em JSON (nulo em caso de DELETE).
   - `usuario_id`: usuário responsável pela ação, conforme capturado da sessão.
   - `executado_em`: timestamp gerado automaticamente pelo banco no momento da gravação.
7. O trigger insere o registro montado na tabela `audit_log`.
8. O PostgreSQL confirma a transação (commit), persistindo de forma atômica tanto a alteração de negócio quanto o registro de log; se qualquer etapa falhar, toda a transação é revertida (rollback), incluindo o log, mantendo consistência entre dado e auditoria.

### Fluxo alternativo (ações de leitura com necessidade de auditoria, ex: geração de relatório e consulta de dados pessoais)

1. Usuário autenticado envia requisição para uma rota de leitura que exige rastreamento (ex: geração de relatório, consulta de dados pessoais sob LGPD).
2. Como não há alteração de dados, nenhum trigger de banco é disparado.
3. A camada de aplicação grava explicitamente um registro na tabela `audit_log`, informando `usuario_id`, `tabela` (ou identificador da ação, ex: "relatorio_arrecadacao"), `operacao` (ex: "READ" ou "EXPORT", exigindo ajuste no `CHECK` da coluna `operacao` para aceitar esse valor), `dados_novos` contendo os parâmetros da consulta (filtros aplicados, período), e `dados_anteriores` nulo, já que não há estado anterior a comparar.
4. A aplicação confirma a transação, persistindo o log de leitura de forma independente da operação de negócio, já que não há alteração de linha para acoplar o log via trigger.

### Fluxo de exceção (falha na gravação do log)

1. Se a gravação do log falhar por qualquer motivo (ex: violação de constraint, indisponibilidade momentânea do banco), a transação inteira é revertida, incluindo a operação de negócio que originou o log.
2. O usuário recebe mensagem de erro genérica indicando falha ao processar a solicitação, sem detalhar a causa técnica.
3. Nenhum estado parcial é persistido: nem a alteração de negócio nem o log ficam gravados isoladamente. Essa é uma decisão deliberada de design para impedir que uma ação sensível seja executada sem deixar rastro auditável; se a auditoria falhar, a ação também falha.

### Pós-condição
Registro de log criado na tabela `audit_log`, com estado completo antes/depois da alteração (quando aplicável), vinculado ao usuário responsável e ao timestamp da ação. O registro é imutável: as permissões de banco (`REVOKE DELETE, UPDATE`) impedem que qualquer role, incluindo a da aplicação, altere ou exclua o log após sua criação.

### Requisitos relacionados
RF06.1, RF06.2, RF06.3

---

**Ponto a confirmar:**

**Pontos a confirmar antes da modelagem de dados:**
1. UC04 assume que existe algum tipo de notificação ao dizimista sobre aprovação/rejeição do cadastro, mas isso não está coberto nos requisitos funcionais atuais. Se notificação for necessária, é preciso adicionar RF e caso de uso específicos.
2. UC06 trata duplicidade de contribuição como bloqueio automático, conforme sinalizado como pendente de confirmação no RF03.3. Se a intenção for permitir correção/complemento em vez de bloqueio total, o fluxo do UC06 muda.
3. UC09 e UC11 introduzem a necessidade de registrar log de auditoria para ações de leitura (não apenas escrita), o que exige lógica explícita na aplicação além do trigger de banco, já que consultas não disparam trigger. Confirme se esse nível de rastreamento de leitura é realmente necessário ou se pode ficar restrito a ações de escrita, o que simplificaria a implementação.
4. UC13 sugere log de tentativas de autenticação falhas como camada complementar de segurança; isso é distinto do log de auditoria de dados (RF06) e não está coberto nos requisitos atuais. Confirme se deve ser incluído no escopo.
5.  o fluxo de exceção define que falha no log reverte também a operação de negócio, priorizando rastreabilidade sobre disponibilidade (nenhuma ação sensível é aceita sem log correspondente). Essa é uma escolha de trade-off que vale validar com você: em caso de indisponibilidade momentânea do banco de auditoria (se um dia ele for extraído para outra tabela ou serviço), isso significa que o sistema todo para de aceitar escritas até o log ser restabelecido. Se esse nível de rigidez não for desejado para todas as tabelas, seria necessário diferenciar entre logs "críticos" (que bloqueiam a operação se falharem) e "best-effort" (que registram falha mas não bloqueiam); no desenho atual, como log e dado estão na mesma transação e mesmo banco, essa distinção não se aplica e o comportamento é uniforme.


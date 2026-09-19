# Casos de Uso - Sistema de Gestão de Dízimo Paroquial

## Atores
- **Administrador**: usuário vinculado a uma paróquia, com acesso irrestrito aos dados dessa paróquia.
- **Dizimista**: usuário vinculado a uma única igreja dentro da paróquia, com acesso restrito às próprias informações.

---

## UC01 - Cadastrar Paróquia
- **Ator**: Administrador
- **Pré-condição**: Nenhuma.
- **Fluxo principal**:
  1. Administrador acessa a funcionalidade de cadastro de paróquia.
  2. Informa os dados da paróquia.
  3. Sistema valida e registra a paróquia.
  4. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Paróquia cadastrada e disponível para vinculação de igrejas.
- **Requisitos relacionados**: RF01.1, RF06.1

## UC02 - Cadastrar Igreja/Comunidade
- **Ator**: Administrador
- **Pré-condição**: Paróquia já cadastrada.
- **Fluxo principal**:
  1. Administrador seleciona a paróquia.
  2. Informa os dados da igreja/comunidade (incluindo se é a matriz).
  3. Sistema valida e vincula a igreja à paróquia.
  4. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Igreja cadastrada e vinculada à paróquia, com registros de arrecadação individualizados.
- **Requisitos relacionados**: RF01.2, RF01.3, RF06.1

## UC03 - Autocadastro de Dizimista
- **Ator**: Dizimista
- **Pré-condição**: Igreja e paróquia já cadastradas.
- **Fluxo principal**:
  1. Dizimista acessa a funcionalidade de autocadastro.
  2. Informa dados pessoais e seleciona a igreja à qual deseja se vincular.
  3. Sistema registra o consentimento para tratamento de dados pessoais (LGPD).
  4. Sistema salva o cadastro com status "pendente de validação".
  5. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Cadastro criado, aguardando validação de um administrador. Dizimista não possui acesso às funcionalidades até validação.
- **Requisitos relacionados**: RF02.5, RF02.7, RF07.3, RF06.1

## UC04 - Validar Cadastro de Dizimista
- **Ator**: Administrador
- **Pré-condição**: Existir cadastro de dizimista com status "pendente".
- **Fluxo principal**:
  1. Administrador acessa a lista de cadastros pendentes.
  2. Seleciona um cadastro e analisa os dados.
  3. Administrador aprova ou rejeita o cadastro.
  4. Sistema atualiza o status do dizimista.
  5. Sistema registra a ação em log de auditoria.
- **Fluxo alternativo**: Se rejeitado, o dizimista permanece sem acesso e pode ser notificado (funcionalidade de notificação não coberta pelas premissas atuais; sinalizo como ponto a confirmar).
- **Pós-condição**: Dizimista habilitado a acessar o sistema (se aprovado) ou cadastro rejeitado.
- **Requisitos relacionados**: RF02.3, RF06.1

## UC05 - Cadastrar Usuário (Administrador cadastra Dizimista)
- **Ator**: Administrador
- **Pré-condição**: Igreja já cadastrada.
- **Fluxo principal**:
  1. Administrador acessa a funcionalidade de cadastro de usuário.
  2. Informa dados do dizimista e seleciona a igreja de vínculo.
  3. Sistema salva o cadastro (já validado, pois foi feito pelo administrador).
  4. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Dizimista cadastrado e habilitado a acessar o sistema.
- **Requisitos relacionados**: RF02.2, RF02.5, RF06.1

## UC06 - Registrar Contribuição de Dízimo
- **Ator**: Administrador
- **Pré-condição**: Dizimista cadastrado e validado.
- **Fluxo principal**:
  1. Administrador seleciona o dizimista.
  2. Informa valor, mês de referência e igreja correspondente.
  3. Sistema verifica se já existe contribuição para o mesmo dizimista no mesmo mês de referência.
  4. Sistema registra a contribuição com a data do registro.
  5. Sistema registra a ação em log de auditoria.
- **Fluxo alternativo**: Se já existir contribuição para o mês de referência, sistema bloqueia o registro e informa o administrador (regra sujeita à confirmação, conforme RF03.3).
- **Pós-condição**: Contribuição registrada e disponível para consulta e relatórios.
- **Requisitos relacionados**: RF03.1, RF03.2, RF03.3, RF06.1

## UC07 - Visualizar Próprias Contribuições
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado e validado.
- **Fluxo principal**:
  1. Dizimista acessa a área de contribuições.
  2. Aplica filtro por mês e/ou ano (opcional).
  3. Sistema exibe o histórico de contribuições do dizimista autenticado.
- **Pós-condição**: Nenhuma alteração de dados; apenas leitura.
- **Requisitos relacionados**: RF04.1

## UC08 - Visualizar Contribuições de Dizimistas (Administrador)
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador seleciona um dizimista vinculado à sua paróquia.
  2. Sistema exibe o histórico de contribuições do dizimista selecionado.
- **Pós-condição**: Nenhuma alteração de dados; apenas leitura.
- **Requisitos relacionados**: RF04.2

## UC09 - Gerar Relatório de Arrecadação
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador seleciona o tipo de relatório (por dizimista, por igreja ou geral).
  2. Seleciona o período (mensal ou anual) e os filtros aplicáveis.
  3. Sistema processa e exibe/exporta o relatório.
  4. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Relatório gerado e disponível para visualização/exportação.
- **Requisitos relacionados**: RF05.1 a RF05.7, RF06.1

## UC10 - Consultar Log de Auditoria
- **Ator**: Administrador
- **Pré-condição**: Administrador autenticado.
- **Fluxo principal**:
  1. Administrador acessa a área de logs de auditoria.
  2. Aplica filtros (usuário, tipo de ação, período).
  3. Sistema exibe os registros correspondentes.
- **Pós-condição**: Nenhuma alteração de dados; logs são somente leitura e não podem ser excluídos.
- **Requisitos relacionados**: RF06.1, RF06.2, RF06.3

## UC11 - Solicitar Consulta de Dados Pessoais (LGPD)
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado.
- **Fluxo principal**:
  1. Dizimista acessa a funcionalidade de consulta de dados pessoais.
  2. Sistema exibe todos os dados pessoais armazenados referentes ao dizimista.
  3. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Nenhuma alteração de dados; apenas leitura.
- **Requisitos relacionados**: RF07.1, RF07.2, RF06.1

## UC12 - Solicitar Exclusão/Anonimização de Dados Pessoais (LGPD)
- **Ator**: Dizimista
- **Pré-condição**: Dizimista autenticado.
- **Fluxo principal**:
  1. Dizimista solicita a exclusão dos seus dados pessoais.
  2. Sistema avalia a solicitação, aplicando anonimização nos dados pessoais e preservando os logs de auditoria intactos.
  3. Sistema registra a ação em log de auditoria.
- **Pós-condição**: Dados pessoais anonimizados; logs de auditoria preservados sem exclusão.
- **Requisitos relacionados**: RF07.4, RF06.3, RF06.1

## UC13 - Autenticar no Sistema
- **Ator**: Administrador, Dizimista
- **Pré-condição**: Usuário previamente cadastrado e validado.
- **Fluxo principal**:
  1. Usuário informa credenciais.
  2. Sistema valida credenciais e perfil de acesso.
  3. Sistema concede acesso às funcionalidades permitidas para o perfil.
- **Fluxo alternativo**: Credenciais inválidas resultam em bloqueio de acesso e mensagem de erro.
- **Pós-condição**: Sessão autenticada iniciada, com autorização aplicada por perfil.
- **Requisitos relacionados**: RF08.1, RF08.2

---

**Pontos a confirmar antes da modelagem de dados:**
1. UC04 assume que existe algum tipo de notificação ao dizimista sobre aprovação/rejeição do cadastro, mas isso não está coberto nos requisitos funcionais atuais. Se notificação for necessária, é preciso adicionar RF e caso de uso específicos.
2. UC06 trata duplicidade de contribuição como bloqueio automático, conforme sinalizado como pendente de confirmação no RF03.3. Se a intenção for permitir correção/complemento em vez de bloqueio total, o fluxo do UC06 muda.

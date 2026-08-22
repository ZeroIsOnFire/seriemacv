# AGENTS.md — seriemaCV

## Propósito do projeto

seriemaCV é uma suíte local-first para gestão de carreira. Ela mantém os dados
canônicos de carreira em YAML e os usa para criar representações Markdown, DOCX e
PDF, analisar vagas, gerar relatórios de compatibilidade explicáveis e preparar
candidaturas.

O produto deve funcionar sem IA. Quando usada, a IA é uma integração opcional e agnóstica de provedor — nunca dona dos dados ou do fluxo de trabalho do usuário.

## Princípios inegociáveis

- A carreira do usuário é local, portátil e inspecionável. `career.yml` é a
  fonte canônica dos dados de carreira; SQLite serve para índices, estado
  normalizado e cache.
- Markdown, DOCX e PDF são artefatos gerados a partir do YAML. Um importador ou
  uma proposta de IA pode sugerir alterações no YAML, mas nada altera a fonte
  canônica sem uma ação explícita do usuário.
- Nunca invente experiência profissional, competências, cargos, datas, empregadores, métricas, credenciais ou declarações legais. Sugestões devem usar evidências verificadas e distinguir claramente fatos de informações pendentes.
- Todo match deve ser explicável: cada requisito da vaga precisa exibir sua classificação e a evidência correspondente, inclusive quando não houver prova.
- Ações externas (enviar candidatura, submeter formulários, enviar mensagens ou alterar perfis) exigem aprovação humana explícita por padrão.
- Preserve uma progressão útil: builder estruturado manual → assistência por IA
  → agentes → automação de navegador. Recursos avançados não podem ser
  pré-requisitos.

## Arquitetura e limites

- Centralize regras no núcleo de aplicação/domínio. Studio, CLI, MCP e worker de Playwright devem chamar os mesmos casos de uso; não duplique lógica de negócio na interface.
- Mantenha limites claros entre domínio, persistência, renderização, IA, conectores de vagas e automação de navegador.
- Operações de IA que propõem mudanças retornam dados estruturados, `evidence_ids`, confiança e indicação de informação que depende do usuário. Propostas não persistem mudanças automaticamente.
- Comece a recuperação de contexto com busca lexical e filtros de metadados. Não introduza embeddings ou infraestrutura vetorial sem uma necessidade comprovada.
- O motor de matching calcula a pontuação a partir de classificações determináveis (`STRONG_MATCH`, `MATCH`, `PARTIAL_MATCH`, `TRANSFERABLE`, `NO_EVIDENCE`, `CONFLICT`), e não de uma porcentagem livre gerada pelo modelo.
- O fluxo de navegador é uma máquina de estados. Priorize: dados de perfil determinísticos, respostas salvas, regras, proposta de IA baseada em evidência e, por último, pergunta ao usuário. Nunca submeta campos obrigatórios sem resolver.

## Privacidade e segurança

- Não inclua texto de currículo em telemetria por padrão. Explique qual contexto será enviado a cada provedor de IA.
- Use armazenamento seguro do sistema operacional para segredos quando possível; nunca exponha tokens, senhas, credenciais ou valores sensíveis em logs.
- Valide toda entrada externa: URLs, Markdown/YAML/JSON, arquivos, respostas de conectores, variáveis de ambiente e resultados de IA.
- Isole perfis de navegador por projeto ou usuário. Logs e diagnósticos devem redigir credenciais e campos sensíveis; bundles diagnósticos não incluem dados pessoais sem seleção explícita.
- Não preencha ou aceite declarações legais, autorização de trabalho, histórico salarial, dados demográficos ou autoidentificação sem dados configurados pelo usuário e uma revisão apropriada.

## Desenvolvimento e qualidade

- Antes de ler arquivos grandes, busque trechos relevantes com `rg`; evite artefatos gerados, logs e dumps desnecessários.
- O núcleo e a CLI são implementados em Python. No PowerShell, o comando oficial de testes é `$env:PYTHONPATH = 'src'; python -m unittest discover -s tests -v`; quando o Windows não resolver `python`, use uma instalação Python 3.11+ ou o launcher `py -3` configurado. O lint oficial é `python -m ruff check src tests` após instalar `.[dev]`.
- Arquivos YAML são carregados com `ruamel.yaml` em modo round-trip e validados por modelos Pydantic estritos. Nunca use loaders inseguros nem aceite campos desconhecidos em schemas centrais sem uma decisão explícita de compatibilidade.
- `seriemacv validate` verifica a estrutura do projeto; `seriemacv career validate` verifica conteúdo, referências e completude de `career.yml`, permitindo que o scaffold inicial seja preenchido incrementalmente.
- Projetos no layout anterior permanecem válidos em modo de compatibilidade; qualquer conversão para `career.yml` deve ser explícita e não pode apagar os artefatos canônicos legados.
- `resume render --format markdown` só renderiza um `career.yml` completo e escreve atomicamente em `exports/resume.md`; `resume_language` é definido no `init`, apenas localiza títulos fixos e nunca traduz ou altera o YAML canônico.
- Feche explicitamente toda conexão SQLite, inclusive em leituras: o gerenciador de contexto da conexão confirma ou desfaz transações, mas não garante seu fechamento no Windows.
- Preserve formatos públicos e contratos estáveis. Erros previsíveis devem ser estruturados e validados nas bordas da aplicação.
- Para mudança de comportamento, escreva ou atualize primeiro o teste que cobre a regra ou regressão. Testes não devem exigir rede, modelos remotos, GPU, segredos ou dados reais de carreira.
- Execute validações focadas durante a alteração e uma validação proporcional ao risco antes de concluir. Não informe sucesso se um comando falhou, expirou ou foi ignorado; registre a limitação.
- Após desenvolver uma funcionalidade, revise o diff não commitado; corrija os problemas acionáveis encontrados e execute novamente as validações afetadas antes de entregar.
- Não adicione dependências, serviços externos ou automações de plataforma sem autorização explícita.
- O primeiro vertical slice prioriza: `career.yml` + evidências + vaga → match
  explicável → proposta/diff de tailoring → variantes geradas (Markdown, DOCX e
  PDF). Não antecipe autoapply, scrapers frágeis ou infraestrutura complexa.

## Git e entrega

- Mantenha alterações pequenas e focadas; não descarte mudanças existentes do usuário que não estejam no escopo da tarefa.
- Commits devem ser atômicos, em português, e seguir Conventional Commits.
- Ao encerrar, informe arquivos alterados, validações executadas, limitações e riscos restantes de forma breve.

## Aprendizados do projeto

- Todo aprendizado útil e durável descoberto durante o desenvolvimento — comandos oficiais, decisões arquiteturais, convenções, limitações, armadilhas ou práticas de validação — deve ser adicionado a este `AGENTS.md` de forma concisa, no tópico apropriado. Evite registrar detalhes temporários ou dados sensíveis.
- A decomposição atual de funcionalidades, dependências e decisões técnicas está em `docs/funcionalidades.md`; atualize-a quando uma decisão de arquitetura mudar.
- O progresso de implementação é registrado em `docs/checklist.md`. Marque um item como concluído somente após implementação e validação proporcional ao risco.
- Referências externas de currículo ficam em `docs/referencias/`, com origem e condições de uso documentadas. Elas servem para análise; não reutilize conteúdo pessoal nem as apresente como estilos próprios do produto.

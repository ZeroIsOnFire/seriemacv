# AGENTS.md — Base para Projetos Python

Use este arquivo como ponto de partida para o `AGENTS.md` de outro projeto Python. Substitua os campos entre `<...>` pelo contexto do novo repositório e mantenha apenas as regras que se aplicarem.

## Contexto

- Descreva em poucas linhas o propósito do serviço, os dados que trata, integrações externas e a stack Python efetivamente usada.
- Registre os comandos oficiais de desenvolvimento, testes, lint, build e execução (de preferência em container quando o projeto usar Docker Compose).

## Uso de Contexto

- Antes de abrir arquivos grandes, use `rg` com padrões específicos e leia apenas os trechos relevantes.
- Evite arquivos gerados, minificados, compilados, logs extensos ou dumps quando uma busca focada for suficiente.
- Resuma saídas grandes antes de prosseguir.
- Ao repetir um comando que falhou, mude a hipótese, o escopo ou o ambiente e registre a causa provável.
- Prefira validações filtradas; só aumente timeouts quando houver motivo concreto.

## Segurança e Dados

- Segurança, privacidade e segregação de dados são prioritárias.
- Toda consulta ou operação sobre dados privados deve ser escopada ao usuário, organização ou tenant já validado; nunca faça buscas globais para recursos privados.
- Exija autenticação e autorização explícitas para endpoints e operações sensíveis.
- Não exponha segredos, tokens, senhas, parâmetros sensíveis ou logs que contenham credenciais.
- Valide e sanitize toda entrada externa: requisições HTTP, arquivos, variáveis de ambiente, webhooks, filas e parâmetros de IA.
- Não apague dados, bancos, volumes ou artefatos locais sem solicitação explícita e um alvo confirmado.

## Arquitetura Python

- Mantenha rotas/controladores finos; coloque regras de negócio reutilizáveis em serviços ou módulos próprios.
- Centralize validações, contratos de entrada/saída e tratamento de erros previsíveis.
- Preserve limites claros entre API, domínio, persistência, integrações e tarefas assíncronas.
- Defina contratos HTTP estáveis: status codes corretos, erros estruturados, validação de conteúdo e preservação de formatos/dimensões quando aplicável.
- Projete tarefas assíncronas para retries seguros, idempotência quando necessária e estados observáveis (`pending`, `completed`, `error` ou equivalentes).
- Evite adicionar dependências Python, Node ou de sistema sem autorização explícita.
- Ao usar modelos, bibliotecas nativas ou aceleração por hardware, documente versões, compatibilidades e fallback seguro para CPU.

## APIs, Arquivos e IA

- Proteja serviços internos também: isolamento de rede não substitui autenticação quando houver risco de acesso indevido.
- Arquivos enviados devem ter tipo, tamanho e conteúdo validados antes do processamento.
- Feche arquivos temporários e limpe recursos mesmo em caminhos de erro.
- Testes não devem baixar modelos, depender de GPU nem chamar serviços externos reais; use mocks/fixtures leves.
- Mantenha processamento determinístico e fallback funcional quando modelos, pesos ou hardware não estiverem disponíveis.

## Docker e Testes

- Use os comandos e containers oficialmente definidos pelo projeto; não misture dependências locais com o ambiente reproduzível sem necessidade.
- Execute testes focados para o código alterado durante a implementação e uma validação mais ampla proporcional ao risco ao final.
- Isole o ambiente de teste de dados e credenciais de desenvolvimento/produção; inclua verificações que evitem execução acidental no banco errado.
- Para mudanças de interface, valide em navegador real com a ferramenta E2E adotada pelo projeto.
- Para mudanças em APIs, cubra casos de sucesso, autenticação/autorização, entradas inválidas, falhas de integração e fallback relevante.

## Qualidade

- Faça TDD quando houver mudança de comportamento: primeiro teste a regra nova ou a regressão, depois implemente.
- Rode formatter, linter, análise de tipos e testes compatíveis com a stack do projeto (por exemplo: `ruff`, `mypy`/`pyright`, `pytest` ou `unittest`).
- Em alterações sensíveis, de dependências ou de autenticação, execute análise de segurança apropriada e reporte resultados inconclusivos como inconclusivos.
- Não declare validação verde quando um comando expirou, foi ignorado ou falhou por ambiente; registre exatamente a limitação.

## Git, PR e Entrega

- Crie branches pequenas e focadas a partir de `main`, salvo orientação diferente.
- Commits devem ser atômicos, em português e seguir Conventional Commits.
- PRs devem explicar o que mudou, por quê e como validar; não mescle com CI obrigatório em falha.
- Revise antes de concluir: escopo de dados, autorização, validações, testes, duplicação desnecessária, segredos e dependências não autorizadas.

## Encerramento

- Informe de forma objetiva os arquivos alterados, testes executados, verificações inconclusivas e riscos restantes.
- Priorize um resumo curto e acionável, sem despejar logs extensos.

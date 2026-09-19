# Ampliação gradual do MCP do seriemaCV

## Resumo

Evoluir o MCP atual de oito ferramentas artesanais para uma interface local completa,
baseada no [SDK Python oficial v2](https://github.com/modelcontextprotocol/python-sdk),
mantendo o núcleo como única fonte das regras de negócio.

A entrega será dividida em cinco fases: modernização, leitura, escrita local
controlada, edição canônica e navegador assistido.

## Mudanças de interface e implementação

### 1. Fundação e compatibilidade

- Substituir o protocolo JSON-RPC manual pelo SDK oficial, fixado em `mcp>=2,<3`,
  usando somente transporte `stdio`.
- Inicializar com `seriemacv-mcp --project <diretório>` e validar a raiz antes de
  atender requisições.
- Durante uma versão, aceitar o `project_path` legado: sem `--project`, a primeira
  chamada válida fixa a raiz; caminhos diferentes são rejeitados e a depreciação é
  informada apenas em `stderr`.
- Retornar `structuredContent` JSON versionado, mantendo representação textual YAML
  para hosts antigos.
- Preservar métricas locais sem conteúdo e sanitização de erros.

### 2. Leitura, recursos e prompts

- Preservar as oito ferramentas atuais e acrescentar leitura de vaga individual,
  variantes, contexto compacto de candidatura e validação do projeto.
- Publicar os seguintes recursos:
  - `seriemacv://career/source`
  - `seriemacv://career/locales/{locale}`
  - `seriemacv://jobs/{job_id}`
  - `seriemacv://matches/{job_id}`
  - `seriemacv://resume/variants/{variant_id}`
  - `seriemacv://applications/{application_id}/context`
  - `seriemacv://templates/{name}`
- `career/source` entrega intencionalmente o `career.yml` completo, inclusive contatos
  e respostas; os recursos de candidatura continuam usando o contexto compacto e
  redigido existente.
- Adicionar os prompts `analyze_job`, `tailor_resume` e `answer_application`, orientados
  pelas evidências, diretrizes contra inferências e revisão obrigatória.

### 3. Escritas locais revisáveis

- Introduzir `PreparedChange` com token, validade, resumo, diff, arquivos afetados,
  alertas e hashes do estado original.
- Expor ferramentas estreitas para preparar mudanças em vagas, variantes/carta,
  renderização e candidaturas; `confirm_change(token)` será a única operação que
  grava.
- Tokens serão criptograficamente aleatórios, mantidos apenas em memória, válidos por
  dez minutos, de uso único e vinculados ao projeto, operação e hashes dos arquivos.
- A confirmação falha se o projeto mudou depois do preview. Mudanças multifile serão
  preparadas e validadas integralmente, com rollback caso uma substituição falhe.
- Cobrir criação e atualização de vagas, aplicação granular de propostas,
  renderização, criação e configuração de candidatura, respostas confirmadas e
  transições locais de status. Marcar `applied` nunca significará que o MCP enviou uma
  candidatura.

### 4. Editor canônico completo

- Criar um caso de uso compartilhado `prepare_career_change`, com operações tipadas
  para:
  - atualizar perfil;
  - criar, atualizar ou excluir experiências, educação, skills, evidências, respostas
    e histórias;
  - atualizar conteúdo dos locales existentes.
- Não aceitar edição bruta, JSON Patch ou substituição direta de arquivos. IDs
  permanecem imutáveis.
- Criações de experiência, educação ou skill exigem os campos localizados necessários
  para todos os locales existentes.
- Exclusões geram uma cascata explícita sobre locales, evidências, histórias,
  respostas e variantes. Cada consequência aparece no diff e integra a mesma
  confirmação.
- Preservar comentários e ordenação com `ruamel.yaml` em round-trip e validar carreira,
  referências, locales e variantes antes de emitir o token.

### 5. Navegador assistido

- `prepare_browser_application` gera o preview e token; a confirmação abre e preenche
  a sessão isolada.
- Preencher somente fatos determinísticos e respostas previamente confirmadas.
- Persistir perguntas detectadas e devolver o contexto atualizado.
- Não expor ferramenta de submissão, não contornar CAPTCHA e não afirmar sucesso
  externo.

## Testes e aceitação

- Testar tools, resources e prompts com o cliente oficial em memória, mais smoke test
  real por `stdio`.
- Verificar a transição legada, fixação da raiz e rejeição de caminhos divergentes.
- Garantir paridade entre conteúdo estruturado e fallback textual, incluindo leitura
  integral do `career.yml` sem vazamento em métricas ou erros.
- Cobrir expiração, replay, adulteração, uso cruzado e invalidação por alteração
  concorrente dos tokens.
- Demonstrar que validações ou falhas intermediárias deixam todos os arquivos intactos.
- Cobrir CRUD canônico, cascatas, sincronização de locales, preservação de
  comentários, transições de candidatura e renderização/cache.
- Testar o navegador com doubles, confirmando que nenhuma operação submete
  formulários.
- Executar `python scripts/check_quality.py` e atualizar documentação arquitetural,
  checklist e manuais em português e inglês.

## Premissas

- O servidor permanece local, por projeto e exclusivamente via `stdio`; HTTP e
  autenticação ficam fora do roadmap.
- Não serão introduzidos banco, índice gerado, vetores ou serviços externos.
- A exposição completa de `career.yml` é uma decisão explícita; demais saídas continuam
  mínimas e redigidas quando aplicável.
- A compatibilidade com `project_path` dura uma versão e depois é removida.

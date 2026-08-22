# Funcionalidades e decisões técnicas

Este documento separa o design do seriemaCV em capacidades implementáveis. A
ordem proposta preserva o primeiro fluxo de valor: **currículo mestre + evidências
+ vaga → match explicável → variante Markdown → PDF**.

Cada módulo define um contrato próprio. A tecnologia deve ser escolhida por módulo
somente depois de validar os critérios listados; a interface gráfica não deve ser
a dona da regra de negócio.

## Mapa de dependências

```text
Projeto de carreira / arquivos
        │
        ├── Perfil e evidências ──┐
        ├── Currículo Markdown ───┼── Match e tailoring ── Renderização
        └── Vagas ────────────────┘          │
                                             ├── CLI
                                             ├── Studio
                                             └── MCP
                                                    │
                                              Aplicações
                                                    │
                                            Automação assistida
```

## 1. Fundação: projeto de carreira

**Responsabilidade:** criar, abrir e validar um projeto local; definir os caminhos
de `seriemacv.yml`, `profile.yml`, currículo, conhecimento, vagas,
candidaturas, estilos e artefatos internos.

**Entregas independentes**

- Estrutura inicial de diretórios e arquivos de exemplo.
- Leitura, escrita atômica e validação de Markdown, YAML e JSONL.
- Configuração versionada sem segredos.
- Índice SQLite local para estado, cache e busca futura.

**Contrato:** recebe um diretório de projeto e produz entidades válidas ou erros
estruturados. Nenhuma interface conhece detalhes de caminhos ou serialização.

**Decisões tecnológicas**

- Escolher a linguagem do núcleo antes de implementar este módulo.
- Adotar um parser YAML seguro e schemas de validação.
- Usar SQLite local com migrações para dados internos; arquivos permanecem a fonte
  de verdade para conteúdo pertencente ao usuário.
- Definir uma abstração de filesystem para testes sem disco real.

**Depende de:** nada.

## 2. Currículo Markdown e validação

**Responsabilidade:** interpretar o currículo mestre (front matter YAML + Markdown
convencional), preservar sua legibilidade e validar estrutura e referências.

**Entregas independentes**

- AST ou modelo intermediário de currículo.
- Leitura de front matter, seções e experiência.
- Diagnósticos de estrutura e de dados ausentes, sem reescrita automática.
- Criação e validação de variantes Markdown.

**Contrato:** Markdown entra; modelo de currículo, diagnósticos e Markdown
normalizado/serializado saem. O módulo não sabe sobre UI, PDF ou provedor de IA.

**Decisões tecnológicas**

- Parser Markdown maduro que preserve conteúdo e posições para diagnósticos/diff.
- Schema mínimo para front matter, sem criar uma linguagem proprietária no v1.
- Estratégia de diff textual/estrutural para propostas de tailoring.

**Depende de:** Fundação.

## 3. Perfil e Career Library

**Responsabilidade:** armazenar dados determinísticos do perfil e evidências
verificadas reutilizáveis: conquistas, competências, histórias e respostas.

**Entregas independentes**

- Modelos de `CareerProfile`, `CareerEvidence`, `Skill` e respostas salvas.
- Identificadores estáveis de evidência e status de verificação.
- Busca lexical por texto, tags e metadados.
- Regras para montar contexto mínimo para outra funcionalidade.

**Contrato:** consultas retornam somente evidências verificadas e rastreáveis. Uma
funcionalidade consumidora recebe IDs de evidência, não fatos implícitos em prompt.

**Decisões tecnológicas**

- YAML/Markdown para conteúdo editável; SQLite FTS5 para índice lexical, se
  necessário após a primeira versão de busca.
- Não usar embeddings inicialmente.
- Modelagem explícita de dados sensíveis e campos permitidos para cada uso.

**Depende de:** Fundação.

## 4. Estilos e renderização

**Responsabilidade:** projetar um currículo em HTML e exportá-lo, inicialmente em
PDF, sem modificar o conteúdo de origem.

**Entregas independentes**

- Contrato de pacote de estilo: `style.yml`, template HTML, CSS de impressão e
  preview.
- 2–3 estilos ATS-safe de uma coluna.
- Preview HTML e exportação PDF determinística.
- Diagnósticos de falha de template e de paginação.

**Contrato:** recebe o modelo de currículo e um estilo; produz HTML/PDF e metadados
do artefato. DOCX será outro renderer, não uma conversão de PDF.

**Decisões tecnológicas**

- Motor de templates HTML compatível com a linguagem escolhida para o núcleo.
- Renderizador de navegador headless para PDF, escolhido por fidelidade de impressão,
  suporte local e manutenção.
- Testes de snapshot/estrutura para HTML e testes de regressão visual quando houver
  UI.

**Depende de:** Fundação, Currículo Markdown.

## 5. Vagas e normalização

**Responsabilidade:** importar uma vaga a partir de texto, URL, captura de navegador
ou JSON e convertê-la no modelo interno `Job`.

**Entregas independentes**

- Inclusão de vaga por texto/Markdown e JSON estruturado no primeiro corte.
- Armazenamento da origem e texto original.
- Extração/edição de título, senioridade, requisitos, localidade, idioma, modelo de
  trabalho e remuneração quando disponível.
- Conector de URL genérico somente como extensão opcional.

**Contrato:** a normalização produz requisitos com origem e campos ausentes
explícitos. Um conector não altera o currículo ou cria candidatura.

**Decisões tecnológicas**

- Adaptadores por fonte; nenhuma regra de domínio em scraper.
- Cliente HTTP e extração de página somente quando forem autorizados e testáveis.
- Parser determinístico primeiro; IA opcional como proposta revisável de extração.

**Depende de:** Fundação.

## 6. Match explicável

**Responsabilidade:** comparar requisitos de uma vaga com evidências verificadas e
gerar relatório auditável.

**Entregas independentes**

- Recuperação de evidências relevantes por requisito.
- Classificação: `STRONG_MATCH`, `MATCH`, `PARTIAL_MATCH`,
  `TRANSFERABLE`, `NO_EVIDENCE` ou `CONFLICT`.
- Cálculo de score configurável por dimensões.
- Relatório com evidências, lacunas, conflitos e notas para entrevista.

**Contrato:** cada conclusão referencia requisitos e `evidence_ids`. Um score sem
explicação é inválido.

**Decisões tecnológicas**

- Regras e pesos determinísticos no núcleo.
- IA, se usada, apenas sugere classificação/extração e precisa retornar evidência,
  confiança e fatos pendentes.
- Fixtures pequenas de perfil/vaga para testes de classificação e regressão.

**Depende de:** Perfil e Career Library, Vagas; pode receber contexto do Currículo.

## 7. Tailor: proposta de variante

**Responsabilidade:** propor uma variante do currículo para uma vaga, preservando os
fatos e mantendo o mestre inalterado até aceite explícito.

**Entregas independentes**

- Seleção de conteúdo e reorganização baseada no Match.
- Proposta estruturada com diff, `evidence_ids`, confiança e pendências.
- Fluxo de aceitar/rejeitar itens e salvar variante em `resume/variants/`.
- Geração de carta de apresentação como artefato separado.

**Contrato:** propostas são imutáveis até aceitação; a persistência de uma variante
é uma operação explícita. Nenhuma proposta pode introduzir alegação não apoiada.

**Decisões tecnológicas**

- Formato de diff que permita aceite granular no Studio, CLI e MCP.
- Interface de adaptador de IA por caso de uso, com implementações para provedores
  compatíveis e endpoint local.
- Validador posterior à IA que rejeite `evidence_ids` inexistentes.

**Depende de:** Currículo Markdown, Career Library, Match, Renderização para export.

## 8. Interfaces: CLI, Studio e MCP

**Responsabilidade:** oferecer os mesmos casos de uso a pessoas e agentes.

**Entregas independentes**

- CLI como primeira interface de referência: inicializar, validar, renderizar,
  importar vaga, comparar e salvar variante.
- API interna de casos de uso e erros estruturados.
- MCP de leitura e proposta; ferramentas de escrita estreitas.
- Studio com editor Markdown, preview, diff e workspace de vagas.

**Contrato:** interfaces adaptam entradas/saídas e não contêm regra de negócio. MCP
de proposta não altera o projeto; ferramentas de escrita são distintas.

**Decisões tecnológicas**

- Definir a linguagem do núcleo e o runtime da CLI antes do Studio.
- Desktop: avaliar **Tauri + frontend web + host Rust** após o núcleo/CLI estarem
  funcionais; uma aplicação web local é alternativa válida para acelerar feedback.
- Protocolo MCP conforme SDK oficial da linguagem escolhida.
- A UI precisa de preview, editor e diff confiáveis antes de investir em comandos
  de IA ou telas secundárias.

**Depende de:** todos os casos de uso que expõe.

## 9. Candidaturas e automação assistida

**Responsabilidade:** registrar candidaturas, preparar dados e auxiliar o
preenchimento no navegador com checkpoint de revisão.

**Entregas independentes**

- Registro de `Application` e transições de status.
- Escolha de variante, carta e respostas reutilizáveis.
- Preparação de sessão isolada de navegador.
- Descoberta de campos, preenchimento determinístico e rascunhos para campos
  incertos.
- Token/checkpoint explícito antes de submissão.

**Contrato:** preparação e preenchimento não equivalem a submissão. Submeter requer
confirmação de uma revisão aprovada pelo usuário.

**Decisões tecnológicas**

- Playwright como camada de execução sugerida pelo design.
- Máquina de estados persistível e observável, não um prompt único.
- Adaptadores de plataforma somente depois de fluxo genérico robusto.
- Armazenamento e exclusão explícita de cookies/perfis por projeto.

**Depende de:** Perfil, Tailor, Vagas e Interfaces. É pós-MVP.

## Ordem de implementação proposta

| Marco | Módulos | Resultado verificável |
| --- | --- | --- |
| Fundação | 1 | Projeto local válido e testável |
| MVP 0 | 2, 4 e CLI de 8 | Currículo Markdown validado, preview e PDF |
| MVP 1 | 3, 7 e IA de 8 | Evidências e propostas revisáveis, sem mudar fatos |
| MVP 2 | 5, 6 e restante de 8 | Vaga, match explicável e variante por vaga |
| MVP 3 | 9 | Preparação de candidatura com revisão antes de enviar |

## Decisões que precisam ser tomadas antes do código

1. **Linguagem do núcleo e CLI:** **decidido: Python**. As escolhas de bibliotecas
   e empacotamento devem priorizar portabilidade local, parsing/validação, SQLite,
   PDF, ecossistema MCP, testes e futura integração com o Studio.
2. **Forma do primeiro Studio:** Tauri desde o início ou web local temporária.
3. **Formato de schemas:** biblioteca de validação e política de compatibilidade
   para `seriemacv.yml`, perfil, evidências, vagas e relatórios.
4. **Pipeline de PDF:** navegador headless e estratégia de empacotamento local.
5. **Primeiro adaptador de IA:** manter a interface agnóstica e escolher um
   adaptador compatível com OpenAI, endpoint local ou ambos para desenvolvimento.

A decisão inicial recomendada é limitar o primeiro ciclo aos módulos 1, 2, 4 e à
CLI do módulo 8. Ela permite validar a base local-first e entrega um currículo
renderizável antes de acoplar IA, fontes externas ou automação.

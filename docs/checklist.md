# Checklist de implementação — seriemaCV

Este checklist acompanha a entrega do produto a partir de
[funcionalidades.md](funcionalidades.md) e do design do projeto. Marque um item
somente quando houver implementação, testes proporcionais ao risco e validação
registrada.

## Fundação

- [x] Criar pacote Python, CLI e comando de testes.
- [x] Criar e validar um projeto de carreira local.
- [x] Criar diretórios e artefatos canônicos iniciais.
- [x] Usar escrita atômica para arquivos gerados.
- [x] Criar índice SQLite local com migração inicial.
- [x] Abrir um projeto validado por uma API tipada.
- [x] Validar `seriemacv.yml` com YAML seguro e schema estrito.
- [x] Impedir sobrescrita de um projeto existente.
- [x] Cobrir a fundação com testes automatizados.

## MVP 0 — Career builder

- [x] Definir o schema versionado e o modelo intermediário de `career.yml`.
- [x] Criar o builder estruturado para perfil, experiência, educação, habilidades e
  evidências.
- [x] Validar seções, experiência e campos obrigatórios do YAML.
- [x] Emitir diagnósticos com arquivo, posição e orientação acionável.
- [ ] Criar e validar variantes estruturadas em `resume/variants/`.
- [ ] Importar currículo Markdown, DOCX ou PDF como proposta revisável de
  `career.yml`.
- [x] Definir o contrato de pacote de estilo (`style.yml`, HTML e CSS).
- [x] Implementar primeiro estilo ATS-safe de uma coluna.
- [x] Gerar currículo Markdown a partir do YAML.
- [x] Renderizar currículo em HTML.
- [x] Exportar PDF por renderizador local de navegador.
- [ ] Exportar DOCX por renderer próprio, sem converter do PDF.
- [ ] Exportar DOC para compatibilidade legada, a partir de uma estratégia local
  definida para o formato.
- [x] Adicionar CLI para editar dados estruturados, validar e renderizar currículo.
- [x] Cobrir YAML, validação e renderização com testes e fixtures.

## MVP 1 — Career Library e assistência por IA

- [ ] Definir schemas para perfil, habilidades e evidências verificadas.
- [ ] Indexar e buscar evidências por texto, tags e metadados.
- [ ] Criar base de respostas e histórias reutilizáveis.
- [ ] Implementar contrato de proposta com `evidence_ids`, confiança e pendências.
- [ ] Definir interface agnóstica de provedor de IA.
- [ ] Implementar primeiro adaptador de IA aprovado.
- [ ] Validar que uma proposta não referencia evidência inexistente.
- [ ] Exibir ou retornar diff com aceite/rejeição granular.
- [ ] Salvar variante apenas após ação explícita do usuário.
- [ ] Gerar carta de apresentação como artefato separado.
- [ ] Cobrir falhas de IA, ausência de evidência e propostas inválidas.

## MVP 2 — Vagas, Match e interfaces

- [x] Definir schemas de vaga e requisito.
- [ ] Definir schema de relatório de match.
- [x] Importar vaga de JSON ou YAML estruturado.
- [x] Preservar conteúdo e origem da vaga importada.
- [x] Expor templates de carreira e vaga para ferramentas externas.
- [ ] Extrair requisitos de forma determinística ou como proposta revisável.
- [ ] Recuperar evidências relevantes para cada requisito.
- [ ] Classificar requisitos com os estados oficiais de match.
- [ ] Calcular score a partir das classificações e pesos configuráveis.
- [ ] Gerar relatório explicável com evidências, lacunas e conflitos.
- [ ] Integrar tailoring de currículo a uma vaga.
- [x] Expandir a CLI para vagas.
- [ ] Expandir a CLI para match e variantes.
- [ ] Expor MCP somente de leitura e proposta inicialmente.
- [ ] Implementar Studio após os casos de uso do núcleo estarem estáveis.
- [ ] Cobrir fluxos de sucesso, dados ausentes, conflito e `NO_EVIDENCE`.

## MVP 3 — Candidatura assistida

- [ ] Definir schema e máquina de estados de candidatura.
- [ ] Criar, atualizar e listar registros de candidatura.
- [ ] Associar vaga, variante, carta e respostas à candidatura.
- [ ] Preparar sessão isolada de navegador por projeto.
- [ ] Detectar campos e mapear dados determinísticos de perfil.
- [ ] Reutilizar respostas salvas quando aplicável.
- [ ] Criar rascunhos de IA apenas para campos incertos.
- [ ] Exigir revisão explícita antes de submeter.
- [ ] Exigir token/checkpoint de confirmação para submissão.
- [ ] Registrar resultado e atualizar status.
- [ ] Cobrir campos obrigatórios não resolvidos e dados sensíveis.

## Privacidade, segurança e entrega

- [ ] Implementar armazenamento seguro de segredos.
- [ ] Redigir tokens e dados sensíveis em logs.
- [ ] Exibir o contexto enviado a provedores de IA.
- [ ] Impedir telemetria de currículo por padrão.
- [ ] Isolar perfis e dados do navegador.
- [ ] Garantir que diagnósticos não exportem artefatos pessoais por padrão.
- [ ] Adicionar formatter, linter e análise de tipos compatíveis com a stack.
- [ ] Configurar CI para testes e verificações estáticas.
- [ ] Documentar instalação, uso local e comandos oficiais.
- [ ] Revisar dependências e políticas de atualização.

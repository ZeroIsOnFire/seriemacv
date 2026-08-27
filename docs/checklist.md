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
- [x] Manter busca lexical direta no YAML, sem índice SQLite.
- [x] Abrir um projeto validado por uma API tipada.
- [x] Validar `seriemacv.yml` com YAML seguro e schema estrito.
- [x] Impedir sobrescrita de um projeto existente.
- [x] Cobrir a fundação com testes automatizados.

## MVP 0 — Career builder

**Foco ativo:** ampliar a biblioteca de estilos e a qualidade dos artefatos de
currículo, com vagas, match e tailoring locais disponíveis.

- [x] Definir o schema versionado e o modelo intermediário de `career.yml`.
- [x] Criar o builder estruturado para perfil, experiência, educação, habilidades e
  evidências.
- [x] Validar seções, experiência e campos obrigatórios do YAML.
- [x] Emitir diagnósticos com arquivo, posição e orientação acionável.
- [x] Separar `i18n/` da aplicação, conteúdo profissional em `career.locales/` e
  overrides editoriais específicos de vaga em `resume/variants/`.
- [x] Definir o contrato de pacote de estilo (`style.yml`, HTML e CSS).
- [x] Adicionar seis famílias visuais estruturais, originais e sem foto, com variantes
  `-alt`: `split-header`, `contact-band`, `left-rail` e `detail-sidebar`.
- [x] Implementar primeiro estilo ATS-safe de uma coluna.
- [x] Criar registro estrito de estilos internos e seleção por configuração/CLI.
- [x] Entregar `classic`, `modern` e `compact` como estilos ATS-safe de uma coluna.
- [x] Entregar `sidebar` como estilo visual experimental de duas colunas.
- [x] Entregar variantes `-alt` sem divisores para todas as famílias, mantendo os IDs
  padrão com divisores de seção e o cabeçalho do `classic` sempre sem linha inferior.
- [x] Gerar variações estruturais de Markdown para todos os estilos.
- [x] Versionar galeria fictícia com previews e PDFs reproduzíveis.
- [x] Separar a galeria bilíngue dos READMEs e adicionar `clean-executive` ATS-safe
  e `timeline` visual/sem foto, incluindo variantes `-alt`.
- [x] Parametrizar cores de fundo/destaque dos estilos dependentes de cor via código
  hexadecimal em `seriemacv.yml`; usar o verde do mascote como padrão em `modern` e
  permitir override em templates como `modern` e `timeline`.
- [x] Gerar currículo Markdown a partir do YAML.
- [x] Renderizar currículo em HTML.
- [x] Exportar PDF por renderizador local de navegador.
- [x] Exportar DOCX por renderer próprio, sem converter do PDF.
- [x] Manter `.doc` fora do produto; a compatibilidade editável termina em DOCX.
- [x] Adicionar CLI para editar dados estruturados, validar e renderizar currículo.
- [x] Cobrir YAML, validação e renderização com testes e fixtures.

## MVP 1 — Career Library e assistência por IA

- [x] Definir schemas para perfil, habilidades e evidências verificadas.
- [x] Indexar e buscar evidências por texto, tags e metadados.
- [x] Criar base de respostas e histórias reutilizáveis.
- [x] Implementar contrato de proposta com `evidence_ids`, confiança e pendências.
- [x] Definir interface agnóstica de provedor de IA.
- [x] Implementar primeiro adaptador de IA aprovado.
- [x] Validar que uma proposta não referencia evidência inexistente.
- [x] Exibir ou retornar diff com aceite/rejeição granular.
- [x] Salvar variante apenas após ação explícita do usuário.
- [x] Gerar carta de apresentação como artefato separado.
- [x] Cobrir falhas de IA, ausência de evidência e propostas inválidas.

## MVP 2 — Vagas, Match e interfaces

**Ativo:** vagas, match explicável, tailoring revisável e interfaces locais usam o
mesmo núcleo e preservam a carreira canônica.

- [x] Definir schemas de vaga e requisito.
- [x] Definir schema de relatório de match.
- [x] Importar vaga de JSON ou YAML estruturado.
- [x] Preservar conteúdo e origem da vaga importada.
- [x] Expor templates de carreira e vaga para ferramentas externas.
- [x] Extrair requisitos de forma determinística ou como proposta revisável.
- [x] Recuperar evidências relevantes para cada requisito.
- [x] Classificar requisitos com os estados oficiais de match.
- [x] Calcular score a partir das classificações e pesos configuráveis.
- [x] Gerar relatório explicável com evidências, lacunas e conflitos.
- [x] Integrar tailoring de currículo a uma vaga.
- [x] Expandir a CLI para vagas.
- [x] Expandir a CLI para match; listagem, validação e renderização de variantes já
  estão disponíveis.
- [x] Expor MCP somente de leitura e proposta inicialmente.
- [x] Implementar Studio após os casos de uso do núcleo estarem estáveis.
- [x] Cobrir fluxos de sucesso, dados ausentes, conflito e `NO_EVIDENCE`.

## MVP 3 — Candidatura assistida

- [x] Definir schema e máquina de estados de candidatura.
- [x] Criar, atualizar e listar registros de candidatura.
- [x] Associar vaga, variante, carta e respostas à candidatura.
- [x] Preparar sessão isolada de navegador por projeto.
- [x] Detectar campos e mapear dados determinísticos de perfil.
- [x] Reutilizar respostas salvas quando aplicável.
- [x] Criar rascunhos de IA apenas para campos incertos.
- [x] Exigir revisão explícita antes de submeter.
- [ ] Exigir token/checkpoint de confirmação para submissão (adiado: este MVP não submete externamente).
- [x] Registrar resultado e atualizar status.
- [x] Cobrir campos obrigatórios não resolvidos e dados sensíveis.

## Privacidade, segurança e entrega

- [ ] Implementar armazenamento seguro de segredos.
- [x] Redigir tokens e dados sensíveis em logs.
- [x] Exibir o contexto enviado a provedores de IA.
- [x] Impedir telemetria de currículo por padrão.
- [x] Isolar perfis e dados do navegador.
- [x] Garantir que diagnósticos não exportem artefatos pessoais por padrão.
- [x] Adicionar formatter, linter e análise de tipos compatíveis com a stack.
- [x] Configurar CI para testes e verificações estáticas.
- [x] Documentar instalação, uso local e comandos oficiais em guia bilíngue por funcionalidade.
- [x] Revisar dependências e políticas de atualização.

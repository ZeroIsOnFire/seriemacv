# Guia completo de uso do seriemaCV

[English manual](../en/index.md) · [README do projeto](../../../README.pt-BR.md)

O seriemaCV armazena informações profissionais localmente em um `career.yml`
canônico e transforma esse documento em currículos Markdown, HTML, PDF e DOCX. O
YAML de origem permanece sempre sob controle do usuário.

## Guia por funcionalidade

| Funcionalidade | O que faz | Guia |
| --- | --- | --- |
| Instalação | Instala a CLI e o Chromium opcional necessário para PDF | [Instalação](instalacao.md) |
| Usar o Seriema com IA | Delega tarefas de carreira revisáveis e baseadas em evidências | [Usar o Seriema com IA](uso-com-ia.md) |
| Usar o Seriema CLI | Executa os mesmos fluxos locais diretamente no PowerShell | [Usar o Seriema CLI](uso-cli.md) |
| Projetos de carreira | Cria, configura e valida o workspace local | [Projetos e configuração](projetos.md) |
| Career Builder | Mantém fatos canônicos e textos de carreira localizados | [Career Builder](career-builder.md) |
| Geração de currículo | Lista estilos e gera Markdown, HTML, PDF e DOCX | [Currículos e estilos](renderizacao.md) |
| Propostas locais de IA | Troca propostas YAML revisáveis com Codex, Claude Code ou outro agente | [Propostas locais de IA](propostas.md) |
| Templates | Expõe o contrato YAML atual para pessoas e ferramentas externas | [Templates e ferramentas externas](templates.md) |
| Vagas e match | Importa vagas, gera relatórios explicáveis e prepara propostas por vaga | [Vagas e match](vagas-e-match.md) |
| Candidaturas assistidas | Prepara candidaturas locais revisáveis sem enviá-las | [Candidaturas assistidas](candidaturas.md) |
| Diagnósticos | Explica erros de validação, navegador, arquivos e Python | [Solução de problemas](solucao-de-problemas.md) |

## Escolha sua interface

Use [Usar o Seriema com IA](uso-com-ia.md) para delegar trabalho revisável a um agente
de IA ou [Usar o Seriema CLI](uso-cli.md) para executar os comandos diretamente. Os
dois caminhos usam o mesmo projeto local e mantêm o YAML sob seu controle.

## Escopo atual

O fluxo local cobre dados profissionais, geração de currículos, importação de vagas,
relatórios explicáveis de match, propostas revisáveis de tailoring e Studio somente leitura.

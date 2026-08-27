# Guia completo de uso do seriemaCV

[English manual](../en/index.md) · [README do projeto](../../../README.pt-BR.md)

O seriemaCV armazena informações profissionais localmente em um `career.yml`
canônico e transforma esse documento em currículos Markdown, HTML, PDF e DOCX. O
YAML de origem permanece sempre sob controle do usuário.

## Guia por funcionalidade

| Funcionalidade | O que faz | Guia |
| --- | --- | --- |
| Instalação | Instala a CLI e o Chromium opcional necessário para PDF | [Instalação](instalacao.md) |
| Projetos de carreira | Cria, configura e valida o workspace local | [Projetos e configuração](projetos.md) |
| Career Builder | Mantém fatos canônicos e textos de carreira localizados | [Career Builder](career-builder.md) |
| Geração de currículo | Lista estilos e gera Markdown, HTML, PDF e DOCX | [Currículos e estilos](renderizacao.md) |
| Propostas locais de IA | Troca propostas YAML revisáveis com Codex, Claude Code ou outro agente | [Propostas locais de IA](propostas.md) |
| Templates | Expõe o contrato YAML atual para pessoas e ferramentas externas | [Templates e ferramentas externas](templates.md) |
| Vagas e match | Importa vagas, gera relatórios explicáveis e prepara propostas por vaga | [Vagas e match](vagas-e-match.md) |
| Diagnósticos | Explica erros de validação, navegador, arquivos e Python | [Solução de problemas](solucao-de-problemas.md) |

## Primeiro fluxo recomendado

```powershell
python -m pip install -e .
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style clean
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id cargo-atual --company "Empresa" --start-date 2024-01
# Adicione o cargo do perfil e o texto de cargo-atual em career.locales/pt-BR.yml.
seriemacv career validate .\minha-carreira
seriemacv career locale validate .\minha-carreira --language pt-BR
seriemacv resume render .\minha-carreira --format docx
```

Use `seriemacv validate .\minha-carreira` para verificar a estrutura do projeto. Use
`seriemacv career validate .\minha-carreira` para verificar o conteúdo profissional
canônico. Use `career locale validate` para verificar o texto de carreira selecionado
junto com seu catálogo i18n antes da renderização.

## Escopo atual

O fluxo local cobre dados profissionais, geração de currículos, importação de vagas,
relatórios explicáveis de match, propostas revisáveis de tailoring e Studio somente leitura.

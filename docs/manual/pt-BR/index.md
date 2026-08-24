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
| Career Builder | Mantém perfil, experiências, formação, competências e evidências | [Career Builder](career-builder.md) |
| Geração de currículo | Lista estilos e gera Markdown, HTML, PDF e DOCX | [Currículos e estilos](renderizacao.md) |
| Templates | Expõe o contrato YAML atual para pessoas e ferramentas externas | [Templates e ferramentas externas](templates.md) |
| NuExtract Docker | Executa o runtime opcional de extração local no Docker | [NuExtract com Docker](nuextract-docker.md) |
| Diagnósticos | Explica erros de validação, navegador, arquivos e Python | [Solução de problemas](solucao-de-problemas.md) |

## Primeiro fluxo recomendado

```powershell
python -m pip install -e .
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style clean
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --title "Seu Cargo" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id cargo-atual --company "Empresa" --title "Cargo" --start-date 2024-01
seriemacv career validate .\minha-carreira
seriemacv resume render .\minha-carreira --format docx
```

Use `seriemacv validate .\minha-carreira` para verificar a estrutura do projeto. Use
`seriemacv career validate .\minha-carreira` para verificar o conteúdo profissional
e sua completude.

## Escopo atual

O fluxo público atual está concentrado em dados profissionais e geração de
currículos. O domínio e os arquivos de vagas continuam preservados, mas seus comandos
estão intencionalmente ocultos enquanto essa área permanece pausada.

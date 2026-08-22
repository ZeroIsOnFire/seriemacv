# seriemacv

[Read in English](README.md)

![Mascote do seriemaCV](mascot.png)

Workspace local-first para manter dados canônicos de carreira em YAML.

## Career Builder

```powershell
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --title "Seu cargo" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id empresa-atual --company "Empresa" --title "Cargo" --start-date 2024-01
seriemacv career validate .\minha-carreira
```

Cada projeto inclui `career.yml` vazio e exemplos fictícios em
`career.yml.example` e `seriemacv.yml.example`. `career.yml` é sempre a fonte
canônica.

## Vagas locais

```powershell
seriemacv jobs add .\minha-carreira --id engenheiro-plataforma --title "Engenheiro de Plataforma" --description "Construa sistemas confiáveis." --requirement python="Experiência profissional com Python"
seriemacv jobs import .\minha-carreira .\vaga.yml
seriemacv jobs validate .\minha-carreira
seriemacv jobs list .\minha-carreira
```

As vagas ficam em `jobs/<id>.yml` por escrita atômica. A importação aceita somente
propostas estruturadas JSON ou YAML, que podem ser produzidas por IA ou outra
ferramenta local; a proposta original é preservada literalmente como metadado de origem.
Letras maiúsculas nos IDs da vaga e dos requisitos são normalizadas para minúsculas
na importação; outros caracteres fora de kebab-case são rejeitados.

```yaml
schema_version: 1
id: engenheiro-plataforma
title: Engenheiro de Plataforma
description: Construir e operar serviços confiáveis de plataforma em nuvem.
requirements:
  - id: python
    statement: Experiência profissional com Python
    priority: required
salary_range: USD 120,000-150,000 por ano
```

Os mesmos campos também podem ser informados em JSON.

## Templates para ferramentas de IA

Uma IA externa ou script local pode consultar os contratos atuais sem ler arquivos
do projeto diretamente:

```powershell
seriemacv template show .\minha-carreira career
seriemacv template show .\minha-carreira job
```

O comando imprime os exemplos YAML fictícios criados pelo `init`. O template de vaga
é o formato de entrada de `seriemacv jobs import`; o importador adiciona os metadados
`source` ao documento canônico armazenado.

## Gerar currículo

```powershell
seriemacv resume render .\minha-carreira --format markdown
seriemacv resume render .\minha-carreira --format html
seriemacv resume render .\minha-carreira --format pdf
```

O comando valida `career.yml` antes de escrever `exports/resume.md`,
`exports/resume.html` ou `exports/resume.pdf`. Para PDF, instale o Chromium local:
`python -m playwright install chromium`.

`resume_language`, definido no `init`, localiza apenas rótulos fixos; o conteúdo
canônico nunca é traduzido ou reescrito.

## Competências e links

```yaml
skills:
  - id: ruby
    name: Ruby
    category: Programação
    level: advanced
    core: true
```

As competências são agrupadas por categoria e as `core` recebem destaque. Os níveis
usam códigos estáveis no YAML e são localizados na renderização. O perfil também
aceita URLs HTTP(S) explícitas em `linkedin` e `portfolio`.

## Verificação local

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Instale as ferramentas de desenvolvimento com `python -m pip install -e ".[dev]"`.

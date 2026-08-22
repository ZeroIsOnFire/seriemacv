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

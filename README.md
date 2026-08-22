# seriemacv

Workspace local-first para manter dados de carreira canônicos em YAML.

## Career Builder (inicial)

```powershell
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --title "Seu cargo" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id empresa-atual --company "Empresa" --title "Cargo" --start-date 2024-01
seriemacv career validate .\minha-carreira
```

Cada projeto inclui um `career.yml` vazio e os exemplos fictícios
`career.yml.example` e `seriemacv.yml.example`. O arquivo canônico é sempre
`career.yml`; exemplos não são usados como dados de carreira.

## Gerar currículo Markdown

```powershell
seriemacv resume render .\minha-carreira --format markdown
```

O comando valida a completude de `career.yml` antes de escrever `exports/resume.md`.
O idioma é definido uma vez no `init` e armazenado como `resume_language` em
`seriemacv.yml`; ele escolhe somente os títulos fixos. O conteúdo canônico nunca é
traduzido ou alterado.

## Verificação local

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Instale as ferramentas de desenvolvimento com `python -m pip install -e ".[dev]"`.

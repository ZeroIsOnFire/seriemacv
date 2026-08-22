# seriemacv

Workspace local-first para manter dados de carreira canônicos em YAML.

## Career Builder (inicial)

```powershell
seriemacv init .\minha-carreira --name "Minha carreira"
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --title "Seu cargo" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id empresa-atual --company "Empresa" --title "Cargo" --start-date 2024-01
seriemacv career validate .\minha-carreira
```

Cada projeto inclui um `career.yml` vazio e os exemplos fictícios
`career.yml.example` e `seriemacv.yml.example`. O arquivo canônico é sempre
`career.yml`; exemplos não são usados como dados de carreira.

## Verificação local

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests
```

Instale as ferramentas de desenvolvimento com `python -m pip install -e ".[dev]"`.

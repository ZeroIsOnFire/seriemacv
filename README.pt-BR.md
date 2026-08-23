# seriemacv

[Read in English](README.md)

![Mascote do seriemaCV](mascot.png)

Workspace local-first para manter dados canônicos de carreira em YAML e gerar
currículos editáveis ou prontos para publicação.

## Documentação

Consulte o [guia completo de uso](docs/manual/pt-BR/index.md) para instalação,
configuração de projetos, todos os comandos do Career Builder, formatos de currículo,
templates e solução de problemas.

## Career Builder

```powershell
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style modern
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --title "Seu cargo" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id empresa-atual --company "Empresa" --title "Cargo" --start-date 2024-01
seriemacv career validate .\minha-carreira
```

Cada projeto inclui `career.yml` vazio e exemplos fictícios em
`career.yml.example` e `seriemacv.yml.example`. `career.yml` é sempre a fonte
canônica. `resume_language` localiza apenas rótulos fixos; o conteúdo informado pelo
usuário nunca é traduzido.

A área de vagas está temporariamente pausada. Arquivos existentes e o domínio
validado permanecem intactos, mas os comandos de vagas não são expostos pela CLI.

## Gerar currículo

```powershell
seriemacv resume styles
seriemacv resume render .\minha-carreira --format markdown
seriemacv resume render .\minha-carreira --format html --style classic
seriemacv resume render .\minha-carreira --format pdf --style modern
seriemacv resume render .\minha-carreira --format docx --style compact
```

`resume_style` em `seriemacv.yml` define o padrão. `--style` o substitui em uma
renderização sem alterar o projeto. Cada formato substitui atomicamente seu artefato
fixo em `exports/resume.*`. PDF requer Chromium local:
`python -m playwright install chromium`.

Os estilos Markdown variam hierarquia, separadores e densidade; Markdown não
representa fontes, cores ou colunas. DOCX permanece editável. `clean`, `classic`,
`modern` e `compact` preservam estrutura linear ATS-safe. `sidebar` usa duas colunas,
é visual/experimental e não é ATS-safe.

## Galeria de estilos internos

Todos os previews e PDFs usam o [currículo fictício da galeria](examples/style-career.yml).

| Estilo | Preview | Características | Exemplo |
| --- | --- | --- | --- |
| `clean` | <img src="examples/styles/clean/preview.png" width="180" alt="Preview do currículo Clean"> | Neutro, uma coluna, ATS-safe | [PDF](examples/styles/clean/resume.pdf) |
| `classic` | <img src="examples/styles/classic/preview.png" width="180" alt="Preview do currículo Classic"> | Serifado tradicional, cabeçalho centralizado, ATS-safe | [PDF](examples/styles/classic/resume.pdf) |
| `modern` | <img src="examples/styles/modern/preview.png" width="180" alt="Preview do currículo Modern"> | Contemporâneo com detalhes azul-marinho, ATS-safe | [PDF](examples/styles/modern/resume.pdf) |
| `compact` | <img src="examples/styles/compact/preview.png" width="180" alt="Preview do currículo Compact"> | Denso para carreiras extensas, ATS-safe | [PDF](examples/styles/compact/resume.pdf) |
| `sidebar` | <img src="examples/styles/sidebar/preview.png" width="180" alt="Preview do currículo Sidebar"> | Duas colunas, foco visual, não ATS-safe | [PDF](examples/styles/sidebar/resume.pdf) |

Para regenerar a galeria:

```powershell
$env:PYTHONPATH = 'src'
python .\scripts\generate_style_examples.py
```

## Templates e competências estruturadas

Ferramentas externas podem consultar o contrato fictício de carreira atual com:

```powershell
seriemacv template show .\minha-carreira career
```

```yaml
skills:
  - id: ruby
    name: Ruby
    category: Programação
    level: advanced
    core: true
```

Competências são agrupadas por categoria e as `core` recebem destaque. Códigos de
nível estáveis são localizados durante a renderização. O perfil também aceita URLs
HTTP(S) explícitas em `linkedin` e `portfolio`.

## Verificação local

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m ruff check src tests scripts
```

Instale as ferramentas de desenvolvimento com `python -m pip install -e ".[dev]"`.

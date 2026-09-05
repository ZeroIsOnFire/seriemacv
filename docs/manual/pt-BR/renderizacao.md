# Currículos e estilos

[Voltar ao guia completo](index.md) · [English](../en/resume-rendering.md)

A geração de currículo é uma projeção somente leitura dos fatos em `career.yml` e
do documento editorial em `career.locales/<locale>.yml`, usando o catálogo da
aplicação em `i18n/<locale>.yml`. Cada saída é escrita atomicamente em um caminho
fixo dentro de `exports/`.

## Variantes estruturadas

O texto profissional reutilizável permanece em `career.locales/`; rótulos fixos,
meses, níveis e formato de data ficam em `i18n/`. Uma variante de vaga usa a estrutura
separada:

```text
resume/variants/<id>/
├── variant.yml
└── locales/
    ├── en.yml
    └── pt-BR.yml
```

`variant.yml` pode referenciar um `job_id` preservado, escolher um estilo e selecionar
ou ordenar IDs canônicos de experiência, formação e habilidades. Os arquivos em
`locales/` são overrides editoriais parciais: campos omitidos herdam o locale
de carreira. Eles não podem alterar nome, contatos, empresas, instituições, datas ou
outros fatos canônicos. Resumos ou destaques direcionados exigem `evidence_ids` que
existam e estejam marcados como `verified: true` em `career.yml`.

```powershell
seriemacv resume variants list .\minha-carreira
seriemacv resume variants validate .\minha-carreira
seriemacv resume variants validate .\minha-carreira --id vaga-plataforma
seriemacv resume render .\minha-carreira --variant vaga-plataforma --language pt-BR --format pdf
```

Artefatos de variante usam `exports/resume.<variante>.<locale>.<ext>` e nunca
sobrescrevem o currículo-base. A precedência de estilo é `--style`, depois o estilo
da variante e, por fim, o padrão do projeto. O locale de variante é opcional; sem ele,
a seleção e a ordem ainda se aplicam, mas todo o texto profissional vem de
`career.locales/<locale>.yml`.

## Listar estilos

```powershell
seriemacv resume styles
```

| Estilo | Layout | Situação ATS | Uso indicado |
| --- | --- | --- | --- |
| `clean` | Uma coluna, sans-serif neutro | ATS-safe | Candidaturas gerais |
| `classic` | Uma coluna, cabeçalho serifado centralizado | ATS-safe | Áreas tradicionais |
| `modern` | Uma coluna, hierarquia visual azul-marinho | ATS-safe | Apresentação contemporânea |
| `compact` | Uma coluna, espaçamento reduzido | ATS-safe | Carreiras mais extensas |
| `clean-executive` | Uma coluna, hierarquia formal | ATS-safe | Perfis seniores e de liderança |
| `sidebar` | Duas colunas | Experimental, não ATS-safe | Cópia visual para leitura humana |
| `timeline` | Faixa de datas e coluna principal | Experimental, não ATS-safe | Cronologia visual sem foto |
| `split-header`, `contact-band` | Layouts de duas colunas guiados pelo cabeçalho | Experimental, não ATS-safe | Cópias visuais para leitura humana |
| `left-rail`, `detail-sidebar` | Layouts com faixa lateral colorida | Experimental, não ATS-safe | Cópias visuais para leitura humana |

Os DOCX de `sidebar` e `timeline` usam tabelas sem bordas; seus HTML/PDF usam grades
visuais. Prefira um dos cinco estilos lineares quando o documento for analisado por
um sistema ATS.

Cada família também oferece um par `-alt`. Os IDs padrão exibem divisores nos títulos
das seções; os IDs `-alt` os removem sem alterar tipografia, espaçamento, layout,
formatos ou situação ATS. O cabeçalho centralizado do `classic` nunca possui divisor
inferior em nenhuma variante.

## Gerar um artefato

```powershell
seriemacv resume render .\minha-carreira --format markdown
seriemacv resume render .\minha-carreira --format html --style classic
seriemacv resume render .\minha-carreira --format pdf --style modern
seriemacv resume render .\minha-carreira --format docx --style compact
```

`--format` é obrigatório. `--style` é opcional e substitui `resume_style` somente
naquela execução.

## Cor

`resume_color` em `seriemacv.yml` define uma cor RGB hexadecimal. O padrão é
`#647D74`, o verde do mascote usado em `timeline`. Ela altera as cores principal e de
destaque de `modern`, `clean-executive`, `timeline`, `sidebar`, `split-header`,
`contact-band`, `left-rail`, `detail-sidebar` e suas variantes `-alt`; os demais
estilos mantêm as cores próprias. `#647D74` e `647D74` são aceitos.

| Formato | Saída | Observações |
| --- | --- | --- |
| `markdown` | `exports/resume.<locale>.md` | Texto portátil; fontes, cores e colunas são achatadas |
| `html` | `exports/resume.<locale>.html` | HTML semântico independente, com CSS embutido e sem recursos de rede |
| `pdf` | `exports/resume.<locale>.pdf` | PDF A4 gerado do HTML no Chromium local |
| `docx` | `exports/resume.<locale>.docx` | Documento Word editável produzido pelo renderer dedicado |

Renderizar outro estilo no mesmo formato substitui o artefato anterior daquele
formato. Os demais formatos não são alterados. Se a validação ou geração falhar, um
artefato existente é preservado.

O PDF canônico possui cache por conteúdo em `.seriemacv/cache/resume/`. Antes de
abrir o Chromium, o renderer compara uma assinatura de todos os dados canônicos e localizados, idioma,
estilo, cor e assets com a assinatura do PDF existente. Se estiverem iguais, o PDF
é reutilizado e a CLI informa `PDF (cached)`. Edições no YAML ou mudanças de
apresentação invalidam o cache automaticamente; não é necessário manter uma data de
atualização manual. Mesmo dados não impressos, como evidências, invalidam o cache ao
serem alterados. PDFs de variantes continuam sendo gerados separadamente e não
usam o cache canônico.

## Regras de conteúdo

- Experiência e formação são ordenadas em cronologia reversa.
- A ausência de `end_date` indica um registro atual.
- Seções opcionais vazias são omitidas.
- Resumo, destaques, localidades, vínculos e demais textos do usuário são preservados.
- Somente rótulos fixos, datas e níveis de competência são localizados.
- Evidências, respostas salvas e histórias não são impressas.
- O conteúdo é escapado antes de entrar no HTML.

## Pré-requisito para PDF

```powershell
python -m playwright install chromium
```

Se o Chromium não estiver disponível, o comando informa essa instalação e não
sobrescreve um PDF existente.

Consulte a [galeria de layouts compatíveis](../../styles.pt-BR.md)
para previews PNG e PDFs de exemplo.

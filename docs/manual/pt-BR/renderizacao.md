# Currículos e estilos

[Voltar ao guia completo](index.md) · [English](../en/resume-rendering.md)

A geração de currículo é uma projeção somente leitura dos fatos em `career.yml` e
do documento editorial em `career.locales/<locale>.yml`.
Cada saída é escrita atomicamente em um caminho fixo dentro de `exports/`.

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

| Formato | Saída | Observações |
| --- | --- | --- |
| `markdown` | `exports/resume.<locale>.md` | Texto portátil; fontes, cores e colunas são achatadas |
| `html` | `exports/resume.html` | HTML semântico independente, com CSS embutido e sem recursos de rede |
| `pdf` | `exports/resume.<locale>.pdf` | PDF A4 gerado do HTML no Chromium local |
| `docx` | `exports/resume.docx` | Documento Word editável produzido pelo renderer dedicado |

Renderizar outro estilo no mesmo formato substitui o artefato anterior daquele
formato. Os demais formatos não são alterados. Se a validação ou geração falhar, um
artefato existente é preservado.

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

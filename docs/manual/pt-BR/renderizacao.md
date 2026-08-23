# Currículos e estilos

[Voltar ao guia completo](index.md) · [English](../en/resume-rendering.md)

A geração de currículo é uma projeção somente leitura de um `career.yml` completo.
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
| `sidebar` | Duas colunas | Experimental, não ATS-safe | Cópia visual para leitura humana |

O DOCX `sidebar` usa uma tabela sem bordas e seu HTML/PDF usa uma grade visual. Prefira
um dos quatro estilos lineares quando o documento for analisado por um sistema ATS.

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
| `markdown` | `exports/resume.md` | Texto portátil; fontes, cores e colunas são achatadas |
| `html` | `exports/resume.html` | HTML semântico independente, com CSS embutido e sem recursos de rede |
| `pdf` | `exports/resume.pdf` | PDF A4 gerado do HTML no Chromium local |
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

Consulte a [galeria de estilos internos](../../../README.pt-BR.md#galeria-de-estilos-internos)
para previews PNG e PDFs de exemplo.

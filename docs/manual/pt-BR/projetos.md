# Projetos e configuração

[Voltar ao guia completo](index.md) · [English](../en/projects.md)

## Criar um projeto

```powershell
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style modern
```

| Argumento | Finalidade | Valores/padrão |
| --- | --- | --- |
| `path` | Diretório que armazenará o projeto | Obrigatório |
| `--name` | Nome legível do projeto | Obrigatório |
| `--language` | Locale BCP 47 padrão do currículo | Os locales incluídos são `pt-BR` e `en`; padrão `pt-BR` |
| `--style` | Estilo padrão do currículo | ID de uma família interna ou sua variante `-alt`; padrão `clean` |

As famílias são `clean`, `classic`, `modern`, `compact`, `clean-executive`,
`timeline`, `sidebar`, `split-header`, `contact-band`, `left-rail` e
`detail-sidebar`. Acrescente `-alt` para escolher a mesma família sem linhas
divisórias nas seções, por exemplo `modern-alt`.

`init` recusa sobrescrever um projeto existente. Ele cria um `career.yml` vazio e
pertencente ao usuário, exemplos fictícios, o índice SQLite local, diretórios de
exportação e diretórios reservados para funcionalidades futuras.

## Arquivos importantes

| Caminho | Função |
| --- | --- |
| `seriemacv.yml` | Configurações versionadas do projeto |
| `career.yml` | Fatos profissionais canônicos e independentes de idioma |
| `career.locales/<locale>.yml` | Texto reutilizável do currículo em um idioma |
| `i18n/<locale>.yml` | Rótulos fixos, meses, níveis e formato de data |
| `resume/variants/<id>/` | Seleção e overrides editoriais opcionais por vaga |
| `career.yml.example` | Contrato completo com dados fictícios |
| `career.locales/<locale>.yml.example` | Texto profissional localizado fictício |
| `i18n/<locale>.yml.example` | Catálogo fictício de traduções da aplicação |
| `seriemacv.yml.example` | Exemplo fictício de configuração |
| `exports/resume.*` | Artefatos gerados; nunca são dados canônicos |
| `.seriemacv/index/` | Estado SQLite interno e local |
| `jobs/` | Documentos estruturados locais de vagas e suas fontes preservadas |

## Configuração

```yaml
schema_version: 2
project_name: Minha carreira
resume_language: pt-BR
resume_style: modern
resume_color: "#647D74"
```

`resume_language` seleciona `career.locales/<locale>.yml`, que contém os textos do
currículo do usuário, e `i18n/<locale>.yml`, que contém títulos de seção, meses,
níveis, “Atual” e `date_format` do seriemaCV. Para adicionar um idioma como `es`, crie
`career.locales/es.yml` e `i18n/es.yml`; nenhuma alteração de código é necessária.
Antes de renderizar, execute
`seriemacv career locale validate <projeto> --language es`.
Os dois schemas são estritos: traduções da aplicação não podem ser colocadas em um
campo `catalog` dentro do locale de carreira.

Projetos criados antes de `resume_style` ou `resume_color` continuam compatíveis e usam
`clean` e o verde do mascote `#647D74`. Campos desconhecidos na configuração são
rejeitados para revelar erros de digitação cedo.

## Validar a estrutura do projeto

```powershell
seriemacv validate .\minha-carreira
```

Quando `path` é omitido, o diretório atual é validado. O comando verifica configuração,
diretórios, artefatos obrigatórios e o índice SQLite local. Ele não verifica se o
conteúdo do currículo está completo.

Para validar o conteúdo, continue em [Career Builder](career-builder.md).

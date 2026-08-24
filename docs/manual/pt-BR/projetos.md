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
| `--language` | Idioma dos rótulos fixos do currículo | `pt-BR` ou `en`; padrão `pt-BR` |
| `--style` | Estilo padrão do currículo | ID de uma família interna ou sua variante `-alt`; padrão `clean` |

As famílias são `clean`, `classic`, `modern`, `compact`, `clean-executive`, `sidebar`
e `timeline`. Acrescente `-alt` para escolher a mesma família sem linhas divisórias
nas seções, por exemplo `modern-alt`.

`init` recusa sobrescrever um projeto existente. Ele cria um `career.yml` vazio e
pertencente ao usuário, exemplos fictícios, o índice SQLite local, diretórios de
exportação e diretórios reservados para funcionalidades futuras.

## Arquivos importantes

| Caminho | Função |
| --- | --- |
| `seriemacv.yml` | Configurações versionadas do projeto |
| `career.yml` | Informações profissionais canônicas do usuário |
| `career.yml.example` | Contrato completo com dados fictícios |
| `seriemacv.yml.example` | Exemplo fictício de configuração |
| `exports/resume.*` | Artefatos gerados; nunca são dados canônicos |
| `.seriemacv/index/` | Estado SQLite interno e local |
| `jobs/` | Workspace preservado da funcionalidade pausada de vagas |

## Configuração

```yaml
schema_version: 2
project_name: Minha carreira
resume_language: pt-BR
resume_style: modern
resume_color: "#647D74"
```

`resume_language` traduz somente os rótulos mantidos pelo seriemaCV, como títulos de
seção, meses, níveis de competência e “Atual”. O conteúdo do usuário nunca é
traduzido.

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

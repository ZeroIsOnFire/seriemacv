# Career Builder

[Voltar ao guia completo](index.md) · [English](../en/career-builder.md)

Os dados de carreira são separados por responsabilidade. `career.yml` contém fatos
canônicos e independentes de idioma. `career.locales/<locale>.yml` contém o texto
reutilizável do currículo, como cargos, resumo, destaques e nomes localizados de
competências. Currículos gerados nunca escrevem alterações nesses arquivos.

| Seção canônica | Fatos em `career.yml` | Texto em `career.locales/<locale>.yml` |
| --- | --- | --- |
| `profile` | Nome, contato e links | Cargo, localização, idiomas e textos de trabalho |
| `experience` | ID, empresa e datas | Cargo, localização, tipo de vínculo e destaques |
| `education` | ID, instituição e datas | Formação, área, localização e destaques |
| `skills` | ID, nível, tags e prioridade editorial | Nome de exibição e categoria |
| `evidence` | Suporte rastreável para declarações profissionais | Não é localizado nem impresso |
| `answers` | Respostas reutilizáveis para fluxos futuros | Não é localizado nem impresso |
| `stories` | Histórias estruturadas em situação, ação e resultado | Não é localizado nem impresso |

O documento de locale também contém o `summary` profissional. Rótulos fixos de seção,
meses, nomes traduzidos dos níveis, “Atual” e `date_format` ficam em
`i18n/<locale>.yml`.

Todos os IDs de registros usam kebab-case minúsculo, como
`empresa-exemplo-senior`, e devem ser únicos dentro da seção. Datas usam `YYYY-MM`;
a data final não pode ser anterior à inicial. LinkedIn, portfólio e links nomeados
aceitam URLs HTTP(S) explícitas. O schema estrito rejeita campos desconhecidos.

## Validar o conteúdo profissional

```powershell
seriemacv career validate .\minha-carreira
```

Esse comando valida os fatos canônicos, incluindo nome e e-mail obrigatórios, sintaxe
YAML, campos desconhecidos, IDs duplicados, datas e referências de evidência. Valide
a projeção renderizável completa separadamente:

```powershell
seriemacv career locale list .\minha-carreira
seriemacv career locale validate .\minha-carreira --language pt-BR
```

A validação do locale exige os arquivos correspondentes
`career.locales/pt-BR.yml` e `i18n/pt-BR.yml`, verifica as referências de todos os
registros canônicos e confirma que o perfil composto possui um cargo localizado.
Quando possível, o diagnóstico inclui caminho do campo, linha e coluna.

## Preencher o perfil

`set-profile` faz uma alteração parcial; campos escalares omitidos mantêm seus valores.

```powershell
seriemacv career set-profile .\minha-carreira `
  --name "Seu Nome" `
  --email voce@example.com `
  --phone "+55 11 5555-0100" `
  --linkedin https://www.linkedin.com/in/exemplo `
  --portfolio https://example.invalid `
  --link GitHub=https://github.com/exemplo
```

`--link` é repetível, e links nomeados são mesclados com `profile.links`. LinkedIn e
portfólio também possuem campos dedicados. Edite cargo, localização, idiomas e outros
textos localizados do perfil em `career.locales/<locale>.yml`.

## Adicionar experiência

```powershell
seriemacv career add-experience .\minha-carreira `
  --id empresa-exemplo-senior `
  --company "Empresa Exemplo" `
  --start-date 2022-03 `
  --end-date 2025-08
```

`--id`, `--company` e `--start-date` são obrigatórios. Omita `--end-date` para o
vínculo atual. Depois adicione o mesmo ID em `experience` em cada locale de carreira
necessário, com o cargo e os destaques factuais.

## Adicionar formação

```powershell
seriemacv career add-education .\minha-carreira `
  --id universidade-exemplo `
  --institution "Universidade Exemplo" `
  --start-date 2014-01 `
  --end-date 2017-12
```

Instituição, ID e data inicial são obrigatórios. Adicione formação, área,
localização e destaques sob o ID correspondente em cada locale de carreira.

## Adicionar competências

```powershell
seriemacv career add-skill .\minha-carreira `
  --id python `
  --level advanced `
  --core `
  --tag backend
```

Os níveis são códigos estáveis em inglês: `beginner`, `intermediate`, `advanced` e
`expert`. A renderização traduz esses códigos. `--core` marca prioridade editorial e
faz a competência receber destaque. Adicione o nome de exibição e a categoria sob o
ID correspondente em cada locale de carreira. Categorias organizam a lista completa;
uma competência sem categoria só aparece no grupo traduzido “Outras” quando também
existirem competências categorizadas.

## Adicionar evidências

```powershell
seriemacv career add-evidence .\minha-carreira `
  --id confiabilidade-deploy `
  --statement "Melhorou a confiabilidade de deploys com verificações automatizadas." `
  --experience-id empresa-exemplo-senior `
  --detail "Mudança documentada no relatório interno de entregas." `
  --tag confiabilidade `
  --verified
```

Tags e detalhes são repetíveis. `--experience-id` deve apontar para uma experiência
existente. Omita `--verified` quando a declaração ainda precisar de confirmação. A
evidência fica no documento canônico, mas não é impressa nos currículos.

## Inspecionar seções

```powershell
seriemacv career list .\minha-carreira profile
seriemacv career list .\minha-carreira experience
seriemacv career list .\minha-carreira skills
```

As seções canônicas válidas são `profile`, `experience`, `education`, `skills`,
`evidence`, `answers` e `stories`. A saída é YAML validado, adequado para inspeção ou
consumo por outra ferramenta local. Os documentos de locale continuam sendo YAML
diretamente inspecionável.

## Campos sem comandos de edição

A CLI ainda não edita textos localizados, respostas salvas, histórias ou registros
existentes. Edite fatos canônicos em `career.yml` e textos profissionais em
`career.locales/<locale>.yml`, seguindo seus arquivos `.example`. Depois execute
`career validate` e `career locale validate`. Campos desconhecidos são rejeitados, e
uma escrita inválida pela CLI não modifica o arquivo canônico.

Continue em [Currículos e estilos](renderizacao.md).

# Career Builder

[Voltar ao guia completo](index.md) · [English](../en/career-builder.md)

`career.yml` é a fonte canônica para perfil, resumo, experiências, formação,
competências, evidências, respostas salvas e histórias. Currículos gerados nunca
escrevem alterações de volta nele.

| Seção | Finalidade | Impressa nos currículos |
| --- | --- | --- |
| `profile` | Identidade, contato, links, idiomas e preferências de trabalho | Campos de contato e idiomas |
| `summary` | Resumo profissional escrito pelo usuário | Sim |
| `experience` | Histórico profissional e destaques factuais | Sim |
| `education` | Formação e seus destaques | Sim |
| `skills` | Competências categorizadas, nível, tags e prioridade editorial | Sim, exceto tags |
| `evidence` | Suporte rastreável para declarações profissionais | Não |
| `answers` | Respostas reutilizáveis para fluxos futuros | Não |
| `stories` | Histórias estruturadas em situação, ação e resultado | Não |

Todos os IDs de registros usam kebab-case minúsculo, como
`empresa-exemplo-senior`, e devem ser únicos dentro da seção. Datas usam `YYYY-MM`;
a data final não pode ser anterior à inicial. LinkedIn, portfólio e links nomeados
aceitam URLs HTTP(S) explícitas. O schema estrito rejeita campos desconhecidos.

## Validar o conteúdo profissional

```powershell
seriemacv career validate .\minha-carreira
```

Um documento renderizável exige pelo menos `profile.name`, `profile.title` e
`profile.email`. A validação também encontra YAML inválido, campos desconhecidos, IDs
duplicados, datas fora de `YYYY-MM`, seções malformadas e evidências que apontam para
experiências inexistentes. Quando possível, o diagnóstico inclui caminho do campo,
linha e coluna.

## Preencher o perfil

`set-profile` faz uma alteração parcial; campos escalares omitidos mantêm seus valores.

```powershell
seriemacv career set-profile .\minha-carreira `
  --name "Seu Nome" `
  --title "Engenheiro de Software Sênior" `
  --location "Cidade, País" `
  --email voce@example.com `
  --phone "+55 11 5555-0100" `
  --linkedin https://www.linkedin.com/in/exemplo `
  --portfolio https://example.invalid `
  --work-preference "Remoto" `
  --work-authorization "Autorizado" `
  --notice-period "30 dias" `
  --language Português `
  --language Inglês `
  --link GitHub=https://github.com/exemplo
```

`--language` e `--link` são repetíveis. Informar idiomas substitui a lista atual. Links
nomeados são mesclados com `profile.links`. LinkedIn e portfólio também possuem campos
dedicados.

## Adicionar experiência

```powershell
seriemacv career add-experience .\minha-carreira `
  --id empresa-exemplo-senior `
  --company "Empresa Exemplo" `
  --title "Engenheiro Sênior" `
  --start-date 2022-03 `
  --location "Remoto" `
  --employment-type "Tempo integral" `
  --highlight "Melhorou a confiabilidade das entregas." `
  --highlight "Orientou outros engenheiros."
```

`--id`, `--company`, `--title` e `--start-date` são obrigatórios. Use `--end-date
YYYY-MM` em um vínculo encerrado. Omita-o para o vínculo atual. `--highlight` é
repetível e deve conter somente informações factuais.

## Adicionar formação

```powershell
seriemacv career add-education .\minha-carreira `
  --id universidade-exemplo `
  --institution "Universidade Exemplo" `
  --degree "Tecnólogo" `
  --field-of-study "Desenvolvimento de Software" `
  --location "Cidade, País" `
  --start-date 2014-01 `
  --end-date 2017-12 `
  --highlight "Concluiu um projeto final de software."
```

Instituição, formação, ID e data inicial são obrigatórios. Destaques da formação também
são repetíveis.

## Adicionar competências

```powershell
seriemacv career add-skill .\minha-carreira `
  --id python `
  --name Python `
  --category Programação `
  --level advanced `
  --core `
  --tag backend
```

Os níveis são códigos estáveis em inglês: `beginner`, `intermediate`, `advanced` e
`expert`. A renderização traduz esses códigos. `--core` marca prioridade editorial e
faz a competência receber destaque. Categorias organizam a lista completa; uma
competência sem categoria só aparece no grupo traduzido “Outras” quando também
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

As seções válidas são `profile`, `summary`, `experience`, `education`, `skills`,
`evidence`, `answers` e `stories`. A saída é YAML validado, adequado para inspeção ou
consumo por outra ferramenta local.

## Campos sem comandos de edição

A CLI ainda não edita o resumo, respostas salvas, histórias ou registros existentes.
Edite essas seções diretamente no `career.yml`, seguindo `career.yml.example`, e rode
`career validate`. Campos desconhecidos são rejeitados, e uma escrita inválida pela
CLI não modifica o arquivo.

Continue em [Currículos e estilos](renderizacao.md).

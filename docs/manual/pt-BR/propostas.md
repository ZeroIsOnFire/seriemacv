# Propostas locais de IA

[Voltar ao guia completo](index.md) · [English](../en/proposals.md)

O seriemaCV usa uma troca de YAML agnóstica de provedor. Ele não chama API, não inicia
um agente e não envia dados automaticamente. Codex, Claude Code ou uma pessoa podem
ler um arquivo de pedido e escrever uma resposta; o seriemaCV valida e aplica somente
itens aceitos explicitamente.

## Criar um pedido

Visualize o YAML local exato antes de criar ou compartilhar um pedido:

```powershell
seriemacv proposal preview .\minha-carreira `
  --id plataforma-tailoring `
  --variant-id vaga-plataforma `
  --language pt-BR
```

`preview` é somente leitura: não grava arquivo nem envia dados. Seu YAML é idêntico
ao pedido gravado pelo comando abaixo.

```powershell
seriemacv proposal request .\minha-carreira `
  --id plataforma-tailoring `
  --variant-id vaga-plataforma `
  --language pt-BR `
  --output .\pedido-plataforma.yml
```

O pedido contém textos localizados do currículo, cargos, registros profissionais e
somente evidências verificadas. Ele exclui email, telefone, links, respostas salvas,
histórias e evidências pendentes. Compartilhe-o apenas com o agente escolhido.

## Escrever uma resposta

O agente externo grava YAML estrito. Cada item tem ID, confiança, informações
pendentes e IDs de evidência. `variant_selection` e `variant_locale` formam uma
variante; `cover_letter` produz um artefato Markdown separado.

```yaml
schema_version: 1
request_id: plataforma-tailoring
items:
  - id: selecao
    kind: variant_selection
    selection: {experience: [cargo-atual], education: [], skills: [python]}
    style: clean
    evidence_ids: []
    confidence: high
    pending_information: []
  - id: texto
    kind: variant_locale
    locale_override:
      summary: Desenvolve serviços de plataforma confiáveis.
    evidence_ids: [entrega-plataforma]
    confidence: medium
    pending_information: [Confirme a senioridade da vaga.]
  - id: carta
    kind: cover_letter
    body: Tenho interesse nesta oportunidade de engenharia de plataforma.
    evidence_ids: [entrega-plataforma]
    confidence: medium
    pending_information: []
```

Toda alegação em texto direcionado ou carta exige evidência existente em `career.yml`
e marcada como `verified: true`. IDs desconhecidos, pendentes ou repetidos são
rejeitados.

## Revisar e aplicar

```powershell
seriemacv proposal review .\minha-carreira .\pedido-plataforma.yml .\resposta-plataforma.yml
seriemacv proposal apply .\minha-carreira .\pedido-plataforma.yml .\resposta-plataforma.yml `
  --accept selecao --accept texto --accept carta
```

A revisão imprime um diff YAML por item. Omita um item de `--accept` para rejeitá-lo.
Itens de variante aceitos criam `resume/variants/<variant-id>/`; uma carta aceita
grava `exports/cover-letters/<proposal-id>.<locale>.md`. Fatos canônicos nunca são
alterados, e uma variante existente nunca é sobrescrita.

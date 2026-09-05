# Vagas e match

[Voltar ao guia completo](index.md) · [English](../en/jobs-and-match.md)

As vagas são documentos YAML locais e estruturados. O texto-fonte importado permanece
guardado no registro canônico da vaga.

```powershell
seriemacv jobs import .\minha-carreira .\vaga.yml
seriemacv jobs import .\minha-carreira .\vagas.zip
seriemacv jobs list .\minha-carreira
seriemacv jobs show .\minha-carreira engenheiro-plataforma
seriemacv jobs extract-requirements .\minha-carreira engenheiro-plataforma
```

Quando a vaga não tem requisitos estruturados, `extract-requirements` apenas imprime
candidatos conservadores e determinísticos; ele nunca altera o arquivo.

Gere o relatório com:

```powershell
seriemacv match .\minha-carreira engenheiro-plataforma
```

O YAML apresenta cada requisito, classificação oficial, `evidence_ids` verificados,
lacunas, conflitos, notas de entrevista e score ponderado. Somente evidências
verificadas sustentam conclusões positivas ou conflitos. `NO_EVIDENCE` não tem IDs e
nunca aumenta o score.

Agentes de IA que complementem esse relatório com elegibilidade, remuneração,
pesquisa de empresa ou prioridade devem seguir a [diretriz de análise de vagas](../../agent-job-analysis-guideline.pt-BR.md).
Essas conclusões são consultivas e não alteram os dados canônicos de vaga ou carreira.

Os pesos ficam em `seriemacv.yml`, são não negativos e devem totalizar 100:

```yaml
match_weights:
  core_technical_fit: 35
  experience_seniority: 20
  responsibilities: 15
  domain: 10
  location_schedule: 10
  language: 5
  other_constraints: 5
```

Para solicitar uma variante voltada à vaga por um agente local, inclua `--job-id` no
comando `proposal request`. O pedido leva o relatório e evidências verificadas, mas a
proposta continua separada e exige revisão e aceite explícito.

## MCP

`seriemacv-mcp` é um servidor MCP local por stdio, compatível com hosts como Codex e
Claude Code. Ele expõe busca, leitura de vagas e relatório de match, além de pedido de
tailoring que não grava nada no projeto.

## Studio local

Inicie o primeiro workspace de vagas somente leitura com
`seriemacv studio .\minha-carreira`. Ele atende apenas em `127.0.0.1` por padrão,
mostra vagas importadas e seus relatórios determinísticos e não oferece edição ou envio.

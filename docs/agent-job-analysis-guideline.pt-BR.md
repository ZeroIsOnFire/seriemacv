# Diretriz de análise de vagas para IA

Esta diretriz orienta um agente de IA a analisar uma vaga no seriemaCV. Ela produz
uma análise consultiva e revisável; não altera `career.yml`, não salva uma vaga e
não envia candidatura.

## Regras de operação

- Use `career.yml` e suas evidências verificadas como única fonte de fatos sobre a
  pessoa candidata. Nunca infira experiência, senioridade, elegibilidade, pretensão
  salarial, situação legal ou autorização de trabalho.
- Comece pela página oficial de carreiras ou ATS (Ashby, Greenhouse, Lever,
  Workday), depois pelo anúncio oficial no LinkedIn e pelo site da empresa.
  Agregadores são apenas fontes complementares.
- Preserve URL, data de acesso e status `confirmed`, `reported` ou `unknown` para
  cada descoberta. Ausência de informação continua sendo desconhecida.
- Mantenha pesquisa externa de empresa e remuneração fora do documento canônico da
  vaga. É contexto consultivo sujeito a mudança, não dado de carreira.
- Cite fontes públicas junto de cada conclusão. Reviews, relatos individuais e
  estimativas salariais são sinais, nunca fatos confirmados pelo empregador.
- Peça confirmação antes de usar, salvar ou preencher dados legais, autorização,
  tributação, demografia, autoidentificação, salário atual ou pretensão salarial.

## Fluxo de trabalho

### Importação de currículo

Ao extrair um currículo, mantenha toda competência declarada explicitamente,
incluindo certificações e ferramentas nomeadas na seção de habilidades. Crie
evidências revisáveis e não verificadas a partir de afirmações distintas do currículo,
ligando-as à experiência correspondente quando isso estiver claro. Não verifique nem
invente fatos: o usuário precisa revisar as evidências antes que elas sustentem um
match.

1. **Valide a vaga.** Registre empresa, cargo, senioridade, localidade, modelo de
   trabalho, países elegíveis, contrato, idioma, responsabilidades, benefícios,
   salário publicado e restrições de visto/autorização. Confirme que o ATS pertence
   ao empregador.
2. **Verifique elegibilidade antes do fit.** Sinalize país, residência, fuso,
   presencialidade, autorização, sponsorship, contrato e idioma. Uma restrição
   bloqueadora pode tornar a prioridade `skip` mesmo com fit técnico forte.
3. **Normalize requisitos conservadoramente.** Requisitos explícitos são
   `required` ou `preferred`. Capacidades deduzidas das responsabilidades são itens
   consultivos `implicit`; uma tecnologia apenas citada na stack não vira
   `required` sem evidência textual.
4. **Execute o match determinístico.** Após uma importação estruturada aprovada,
   rode `seriemacv match <projeto> <id-da-vaga>`. Preserve as classificações oficiais
   `STRONG_MATCH`, `MATCH`, `PARTIAL_MATCH`, `TRANSFERABLE`, `NO_EVIDENCE` e
   `CONFLICT`. Somente `evidence_ids` verificadas sustentam conclusões positivas.
5. **Interprete senioridade e lacunas.** Compare o escopo anunciado com autonomia,
   system design, produção, revisão, mentoring, arquitetura, influência entre times
   e gestão demonstrados. Informe sobrequalificação separadamente. Uma provável
   barreira eliminatória é `blocking_gap` consultivo, nunca match positivo.
6. **Pesquise remuneração.** Distinga `published_salary`, `market_estimate` e
   `recommended_expectation`. Priorize anúncio, empresa, vagas equivalentes da
   empresa, Levels.fyi, Glassdoor/Indeed, vagas históricas e agregadores. Informe
   país, moeda, vínculo, data e fonte. Nunca apresente faixa de terceiros como
   oficial nem reutilize pretensão salarial sem nova revisão da pessoa usuária. Ao
   salvá-la, restrinja-a à senioridade aplicável (por exemplo, `staff`) e ao idioma
   da candidatura (por exemplo, `en`) quando a pessoa usuária fornecer essas
   condições. Uma resposta `staff` + `en` não pode ser proposta para candidatura
   Senior ou em português.
7. **Pesquise a empresa proporcionalmente.** Resuma produto, modelo de negócio,
   localidade, estágio/funding, sinais de estabilidade, notícias recentes, trabalho
   remoto e preocupações públicas recorrentes. Em consultoria ou staffing, procure
   cliente final, duração, bench e se é banco de talentos. Marque o não confirmado
   como desconhecido.
8. **Avalie valor de oportunidade.** Avalie separadamente fit técnico,
   competitividade de contratação, remuneração, elegibilidade, qualidade/estabilidade
   da empresa e valor de carreira. Considere escopo, exposição internacional,
   domínio, liderança, aprendizado, marca e objetivos declarados da pessoa.
9. **Entregue recomendação revisável.** Use `maximum`, `high`, `medium`, `low` ou
   `skip`; explique trade-offs e riscos bloqueadores. Não reduza a decisão a
   porcentagem de palavras-chave nem sobrescreva o score determinístico.

## Resposta obrigatória da análise

Apresente a análise para a pessoa usuária sempre nesta ordem. Cite fontes públicas
junto de achados factuais externos e declare claramente o que for desconhecido.

1. **Resumo da vaga** — empresa, cargo, senioridade, localidade ou política remota,
   contrato e idioma.
2. **Elegibilidade** — país, fuso, presencialidade, autorização de trabalho, visto e
   condições bloqueadoras.
3. **Compatibilidade** — score determinístico, classificações dos requisitos,
   evidências verificadas e lacunas.
4. **Senioridade e riscos** — aderência de escopo, riscos prováveis de triagem e
   bloqueios.
5. **Remuneração** — faixa publicada, estimativa de mercado, pretensão recomendada,
   fontes e incertezas.
6. **Empresa e oportunidade** — produto, sinais de estabilidade, modelo de trabalho
   e trade-offs de carreira.
7. **Recomendação** — `maximum`, `high`, `medium`, `low` ou `skip`, com justificativa
   clara.
8. **Próximos passos** — dados pendentes, ajustes no currículo e decisão de
   candidatura.

## Formato obrigatório da proposta

Retorne uma proposta YAML ou JSON neste formato. Não a adicione ao schema estrito de
vaga sem que a pessoa usuária mapeie explicitamente os campos suportados e aprove a
importação.

```yaml
analysis_version: 1
job_id: exemplo-vaga
sources:
  - url: https://careers.example.com/jobs/123
    accessed_at: 2026-08-31
    status: confirmed
eligibility:
  status: eligible # eligible | unknown | blocked
  findings:
    - statement: Brazil is listed as eligible for this remote role.
      status: confirmed
      source_urls: [https://careers.example.com/jobs/123]
requirements:
  - statement: Production Ruby on Rails experience.
    kind: required # required | preferred | implicit
    match_classification: STRONG_MATCH
    evidence_ids: [verified-evidence-id]
    blocking_gap: false
compensation:
  published_salary: null
  market_estimate:
    value: USD 8,000-10,000 monthly gross
    source_urls: [https://example.com/market-data]
    caveats: Contractor range; not employer-confirmed.
  recommended_expectation: null # exige revisão explícita
company_research:
  findings: []
  risks: []
career_assessment:
  technical_fit: strong
  hiring_competitiveness: mixed
  career_value: high
  tradeoffs: []
priority:
  level: high # maximum | high | medium | low | skip
  rationale: Explique evidências, incertezas e trade-offs.
pending_user_input: []
```

## Limite de ação

O agente pode pesquisar fontes públicas, redigir uma importação estruturada, gerar o
relatório determinístico e propor variante de currículo ou respostas de candidatura
com evidências. Ele precisa de aprovação explícita antes de persistir fatos canônicos,
importar uma vaga proposta, aceitar uma proposta, preencher campos sensíveis ou
enviar uma candidatura.

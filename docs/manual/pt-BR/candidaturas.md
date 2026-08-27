# Candidaturas assistidas

`applications/<id>.yml` é o registro canônico local de uma candidatura. Ele liga a
vaga estruturada, uma variante opcional do currículo, anexos, respostas confirmadas
e perguntas pendentes. Senhas, cookies e valores de formulário não entram nos
diagnósticos.

```powershell
seriemacv applications create .\minha-carreira --id candidatura-plataforma --job-id vaga-plataforma --variant-id vaga-plataforma --url https://example.invalid/apply
seriemacv applications validate .\minha-carreira
seriemacv applications prepare .\minha-carreira candidatura-plataforma --interactive
seriemacv applications questions .\minha-carreira candidatura-plataforma
seriemacv applications apply-answer .\minha-carreira candidatura-plataforma question-why --answer "..." --save-answer-id por-que-plataforma
seriemacv applications set-status .\minha-carreira candidatura-plataforma applied
```

`prepare --interactive` abre um perfil persistente isolado em
`.seriemacv/browser`. O login é manual. O preparador genérico preenche apenas dados
seguros do perfil e respostas salvas não sensíveis; os campos obrigatórios sem
resolução tornam-se perguntas. Declarações legais, autorização de trabalho,
salário, demografia e autoidentificação nunca são preenchidos automaticamente.

Um agente externo via MCP pode ler candidaturas e perguntas e devolver uma proposta
revisável. O usuário deve aplicar a resposta explicitamente na CLI; com
`--save-answer-id`, a resposta confirmada também é salva em `career.yml`. Respostas
sensíveis podem ser salvas, mas nunca são reutilizadas automaticamente.

Para formulários com rótulos inconsistentes ou carta de apresentação, use o fluxo
opcional com agente externo. `prepare --ai-assisted` inclui campos opcionais sem
resolução na fila de perguntas. A solicitação leva apenas a identificação da vaga,
os rótulos detectados e evidências verificadas; ela exclui contatos, senhas, cookies
e valores de formulário.

```powershell
seriemacv applications prepare .\minha-carreira candidatura-plataforma --interactive --ai-assisted
seriemacv applications ai-request .\minha-carreira candidatura-plataforma --request-id formulario-plataforma --output .\formulario-request.yml
# Peça a Codex, Claude Code ou outro agente local que devolva um YAML de resposta.
seriemacv applications ai-review .\minha-carreira .\formulario-request.yml .\formulario-response.yml
seriemacv applications ai-apply .\minha-carreira .\formulario-request.yml .\formulario-response.yml --accept resposta-por-que --accept carta
```

A resposta pode mapear nomes semânticos de campos e propor uma carta separada, mas
cada item aceito é selecionado individualmente. O agente não pode propor respostas
para campos sensíveis. Execute `prepare` novamente após aceitar respostas para
preencher os valores aprovados na sessão local do navegador.

Não existe comando de envio. Revise a página e envie manualmente no navegador; em
seguida registre `applied`. Use `clear-browser-profile` para remover o perfil
isolado.

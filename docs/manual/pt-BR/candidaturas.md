# Candidaturas assistidas

`applications/<id>.yml` é o registro canônico local de uma candidatura. Ele liga a
vaga estruturada, uma variante opcional do currículo, anexos, respostas confirmadas
e perguntas pendentes. Senhas, cookies e valores de formulário não entram nos
diagnósticos.

```powershell
seriemacv applications create .\minha-carreira --id candidatura-plataforma --job-id vaga-plataforma --variant-id vaga-plataforma --url https://example.invalid/apply
seriemacv applications validate .\minha-carreira
seriemacv applications prepare .\minha-carreira candidatura-plataforma --interactive
seriemacv applications prepare-job .\minha-carreira vaga-plataforma --url https://example.invalid/apply --interactive
seriemacv applications context .\minha-carreira vaga-plataforma-application
seriemacv applications questions .\minha-carreira candidatura-plataforma
seriemacv applications apply-answer .\minha-carreira candidatura-plataforma question-why --answer "..." --save-answer-id por-que-plataforma
seriemacv applications set-status .\minha-carreira candidatura-plataforma applied
```

`prepare --interactive` abre um perfil persistente isolado em
`.seriemacv/browser`. O login é manual. Enquanto a janela estiver aberta, use os
comandos `refill`, `inspect` e `close` no terminal para controlar a mesma sessão. O
comando `inspect` e a verificação final apenas observam e atualizam pendências;
somente `refill` repete preenchimento e upload. O preparador genérico preenche apenas
dados seguros do perfil e respostas salvas não sensíveis; os campos obrigatórios sem
resolução tornam-se perguntas. As perguntas são persistidas antes do upload, mesmo
quando uma etapa posterior falha. Declarações legais, autorização de trabalho,
salário, demografia e autoidentificação nunca são preenchidos automaticamente.

`prepare-job` valida a vaga, cria ou reutiliza sua candidatura, seleciona a única
variante vinculada quando houver, resolve ou reutiliza o PDF antes de abrir o
navegador e inicia a preparação. Comboboxes Greenhouse só são considerados
preenchidos depois que uma opção visível com texto correspondente é selecionada e o
valor final é confirmado; controles que falham ficam pendentes sem novas tentativas
automáticas naquela sessão.
Use `--application-id` ou `--variant-id` quando houver mais de uma opção. O comando
`context` retorna somente o estado, anexos, respostas confirmadas, pendências e a
próxima ação. Respostas sensíveis aparecem apenas como confirmação redigida.

Prefira uma conversa de agente por vaga e use a saída de `context` para retomar o
trabalho sem carregar o histórico de outras candidaturas.

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
seriemacv applications ai-preview .\minha-carreira candidatura-plataforma --request-id formulario-plataforma
seriemacv applications ai-request .\minha-carreira candidatura-plataforma --request-id formulario-plataforma --output .\formulario-request.yml
# Peça a Codex, Claude Code ou outro agente local que devolva um YAML de resposta.
seriemacv applications ai-review .\minha-carreira .\formulario-request.yml .\formulario-response.yml
seriemacv applications ai-apply .\minha-carreira .\formulario-request.yml .\formulario-response.yml --accept resposta-por-que --accept carta
```

`ai-preview` imprime o YAML exato do pedido sem gravá-lo nem enviar dados. Revise-o
antes de compartilhá-lo com um agente externo; o arquivo de `ai-request` seguinte tem
o mesmo conteúdo.

A resposta pode mapear nomes semânticos de campos e propor uma carta separada, mas
cada item aceito é selecionado individualmente. O agente não pode propor respostas
para campos sensíveis. Execute `prepare` novamente após aceitar respostas para
preencher os valores aprovados na sessão local do navegador.

Não existe comando de envio. Revise a página e envie manualmente no navegador; em
seguida registre `applied`. Use `clear-browser-profile` para remover o perfil
isolado.

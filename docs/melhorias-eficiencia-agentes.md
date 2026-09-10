# Melhorias de eficiência para agentes

Este documento registra melhorias para reduzir o uso de contexto, chamadas ao modelo
e repetições durante importação, análise e candidatura a vagas no seriemaCV.

Os itens de agrupamento de perguntas, sessão persistente, preparação integrada,
contexto compacto, conversa por vaga e exclusão do estado local do Git foram
implementados. Limites automáticos de saída, adaptadores por plataforma e métricas
locais permanecem como próximas melhorias.

## Diagnóstico observado

Em uma sessão com duas candidaturas, os registros locais indicaram aproximadamente
9,55 milhões de tokens processados. Cerca de 9,50 milhões eram tokens de entrada e
8,95 milhões estavam em cache. A principal ocorrência isolada foi a tentativa de
exibir um HTML minificado em uma única linha, que gerou cerca de 178 mil tokens antes
do truncamento.

Também contribuíram para o consumo:

- histórico crescente reapresentado a cada etapa;
- várias rodadas entre o modelo e ferramentas para operações determinísticas;
- releitura de YAML, HTML e resultados já validados;
- reinicializações do navegador para preencher o mesmo formulário;
- tentativas repetidas em controles de formulário instáveis;
- detecção de cada opção de radio como uma pergunta independente.

## Prioridade alta

### Limitar extrações e saídas

- Verificar tamanho, quantidade de linhas e formato antes de ler um artefato externo.
- Salvar HTML e respostas de API localmente sem devolvê-los integralmente ao modelo.
- Extrair somente campos necessários por parser de HTML ou JSON.
- Aplicar limites de caracteres, linhas e itens às saídas dos comandos.
- Interromper a operação com uma mensagem objetiva quando o conteúdo não puder ser
  resumido de forma segura.

Critério de conclusão: nenhum fluxo normal de vaga imprime HTML minificado, resposta
integral de API, log de sessão ou YAML grande no contexto do agente.

### Agrupar controles de formulário

- Agrupar `radio` e `checkbox` pelo nome e pela pergunta visível.
- Representar as opções em uma única pergunta estruturada.
- Ignorar campos opcionais vazios que não exigem decisão do usuário.
- Verificar a alternativa selecionada pelo rótulo, sem depender da ordem no DOM.

Critério de conclusão: o formulário da Megaport gera uma pergunta para proficiência
em inglês e uma pergunta opcional para pronomes, em vez de uma pergunta por opção.

### Criar adaptadores por plataforma

- Implementar adaptadores para Lever, Greenhouse e FullStack.
- Centralizar mapeamento de perfil, upload, perguntas e validação por plataforma.
- Usar o detector genérico apenas quando não houver adaptador compatível.
- Manter CAPTCHA, autenticação e envio final sob controle do usuário.

Critério de conclusão: uma candidatura conhecida pode ser preparada em uma execução
determinística, sem criar scripts temporários específicos para a vaga.

### Controlar uma sessão persistente do navegador

- Manter uma sessão identificável por candidatura.
- Aceitar comandos locais como `fill`, `inspect`, `review` e `close`.
- Permitir novo preenchimento sem fechar ou relançar a janela.
- Recuperar com segurança uma sessão encerrada ou um perfil bloqueado.

Critério de conclusão: o agente consegue corrigir um campo na janela já aberta sem
refazer navegação, inspeção, upload e preenchimento dos demais campos.

## Prioridade média

### Integrar a preparação da candidatura

Criar um comando semelhante a:

```text
seriemacv applications prepare-job JOB_ID
```

O comando deve validar a vaga, selecionar ou renderizar o currículo necessário,
detectar perguntas, preencher respostas revisadas e abrir o navegador em uma única
execução. O resultado deve ser um resumo estruturado e curto.

### Produzir contexto compacto

Criar um comando `applications context ID` que retorne somente:

- estado atual;
- currículo e anexos selecionados;
- respostas confirmadas;
- campos obrigatórios pendentes;
- último resultado observável;
- próxima ação permitida.

O agente deve usar esse resumo em vez de reler o documento completo da candidatura.

### Instrumentar operações caras

- Registrar localmente quantidade de chamadas e bytes retornados por operação.
- Alertar quando uma saída ultrapassar o limite configurado.
- Mostrar os maiores resultados sem incluir dados pessoais ou conteúdo integral.
- Separar métricas de entrada, saída, cache e chamadas de navegador.

Critério de conclusão: uma saída anormal é identificada na mesma etapa em que ocorre.

## Práticas operacionais

- Usar uma conversa nova por vaga quando o histórico anterior não for necessário.
- Reutilizar documentos, análises, PDFs e respostas já validados.
- Agrupar leituras independentes e etapas determinísticas na mesma chamada.
- Executar uma inspeção do formulário e depois preencher e validar em lote.
- Após duas falhas idênticas, mudar a abordagem ou entregar o controle ao usuário.
- Usar modelos e níveis de raciocínio menores em tarefas rotineiras quando disponíveis
  e suficientes para o resultado esperado.
- Manter perfis e artefatos temporários do navegador fora do Git.

## Ordem sugerida de implementação

1. Corrigir o agrupamento de perguntas.
2. Adicionar limites técnicos de saída e parsers seletivos.
3. Implementar o adaptador do Lever e seus testes.
4. Implementar controle persistente da sessão do navegador.
5. Criar `applications context` e o comando integrado de preparação.
6. Adicionar métricas locais e adaptar outras plataformas.

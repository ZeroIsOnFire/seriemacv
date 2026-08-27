# Plano: prévia do contexto de IA

## Objetivo

Exibir o YAML completo e exato que uma pessoa poderá compartilhar com um agente
externo, sem que o seriemaCV envie dados automaticamente.

## Implementação planejada

- Adicionar `seriemacv proposal preview`, com os argumentos de `proposal request`
  exceto `--output`, para imprimir um `ProposalRequest` somente leitura.
- Adicionar `seriemacv applications ai-preview`, com os argumentos necessários para
  gerar um `ApplicationAiRequest` somente leitura.
- Reutilizar os mesmos casos de uso e serializadores dos comandos de gravação para
  assegurar que a prévia e o arquivo gerado sejam idênticos.
- Manter os comandos atuais e a troca local de YAML; não haverá chamada de API,
  agente iniciado automaticamente ou confirmação adicional.

## Garantias e validação

- Cobrir os dois comandos pela CLI, incluindo ausência de escrita no projeto.
- Confirmar que contatos, evidências pendentes, senhas, cookies e valores de
  formulário continuam excluídos quando aplicável.
- Atualizar os manuais em inglês e português e concluir o item correspondente do
  checklist após a implementação.

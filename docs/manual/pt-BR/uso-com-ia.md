# Usar o Seriema com IA

[Voltar ao guia completo](index.md) · [English](../en/using-ai.md)

Um agente de IA trabalha com um projeto local do Seriema; ele não é dono do projeto
nem inventa fatos de carreira. Informe o local do projeto quando necessário e deixe o
resultado desejado explícito. Revise toda mudança canônica proposta e toda resposta
sensível de candidatura.

## Importar e avaliar uma vaga

```text
Importe esta vaga: https://careers.example.com/jobs/123.
Valide o anúncio, analise minha compatibilidade, identifique lacunas e riscos de
elegibilidade e pesquise uma pretensão salarial com fontes.
```

O agente deve localizar a vaga oficial quando possível, criar um registro local de
vaga validado após aprovação e entregar um match explicável. Deve diferenciar a
remuneração publicada pelo empregador de uma estimativa de mercado e de informações
desconhecidas.

## Melhorar dados verificados e gerar currículos novamente

```text
Nas evidências da minha carreira, adicione `NoSQL` a cada item verificado que já cite
MongoDB ou Redis e adicione `REST` aos itens que já citam uma API. Depois valide minha
carreira e gere novamente os currículos PDF e DOCX em inglês e português.
```

O agente só aplica a alteração no YAML canônico quando o usuário a solicita
explicitamente. Ele só pode regenerar artefatos depois que o documento de carreira validar.

## Preparar uma candidatura

```text
Vamos nos inscrever em platform-engineer. Minha pretensão é R$ 20.000.
Primeiro confira se a análise de compatibilidade está atual. Prepare o currículo em
inglês e as respostas da candidatura, pergunte os campos obrigatórios que faltarem e
abra a candidatura no Playwright para eu revisar.
```

O agente não pode supor autorização de trabalho, visto, demografia, tributação,
salário atual ou pretensão salarial. Ele abre o navegador para você fazer login e
inspecionar o formulário. Só envia com sua autorização explícita.

## Registrar o resultado

```text
Enviei a candidatura para Platform Engineer. Marque-a como aplicada.
```

O agente atualiza somente o registro local da candidatura. Ele deve informar
perguntas pendentes ou falhas, em vez de presumir que a candidatura externa deu certo.

## Limite de privacidade

Antes de compartilhar qualquer solicitação local com um provedor externo de IA,
inspecione seu conteúdo. As solicitações de proposta do Seriema usam evidências
verificadas e excluem contatos, senhas, cookies e valores de formulário do navegador.
Veja [Propostas locais de IA](propostas.md) para a troca YAML independente de provedor.

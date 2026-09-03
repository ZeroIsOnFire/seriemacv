# Usar o Seriema com IA

[Voltar ao guia completo](index.md) · [English](../en/using-ai.md)

Um agente de IA trabalha com um projeto local do Seriema; ele não é dono do projeto
nem inventa fatos de carreira. Informe o local do projeto quando necessário e deixe o
resultado desejado explícito. Revise toda mudança canônica proposta e toda resposta
sensível de candidatura.

## Iniciar um projeto a partir de um currículo existente

Peça ao agente para criar o workspace local e depois anexe ou forneça o currículo:

```text
Crie um projeto Seriema em .\minha-carreira, em português, com o estilo clean.
Vou anexar meu currículo atual. Extraia somente os fatos presentes nele para uma
proposta de career.yml, liste as informações faltantes e aguarde minha revisão antes
de salvar qualquer coisa.
```

O agente pode transformar o currículo em uma proposta YAML revisável, mas não pode
inferir datas, empresas, habilidades, métricas ou credenciais que não estejam na
fonte. O `career.yml` só se torna canônico depois que você aceitar explicitamente os
fatos propostos.

## Verificar evidências antes de usá-las

As evidências sustentam os relatórios de compatibilidade, o texto personalizado e as
respostas de candidatura. Revise-as antes de importar vagas ou adaptar o currículo:

```text
Mostre minhas evidências de carreira e identifique as afirmações que precisam de
verificação. Marque como verificadas apenas as que eu confirmar; deixe pendentes as
afirmações inferidas ou sem suporte.
```

Somente evidências verificadas podem sustentar um match positivo ou uma afirmação
factual em currículo adaptado. Um item ausente ou não verificado continua sendo uma
lacuna, nunca uma habilidade presumida.

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

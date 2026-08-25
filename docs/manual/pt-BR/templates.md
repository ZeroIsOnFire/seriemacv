# Templates e ferramentas externas

[Voltar ao guia completo](index.md) · [English](../en/templates.md)

## Consultar o contrato de carreira

```powershell
seriemacv template show .\minha-carreira career
```

O comando imprime o `career.yml.example` do projeto. Projetos antigos sem exemplo
local recebem o template fictício interno. Essa operação é somente leitura e permite
que uma pessoa, script ou ferramenta de IA consulte o contrato YAML público exato.

Uma cópia versionada também está disponível em
[`examples/career.yml`](../../../examples/career.yml).

## Consultar os contratos de variante

```powershell
seriemacv template show .\minha-carreira variant
seriemacv template show .\minha-carreira variant-locale
```

O primeiro template descreve seleção, ordem, vínculo com vaga e estilo. O segundo
descreve textos parciais específicos de vaga aplicados sobre um arquivo de
`career.locales`; ele não contém traduções da aplicação mantidas em `i18n/`. As
cópias versionadas ficam em `examples/variant.yml` e
`examples/variant-locale.yml`.

## Fluxo seguro com uma ferramenta externa

1. Forneça à ferramenta a saída de `template show` e as informações de origem que
   você escolheu.
2. Peça um YAML compatível com o template e sem fatos inventados.
3. Salve a proposta separadamente e revise todos os campos.
4. Copie explicitamente apenas as informações aceitas para `career.yml`.
5. Rode `seriemacv career validate <projeto>`.
6. Gere um currículo somente depois que a validação passar.

Para uma variante, salve os arquivos aceitos em `resume/variants/<id>/`, execute
`seriemacv resume variants validate <projeto> --id <id>` e renderize com
`resume render --variant <id>`. Isso não altera nenhum fato canônico de carreira.

Ferramentas externas não recebem autorização implícita para alterar `career.yml`. O
seriemaCV não oferece atualmente um importador de currículos nem aplica propostas de
IA automaticamente.

## Situação do template de vagas

O domínio e o exemplo de vaga do repositório continuam preservados para trabalho
futuro, mas `template show ... job` e os comandos públicos `jobs` estão
intencionalmente indisponíveis enquanto a funcionalidade de vagas está pausada.

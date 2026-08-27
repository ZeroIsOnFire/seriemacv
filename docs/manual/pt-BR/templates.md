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

Projetos localizados possuem dois contratos estritos adicionais. Consulte
`career.locales/<locale>.yml.example` para os textos profissionais e
`i18n/<locale>.yml.example` para rótulos da aplicação, meses, níveis e formato de
data. Há cópias versionadas em `examples/career.locales.*.yml` e
`examples/i18n.*.yml`.

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

1. Forneça à ferramenta os templates relevantes e somente as informações de origem
   que você escolheu.
2. Indique qual destino ela pode editar: fatos canônicos, texto de carreira, i18n da
   aplicação ou uma variante identificada. Peça que não mova campos entre essas
   camadas nem invente fatos.
3. Salve a proposta separadamente e revise todos os campos.
4. Aplique fatos aceitos em `career.yml`, textos reutilizáveis em
   `career.locales/<locale>.yml` e traduções fixas em `i18n/<locale>.yml`.
5. Execute `seriemacv validate <projeto>`, `seriemacv career validate <projeto>` e
   `seriemacv career locale validate <projeto> --language <locale>`.
6. Gere um currículo somente depois que todas as validações aplicáveis passarem.

Para uma variante, salve os arquivos aceitos em `resume/variants/<id>/`, execute
`seriemacv resume variants validate <projeto> --id <id>` e renderize com
`resume render --variant <id>`. Isso não altera nenhum fato canônico de carreira.

Para uma troca estruturada e agnóstica de provedor com Codex, Claude Code ou outro
agente, use [Propostas locais de IA](propostas.md). O usuário continua revisando o
diff e selecionando cada item que pode ser persistido.

## Situação do template de vagas

Use `jobs import <projeto> <vaga.yml|vaga.json|vagas.zip>` para
adicionar uma vaga YAML/JSON ou todos os YAMLs de um arquivo ZIP. O importador valida
todos os documentos e colisões de ID antes de gravar; o texto-fonte original permanece
preservado em cada registro. Use `jobs list`, `jobs show` e
`jobs extract-requirements` para inspeção local, depois execute
`seriemacv match <projeto> <id-da-vaga>` para gerar um relatório YAML com evidências.

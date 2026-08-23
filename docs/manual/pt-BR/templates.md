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

## Fluxo seguro com uma ferramenta externa

1. Forneça à ferramenta a saída de `template show` e as informações de origem que
   você escolheu.
2. Peça um YAML compatível com o template e sem fatos inventados.
3. Salve a proposta separadamente e revise todos os campos.
4. Copie explicitamente apenas as informações aceitas para `career.yml`.
5. Rode `seriemacv career validate <projeto>`.
6. Gere um currículo somente depois que a validação passar.

Ferramentas externas não recebem autorização implícita para alterar `career.yml`.

## Importação local opcional com NuExtract

Instale o suporte a PDF somente quando necessário com `pip install .[import]`, rode
um `llama-server` multimodal local e configure seu endpoint de loopback em
`seriemacv.yml`:

```yaml
nuextract:
  endpoint: http://127.0.0.1:8080
  model: nuextract
  multimodal: true
```

Crie e revise a proposta antes de aplicá-la:

```powershell
seriemacv career import propose .\minha-carreira .\curriculo.pdf --language pt-BR
seriemacv career import list .\minha-carreira
seriemacv career import show .\minha-carreira import-20260101000000
seriemacv career import apply .\minha-carreira import-20260101000000
```

As propostas ficam em `proposals/`, com metadados e excertos da origem. `apply` é
explícito, atômico e recusa sobrescrever dados ou textos de locale existentes. Páginas
PDF sem texto selecionável exigem endpoint multimodal local; o seriemaCV não envia a
origem a serviços hospedados.

## Situação do template de vagas

O domínio e o exemplo de vaga do repositório continuam preservados para trabalho
futuro, mas `template show ... job` e os comandos públicos `jobs` estão
intencionalmente indisponíveis enquanto a funcionalidade de vagas está pausada.

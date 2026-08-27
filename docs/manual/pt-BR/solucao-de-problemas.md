# Solução de problemas

[Voltar ao guia completo](index.md) · [English](../en/troubleshooting.md)

## `seriemacv` não é reconhecido

Instale a cópia local e confirme que o diretório de scripts está no `PATH`:

```powershell
python -m pip install -e .
python -m pip show seriemacv
```

## O Windows abre o alias Python da Microsoft Store

Use o caminho completo do Python 3.11+, um `py -3.12` funcional ou desative o alias
de execução conflitante nas configurações do Windows.

## A validação do projeto falha

```powershell
seriemacv validate .\minha-carreira
```

Restaure especificamente o diretório ou artefato indicado. Não recrie o arquivo
SQLite como texto. Se o projeto for anterior ao layout atual, a validação reconhece
automaticamente o contrato legado suportado.

## A validação da carreira falha

```powershell
seriemacv career validate .\minha-carreira
```

Leia o diagnóstico como `arquivo:linha:coluna: caminho.do.campo: mensagem`. Causas
comuns são nome/cargo/e-mail vazios, indentação inválida, campo desconhecido, IDs
duplicados, data inválida ou evidência apontando para uma experiência inexistente.

Erros técnicos ocultam credenciais e valores pessoais, incluindo tokens, senhas,
cookies, e-mails, telefones e campos sensíveis de candidatura. O nome do campo
permanece visível para que o problema ainda possa ser localizado.

## Compartilhar um bundle de diagnóstico com segurança

```powershell
seriemacv diagnostics bundle .\minha-carreira --output .\diagnosticos.zip
```

O ZIP contém somente `diagnostics.json`, com a versão do seriemaCV e a validação
redigida da estrutura do projeto. Ele exclui YAML de carreira, registros de vagas e
candidaturas, exportações, índices SQLite, perfis de navegador e arquivos de pedido
ou resposta de IA. O seriemaCV não coleta nem envia telemetria.

Datas devem usar `YYYY-MM`, como `2024-01`. Registros atuais omitem `end_date`.

## O PDF informa que o Chromium está ausente

```powershell
python -m playwright install chromium
```

Execute com o mesmo ambiente Python em que o seriemaCV foi instalado.

## Outro estilo substituiu meu currículo

As saídas são deliberadamente fixas em `exports/resume.<ext>`. Gerar um segundo
estilo no mesmo formato substitui atomicamente o artefato anterior. Copie ou renomeie
o arquivo antes de gerar outro estilo quando precisar manter as duas versões.

## O Markdown não se parece com o PDF ou DOCX

Markdown não representa de forma confiável geometria de página, fontes, cores ou
barras laterais. Ele preserva o conteúdo e varia apenas elementos estruturais como
títulos, separadores, densidade e agrupamento.

## O `sidebar` ou `timeline` foi interpretado incorretamente por um ATS

Isso é esperado: ambas as famílias são explicitamente não ATS-safe. Gere `clean`,
`classic`, `modern`, `compact`, `clean-executive` ou uma de suas variantes `-alt`
para análise automatizada.

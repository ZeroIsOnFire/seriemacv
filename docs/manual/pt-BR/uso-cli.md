# Usar o Seriema CLI

[Voltar ao guia completo](index.md) · [English](../en/using-cli.md)

Use a CLI quando preferir operar diretamente o mesmo projeto local. Os comandos
abaixo são os exemplos iniciais existentes, reunidos em um único lugar.

## Criar e validar um projeto de carreira

```powershell
python -m pip install -e .
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style clean
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id cargo-atual --company "Empresa" --start-date 2024-01
# Adicione o cargo do perfil e o texto de cargo-atual em career.locales/pt-BR.yml.
seriemacv validate .\minha-carreira
seriemacv career validate .\minha-carreira
seriemacv career locale validate .\minha-carreira --language pt-BR
```

## Gerar um currículo

```powershell
seriemacv resume styles
seriemacv resume render .\minha-carreira --format markdown
seriemacv resume render .\minha-carreira --language en --format pdf --format docx
```

## Trabalhar com vaga e candidatura

```powershell
seriemacv jobs import .\minha-carreira .\vaga.yml
seriemacv match .\minha-carreira engenheiro-plataforma
seriemacv applications create .\minha-carreira --id candidatura-plataforma --job-id engenheiro-plataforma --url https://example.invalid/apply
seriemacv applications prepare .\minha-carreira candidatura-plataforma --interactive
```

O comando de candidatura abre um perfil isolado no navegador para revisão; ele não
envia o formulário. Veja [Vagas e match](vagas-e-match.md) e [Candidaturas
assistidas](candidaturas.md) para a referência completa de comandos.

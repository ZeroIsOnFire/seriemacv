# Instalação

[Voltar ao guia completo](index.md) · [English](../en/installation.md)

## Requisitos

- Python 3.11 ou mais recente.
- Uma cópia local deste repositório.
- Chromium do Playwright apenas para gerar arquivos PDF.

A geração de DOCX usa `python-docx` e não exige Microsoft Word. Markdown e HTML não
precisam de navegador.

## Instalar a CLI

Na raiz do repositório, instale o projeto em modo editável:

```powershell
python -m pip install -e .
```

Para desenvolvimento e verificações locais, instale também as ferramentas opcionais:

```powershell
python -m pip install -e ".[dev]"
```

Confirme que o comando está disponível:

```powershell
seriemacv --help
seriemacv resume styles
```

## Habilitar geração de PDF

O Playwright é instalado como dependência Python, mas o Chromium é separado:

```powershell
python -m playwright install chromium
```

O navegador é usado localmente. Depois que ele estiver instalado, a geração do
currículo não precisa de acesso à rede.

## Resolução do Python no Windows

Se o Windows selecionar o alias `python.exe` da Microsoft Store em vez do interpretador
instalado, use o caminho completo do Python 3.11+ ou corrija os aliases de execução de
aplicativos. O launcher também pode ser usado quando reconhecer a instalação:

```powershell
py -3.12 -m pip install -e .
```

Continue em [Projetos e configuração](projetos.md).

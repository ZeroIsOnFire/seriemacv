# seriemacv

[Read in English](README.md)

<img src="mascot.png" width="140" alt="Mascote do seriemaCV">

Workspace local-first para manter dados canônicos de carreira em YAML e gerar
currículos editáveis ou prontos para publicação.

O seriemaCV é atualmente uma interface de linha de comando pensada primeiro para
agentes de IA e automação local. Seu objetivo inicial é ajudar agentes a transformar
experiências profissionais verificadas em YAML estruturado e gerar currículos
consistentes sem controlar os dados ou as decisões do usuário. Pessoas também podem
usar todos os comandos diretamente. Uma futura GUI independente poderá oferecer os
mesmos fluxos principais sem depender de um agente.

## Documentação

Consulte o [guia completo de uso](docs/manual/pt-BR/index.md) para instalação,
configuração de projetos, todos os comandos do Career Builder, formatos de currículo,
templates e solução de problemas.

## Seriema com IA

Use um agente de IA com o caminho do projeto local e um pedido claro. Por exemplo:

```text
Crie um projeto Seriema em .\minha-carreira. Vou anexar meu currículo; extraia apenas
os fatos presentes nele para uma proposta de career.yml e aguarde minha revisão antes de salvar.
```

```text
Importe esta vaga: https://careers.example.com/jobs/123.
Valide-a, analise a compatibilidade com a minha carreira e pesquise a pretensão salarial.
```

```text
Vamos nos inscrever em platform-engineer. Minha pretensão é R$ 20.000.
Primeiro confirme a análise de compatibilidade, prepare o currículo e as respostas
corretos e abra a candidatura no Playwright para eu revisar.
```

O agente deve fundamentar afirmações em evidências verificadas, pedir revisão antes
de usar respostas sensíveis e nunca enviar sem autorização explícita. Veja [Usar o
Seriema com IA](docs/manual/pt-BR/uso-com-ia.md) para exemplos completos.

## Seriema CLI

```powershell
seriemacv init .\minha-carreira --name "Minha carreira" --language pt-BR --style modern
seriemacv career set-profile .\minha-carreira --name "Seu Nome" --email voce@example.com
seriemacv career add-experience .\minha-carreira --id empresa-atual --company "Empresa" --start-date 2024-01
seriemacv career validate .\minha-carreira
```

Cada projeto inclui `career.yml` vazio e exemplos fictícios em
`career.yml.example` e `seriemacv.yml.example`. `career.yml` é sempre a fonte
canônica dos fatos. O texto profissional por idioma fica em
`career.locales/<locale>.yml`; rótulos, meses, níveis e formato de data configuráveis
do seriemaCV ficam em `i18n/<locale>.yml`.
Textos específicos de vaga ficam separados em
`resume/variants/<id>/locales/<locale>.yml` e herdam o conteúdo omitido do locale
base de carreira.

A área de vagas suporta importação estruturada local, relatórios determinísticos de
match, propostas de tailoring revisáveis, candidaturas locais assistidas e Studio local somente leitura.

## Gerar currículo

```powershell
seriemacv resume styles
seriemacv resume render .\minha-carreira --format markdown
seriemacv resume render .\minha-carreira --language en --format pdf --format docx
seriemacv resume render .\minha-carreira --format html --style classic
seriemacv resume render .\minha-carreira --format pdf --style modern
seriemacv resume render .\minha-carreira --format docx --style compact
seriemacv resume variants list .\minha-carreira
seriemacv resume variants validate .\minha-carreira
seriemacv resume render .\minha-carreira --variant vaga-plataforma --format pdf
```

`resume_style` em `seriemacv.yml` define o padrão. `--style` o substitui em uma
renderização sem alterar o projeto. Cada formato substitui atomicamente seu artefato
fixo em `exports/resume.*`. PDF requer Chromium local:
`python -m playwright install chromium`.

PDFs canônicos usam cache por conteúdo. Se dados localizados, idioma, estilo, cor e
assets continuarem iguais, o comando reutiliza `exports/resume.<locale>.pdf` sem
abrir o Chromium. Uma alteração em qualquer entrada invalida o cache. Variantes de
vaga são sempre renderizadas separadamente.

`resume_color` define a cor RGB dos estilos configuráveis `modern`,
`clean-executive`, `timeline`, `sidebar`, `split-header`, `contact-band`, `left-rail`
e `detail-sidebar` (incluindo `-alt`); o padrão é o verde do mascote `#647D74`.

Os estilos Markdown variam hierarquia, separadores e densidade; Markdown não
representa fontes, cores ou colunas. DOCX permanece editável. As famílias `sidebar`,
`timeline`, `split-header`, `contact-band`, `left-rail` e `detail-sidebar` usam layouts
visuais não lineares e são explicitamente experimentais e não ATS-safe; as cinco
famílias restantes permanecem lineares.

Cada família possui um estilo padrão com linhas divisórias nas seções e um estilo
`-alt` sem elas. `classic` e `classic-alt` nunca exibem linha abaixo do cabeçalho
centralizado; apenas os divisores dos títulos de seção variam.

## Layouts compatíveis

As famílias `split-header`, `contact-band`, `left-rail` e `detail-sidebar` são
interpretações visuais originais. Elas usam somente os dados
canônicos disponíveis e não criam foto, certificados, prêmios ou interesses.

Veja previews, observações sobre ATS, orientação de escolha e exemplos para download
na [galeria de layouts compatíveis](docs/styles.pt-BR.md). Ela inclui a família
formal `clean-executive` e a família visual `timeline`, sem foto.

## Templates e competências estruturadas

Ferramentas externas podem consultar o contrato fictício de carreira atual com:

```powershell
seriemacv template show .\minha-carreira career
seriemacv template show .\minha-carreira variant
seriemacv template show .\minha-carreira variant-locale
```

```yaml
skills:
  - id: ruby
    name: Ruby
    category: Programação
    level: advanced
    core: true
```

Competências são agrupadas por categoria e as `core` recebem destaque. Códigos de
nível estáveis são localizados durante a renderização. O perfil também aceita URLs
HTTP(S) explícitas em `linkedin` e `portfolio`.

## Verificação local

```powershell
python scripts/check_quality.py
```

Instale as ferramentas de desenvolvimento com `python -m pip install -e ".[dev]"`.
O gate compila o código, verifica lint e formatação, analisa a baseline de módulos
tipados e executa toda a suíte unitária. O CI também roda `python -m pip check` numa
matriz limpa com Python 3.11 e 3.12.

## Licença

O seriemaCV é licenciado somente sob a
[GNU Affero General Public License v3.0](LICENSE).
Copyright © 2026 Eli Fachin Junior.

Os dados de carreira fornecidos pelos usuários permanecem pertencendo aos seus
respectivos autores. Consulte a licença para os termos aplicáveis ao código-fonte e
aos recursos incluídos no seriemaCV.

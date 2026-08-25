# Templates and external tools

[Back to the complete guide](index.md) · [Português](../pt-BR/templates.md)

## Read the career contract

```powershell
seriemacv template show .\my-career career
```

This prints the project's `career.yml.example`. Older projects without a local
example receive the built-in fictional template. The command is read-only and lets a
person, script, or AI tool inspect the exact public YAML contract.

A repository copy is also available at
[`examples/career.yml`](../../../examples/career.yml).

Localized projects have two additional strict contracts. Inspect
`career.locales/<locale>.yml.example` for professional wording and
`i18n/<locale>.yml.example` for application labels, months, levels, and date format.
Repository copies are available under `examples/career.locales.*.yml` and
`examples/i18n.*.yml`.

## Read the resume variant contracts

```powershell
seriemacv template show .\my-career variant
seriemacv template show .\my-career variant-locale
```

The first template describes selection, order, job linkage, and style. The second
describes partial job-specific wording layered over a `career.locales` file; it does
not contain application translations from `i18n/`.
Repository copies live in `examples/variant.yml` and `examples/variant-locale.yml`.

## Safe workflow with an external tool

1. Give the tool the relevant templates and only the source information you chose.
2. State which target it may edit: canonical facts, career wording, app i18n, or a
   named variant. Ask it not to move fields between those layers or invent facts.
3. Save the proposal separately and review every field.
4. Apply accepted facts to `career.yml`, reusable wording to
   `career.locales/<locale>.yml`, and fixed translations to `i18n/<locale>.yml`.
5. Run `seriemacv validate <project>`, `seriemacv career validate <project>`, and
   `seriemacv career locale validate <project> --language <locale>`.
6. Render a resume only after every applicable validation succeeds.

For a variant, save the accepted files under `resume/variants/<id>/`, run
`seriemacv resume variants validate <project> --id <id>`, and render with
`resume render --variant <id>`. This changes no canonical career facts.

An AI tool may edit these YAML files directly when the user explicitly authorizes
that project change, but seriemaCV does not currently provide an importer or
automatically apply AI proposals. The user must still review the diff and validation
result.

## Jobs template status

The job domain and repository example remain preserved for future work, but
`template show ... job` and public `jobs` commands are intentionally unavailable
while the jobs feature is paused.

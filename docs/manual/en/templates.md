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

1. Give the tool the output of `template show` and the source information you chose.
2. Ask it to produce YAML matching the template without inventing facts.
3. Save the proposal separately and review every field.
4. Copy accepted information into `career.yml` explicitly.
5. Run `seriemacv career validate <project>`.
6. Render a resume only after validation succeeds.

For a variant, save the accepted files under `resume/variants/<id>/`, run
`seriemacv resume variants validate <project> --id <id>`, and render with
`resume render --variant <id>`. This changes no canonical career facts.

External tools do not receive implicit permission to modify `career.yml`. seriemaCV
does not currently provide a resume importer or automatically apply AI proposals.

## Jobs template status

The job domain and repository example remain preserved for future work, but
`template show ... job` and public `jobs` commands are intentionally unavailable
while the jobs feature is paused.

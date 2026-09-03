# Using Seriema CLI

[Back to the complete guide](index.md) · [Português](../pt-BR/uso-cli.md)

Use the CLI when you prefer to operate the same local project directly. The commands
below are the existing starter examples, collected in one place.

## Create and validate a career project

```powershell
python -m pip install -e .
seriemacv init .\my-career --name "My career" --language en --style clean
seriemacv career set-profile .\my-career --name "Your Name" --email you@example.com
seriemacv career add-experience .\my-career --id current-role --company "Company" --start-date 2024-01
# Add the profile title and current-role wording to career.locales/en.yml.
seriemacv validate .\my-career
seriemacv career validate .\my-career
seriemacv career locale validate .\my-career --language en
```

## Render a resume

```powershell
seriemacv resume styles
seriemacv resume render .\my-career --format markdown
seriemacv resume render .\my-career --language en --format pdf --format docx
```

## Work with a job and application

```powershell
seriemacv jobs import .\my-career .\role.yml
seriemacv match .\my-career platform-engineer
seriemacv applications create .\my-career --id platform-application --job-id platform-engineer --url https://example.invalid/apply
seriemacv applications prepare .\my-career platform-application --interactive
```

The application command opens an isolated browser profile for review; it does not
submit the form. See [Jobs and match](jobs-and-match.md) and [Assisted
applications](applications.md) for the full command reference.

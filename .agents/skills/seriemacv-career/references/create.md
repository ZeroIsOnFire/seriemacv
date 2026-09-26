# Create a career from an interview

If the project does not exist, first ask only for the destination, project name,
primary resume language, and preferred built-in style, then initialize it. Use the
initialized schema and locales; do not create a separate “resume” record.

Collect and checkpoint topics in this order unless the user already supplied them:

1. identity, contact links, target title, location, and languages;
2. one work experience at a time, including dates, employment context,
   responsibilities, achievements, scope, and user-known outcomes;
3. education and credentials;
4. skills, with level or priority only when the user can assess them;
5. evidence supporting distinct professional claims;
6. professional summary, written last from confirmed facts;
7. reusable answers or stories only when the user wants them.

Do not turn every answer into a resume bullet. Consolidate related details, retain
the user's meaning, and keep evidence separate from display text. Generate stable
kebab-case IDs and localized wording for every configured career locale; ask the
user to review translations without re-asking the underlying fact.

Save after each confirmed profile, experience, education, or skills/evidence block.
If the session ends, the next run should inspect the existing YAML and resume at the
first incomplete topic rather than restarting the interview.

# Gerald Roadmap

## Completed

- Platform scaffold: `/root/projects/gerald/` with `docs/`, `modules/`, `shared/`, `data/`
- Module placeholders: `fitness`, `career`, `health`, `home`, `research`
- Platform docs: `GERALD_CONSTITUTION.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`, `MIGRATION_PLAN.md`
- Fitness migration plan documented and awaiting approval

## In Progress

- Awaiting approval to migrate the existing fitness module into `/root/projects/gerald/modules/fitness/`

## Next

1. Fitness module migration and path refactor
2. Investigate whether fitness cron wrapper should stay as a shell script or shift to a shared Python runner
3. Define minimal contracts for `career` and `home` modules
4. Define shared transport interface if multiple modules use similar Telegram patterns

## Out of Scope

- Multi-user support
- Cloud sync
- Marketplace / plugin distribution

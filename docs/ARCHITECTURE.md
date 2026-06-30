# Gerald Architecture

This is the platform-level architecture overview. Module-specific architectural detail lives in the respective module docs.

## 1. File Structure

```
/root/projects/gerald/
├── docs/
│   ├── GERALD_CONSTITUTION.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── CHANGELOG.md
│   └── MIGRATION_PLAN.md
├── modules/
│   ├── fitness/
│   ├── career/
│   ├── health/
│   ├── home/
│   └── research/
├── shared/
├── data/
```

## 2. Module Isolation Model

- Each module lives under `/root/projects/gerald/modules/<module>/`
- A module may own its own `scripts/`, `logs/`, `backups/`, and local state files.
- No module may import or assume another module at interpreter startup.
- Shared libraries, if ever needed, must be placed in `/root/projects/gerald/shared/` and remain top-level directory only; no cross-module symlinks.

## 3. Delivery Model

- Each module defines its own delivery wrapper and schedule.
- Platform has no central scheduler.
- Cron prompts must be minimal and module-local; they must not carry platform context beyond what the module requires.

## 4. Data Model

- Module-local data only; no shared JSON by default.
- Sensitive state must use `0600` permissions.
- Schemas and migrations are versioned per module.

## 5. Integration Model

- Inbound and outbound messaging is module-defined.
- The platform does not enforce HTTP/gRPC/etc.; first-class wire format is shell/CLI + optional file queue.

## 6. Migrations

- Migration plans must be reviewed and approved before moving working code.
- Retain a `.bak` path during cutover.
- Freeze scheduling during relocation.

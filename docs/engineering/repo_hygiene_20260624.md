# Repo Hygiene Audit — 2026-06-24

## Scope
- Production repo: /opt/kanban-react
- Base branch: backup/prod-snapshot-20260623-232316
- Hygiene branch: engineering/repo-hygiene-20260624
- Master policy: do not overwrite master yet

## Current findings
- GitLab master is not current production state.
- Current production snapshot branch exists on GitLab: backup/prod-snapshot-20260623-232316.
- Source tree is mixed with build artifacts, runtime DB/log files, user uploads, and historical backups.
- Tracked generated/runtime candidate paths: 50703
- Current untracked paths: 9
- Current non-untracked status entries: 5

## Actions in this branch
- Expanded .gitignore to block new generated/runtime artifacts:
  - Python caches: __pycache__, *.pyc, pytest/mypy/ruff cache
  - Frontend dependencies/build: node_modules, dist, build, .vite
  - Historical dist/backups: dist.prev_*, backend.backup.*, frontend.backup.*, backups
  - Runtime logs/pids: *.log, logs, *.pid
  - Local DB/runtime state: *.db, *.sqlite, backend/data/*.json(l), macmini_sync_data.json
  - Upload/output dirs: uploads, frontend/public/uploads, Files/output
  - Temp patch dirs: tmp, remote_kanban_patches_*

## Important limitation
.gitignore only prevents new files from being added. It does not remove files already tracked by Git.
A later cleanup branch should use git rm --cached for generated/runtime files after confirming no source files are lost.

## Recommended next steps before merging to master
1. Keep backup/prod-snapshot-20260623-232316 as immutable production safety branch.
2. Create a clean source branch from this hygiene branch.
3. Review tracked generated/runtime candidates in batches.
4. Use git rm --cached only for confirmed generated/runtime files.
5. Run build/test and compare deployed UI/API before merging.
6. Merge clean source branch to GitLab master only after verification.

# Master Source Refresh Runbook - 2026-06-24

## Scope
- MR: !1
- Source: release/master-source-only-20260624
- Target: master
- Source HEAD: a137d963 (a137d9635ce911b0f2c1cbf24bed6ad82fa7551d)
- Target HEAD before merge: 7c18c250 (7c18c2506bd361adab31593fcc3101a620ca2ea7)
- Backup branch: backup/master-before-source-refresh-20260624_230934
- Backup tag: backup-master-before-source-refresh-20260624_230934

## Pre-merge evidence
- Dry-run merge into master: clean
- Post-merge backend py_compile in temporary worktree: pass
- Post-merge frontend build with independent npm install/ci: pass
- Production frontend build sanity: pass
- Tracked generated/runtime paths in source candidate: 0
- Services active+enabled: nginx, mysql, kanban-api, kanban-backend, kanban-bs, email-api, sds-crewai, kanban-crew-api
- Public endpoints verified 200: /, /api/health, /api/tasks, /api/projects, /api/actors, /api/actor/modes, /api/llm/global-context, /api/crews/health, /api/crews/status, Socket.IO polling

## Manual merge procedure
1. Open GitLab MR !1: http://47.93.184.128/root/kanban/-/merge_requests/1
2. Confirm source branch release/master-source-only-20260624 and target master.
3. Confirm verification evidence above.
4. Click Merge manually.
5. On server, fetch and verify master HEAD.

## Post-merge verification
```bash
git fetch gitlab master
python3 -m py_compile backend/crew_api.py backend/routes/sds_crew/framework.py backend/routes/actor_api.py backend/routes/modes_config.py backend/scripts/update_llm_context.py
cd frontend && npm run build
for u in / /api/health /api/tasks /api/projects /api/actors /api/actor/modes /api/llm/global-context /api/crews/health /api/crews/status '/socket.io/?EIO=4&transport=polling'; do
  curl -k -L -s -o /dev/null -w "%{http_code} $u\n" "https://kanbanyun.com$u"
done
```

## Rollback if needed
Do not delete production runtime/upload/output files. If source rollback is needed:
```bash
git fetch gitlab backup/master-before-source-refresh-20260624_230934 master
git checkout master
git reset --hard gitlab/backup/master-before-source-refresh-20260624_230934
git push --force-with-lease gitlab master
```

## Notes
The large deletion set is expected: old master tracked runtime/generated/backup/static output files. The MR removes these from Git tracking only.

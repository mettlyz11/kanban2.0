# Tracked Generated/Runtime Candidate Manifest — 2026-06-24
This is a classification manifest only. It does **not** delete files.

## Counts by category
| Category | Count | Suggested action |
|---|---:|---|
| frontend_build | 54422 | review, then git rm --cached in cleanup branch |
| historical_backups | 3289 | review, then git rm --cached in cleanup branch |
| local_db | 73 | review, then git rm --cached in cleanup branch |
| logs_pid | 99 | review, then git rm --cached in cleanup branch |
| python_cache | 44 | review, then git rm --cached in cleanup branch |
| runtime_data_uploads | 3394 | review, then git rm --cached in cleanup branch |
| secrets_env | 10 | urgent review; remove from Git history strategy needed if real secrets |
| temp_patch_work | 2 | review, then git rm --cached in cleanup branch |
| **TOTAL** | **61333** |  |

## Sample paths

### frontend_build
- `backend.backup.20260315_073954/build/_redirects`
- `backend.backup.20260315_073954/build/assets/index-By0kmdCk.js`
- `backend.backup.20260315_073954/build/assets/index-C1r-1_NX.css`
- `backend.backup.20260315_073954/build/assets/index-C3pOHfGg.css`
- `backend.backup.20260315_073954/build/assets/index-C7G_Cb0B.js`
- `backend.backup.20260315_073954/build/assets/index-CSda_P2V.js`
- `backend.backup.20260315_073954/build/assets/index-CXORH_G4.js`
- `backend.backup.20260315_073954/build/assets/index-DFOP4PDL.js`
- `backend.backup.20260315_073954/build/assets/index-DI8ydzUf.js`
- `backend.backup.20260315_073954/build/assets/index-Du5gotTb.css`
- `backend.backup.20260315_073954/build/assets/index-zbcqdbiR.css`
- `backend.backup.20260315_073954/build/assets/main-DyEqMEa9.css`
- `backend.backup.20260315_073954/build/assets/main-aB5XIj-t.js`
- `backend.backup.20260315_073954/build/assets/main-aB5XIj-t.js.map`
- `backend.backup.20260315_073954/build/assets/ui-DNAc6bOc.js`
- `backend.backup.20260315_073954/build/assets/ui-DNAc6bOc.js.map`
- `backend.backup.20260315_073954/build/assets/vendor-DqvBY7vd.js`
- `backend.backup.20260315_073954/build/assets/vendor-DqvBY7vd.js.map`
- `backend.backup.20260315_073954/build/goal-project-task`
- `backend.backup.20260315_073954/build/goal-project-task.html`
- `backend.backup.20260315_073954/build/hierarchy.html`
- `backend.backup.20260315_073954/build/index.html`
- `backend.backup.20260315_073954/build/vite.svg`
- `backend.backup.20260330_2345/build/_redirects`
- `backend.backup.20260330_2345/build/assets/index-By0kmdCk.js`
- `backend.backup.20260330_2345/build/assets/index-C1r-1_NX.css`
- `backend.backup.20260330_2345/build/assets/index-C3pOHfGg.css`
- `backend.backup.20260330_2345/build/assets/index-C7G_Cb0B.js`
- `backend.backup.20260330_2345/build/assets/index-CSda_P2V.js`
- `backend.backup.20260330_2345/build/assets/index-CXORH_G4.js`
- ... +54392 more; full list in `tracked_generated_candidates_20260624.tsv`

### historical_backups
- `Files/sds1/core/project_gap_analyzer.py.bak`
- `Files/sds1/templates/subagent_executor.py.bak`
- `backend.backup.20260315_073954/AUDIT_SYSTEM_README.md`
- `backend.backup.20260315_073954/AUDIT_UPDATE_COMPLETE.md`
- `backend.backup.20260315_073954/LONG_THINKING.md`
- `backend.backup.20260315_073954/PERCEPTION_README.md`
- `backend.backup.20260315_073954/VERSION`
- `backend.backup.20260315_073954/app.py`
- `backend.backup.20260315_073954/app.py.backup.20260312_212026`
- `backend.backup.20260315_073954/app.py.backup.20260314_132745`
- `backend.backup.20260315_073954/app.py.backup.20260315_012156`
- `backend.backup.20260315_073954/app.py.broken`
- `backend.backup.20260315_073954/audit_routes.py`
- `backend.backup.20260315_073954/build.backup_20260310_182650/_redirects`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-By0kmdCk.js`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-C1r-1_NX.css`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-C3pOHfGg.css`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-CSda_P2V.js`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-CXORH_G4.js`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-DFOP4PDL.js`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-DI8ydzUf.js`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-Du5gotTb.css`
- `backend.backup.20260315_073954/build.backup_20260310_182650/assets/index-zbcqdbiR.css`
- `backend.backup.20260315_073954/build.backup_20260310_182650/index.html`
- `backend.backup.20260315_073954/build.backup_20260310_182650/vite.svg`
- `backend.backup.20260315_073954/caldav_sync.py`
- `backend.backup.20260315_073954/calendar_schema.sql`
- `backend.backup.20260315_073954/check_tables.py`
- `backend.backup.20260315_073954/cron_api.py`
- `backend.backup.20260315_073954/database_config.py`
- ... +3259 more; full list in `tracked_generated_candidates_20260624.tsv`

### local_db
- `backend.backup.20260315_073954/app.py.sqlite.backup`
- `backend.backup.20260315_073954/kanban_react.db`
- `backend.backup.20260315_073954/kanban_v5.db`
- `backend.backup.20260315_073954/kanban_v5.db.backup.20260312_185411`
- `backend.backup.20260315_073954/kanban_v5.db.backup.20260312_190314`
- `backend.backup.20260315_073954/kanban_v5.db.backup.20260312_212026`
- `backend.backup.20260315_073954/kanban_v5.db.backup.20260314_095821`
- `backend.backup.20260330_2345/app.py.sqlite.backup`
- `backend.backup.20260330_2345/kanban_v5.db`
- `backend.backup.20260330_2345/kanban_v5.db.backup.20260312_185411`
- `backend.backup.20260330_2345/kanban_v5.db.backup.20260312_190314`
- `backend.backup.20260330_2345/kanban_v5.db.backup.20260312_212026`
- `backend.backup.20260330_2345/kanban_v5.db.backup.20260314_095821`
- `backend.backup.20260330_2345/kanban_v5.db.backup.20260318_091526`
- `backend.backup.20260330_2345/kanban_v5.db.backup_full`
- `backend.backup.20260330_2345/monitoring.db`
- `backend.backup.20260330_2345/task_worker.py.sqlite.backup`
- `backend/app.py.sqlite.backup`
- `backend/dist/output/task-2078/data/health_data.db`
- `backend/kanban_v5.db`
- `backend/kanban_v5.db.backup.20260312_185411`
- `backend/kanban_v5.db.backup.20260312_190314`
- `backend/kanban_v5.db.backup.20260312_212026`
- `backend/kanban_v5.db.backup.20260314_095821`
- `backend/kanban_v5.db.backup.20260318_091526`
- `backend/kanban_v5.db.backup_full`
- `backend/monitoring.db`
- `backend/task_worker.py.sqlite.backup`
- `backend_old/kanban_v5.db`
- `backend_old/kanban_v5.db.backup`
- ... +43 more; full list in `tracked_generated_candidates_20260624.tsv`

### logs_pid
- `backend.backup.20260315_073954/flask.log`
- `backend.backup.20260315_073954/server.log`
- `backend.backup.20260330_2345/access.log`
- `backend.backup.20260330_2345/error.log`
- `backend.backup.20260330_2345/flask.log`
- `backend.backup.20260330_2345/gunicorn.log`
- `backend.backup.20260330_2345/logs/task_worker_20260311.log`
- `backend.backup.20260330_2345/logs/task_worker_20260318.log`
- `backend.backup.20260330_2345/logs/task_worker_sim_20260311.log`
- `backend.backup.20260330_2345/perception_agent.log`
- `backend.backup.20260330_2345/perception_agent.pid`
- `backend.backup.20260330_2345/server.log`
- `backend.backup.20260330_2345/startup.log`
- `backend/access.log`
- `backend/app.log`
- `backend/dist/output/task-1570/sds_blocked_actions.log`
- `backend/dist/output/task-1570/sds_nohup.log`
- `backend/dist/output/task-1570/sds_runtime.log`
- `backend/dist/output/task-1570/sds_safety_audit.log`
- `backend/dist/output/task-1570/sds_v44_runtime.log`
- `backend/error.log`
- `backend/flask.log`
- `backend/gunicorn.log`
- `backend/gunicorn.pid`
- `backend/logs/backend.log`
- `backend/logs/gunicorn.log`
- `backend/logs/task_worker_20260311.log`
- `backend/logs/task_worker_20260318.log`
- `backend/logs/task_worker_sim_20260311.log`
- `backend/perception_agent.log`
- ... +69 more; full list in `tracked_generated_candidates_20260624.tsv`

### python_cache
- `backend.backup.20260330_2345/__pycache__/app.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/auth_manager.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/auth_routes.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/database_config.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/file_indexer.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/long_thinking.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/p049_monitoring.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/perception_agent.cpython-312.pyc`
- `backend.backup.20260330_2345/__pycache__/socket_events.cpython-312.pyc`
- `backend/__pycache__/admin_models.cpython-312.pyc`
- `backend/__pycache__/admin_routes.cpython-312.pyc`
- `backend/__pycache__/admin_services.cpython-312.pyc`
- `backend/__pycache__/app.cpython-312.pyc`
- `backend/__pycache__/auth_manager.cpython-312.pyc`
- `backend/__pycache__/auth_routes.cpython-312.pyc`
- `backend/__pycache__/company_tabs_routes.cpython-312.pyc`
- `backend/__pycache__/database_config.cpython-312.pyc`
- `backend/__pycache__/db_config.cpython-312.pyc`
- `backend/__pycache__/file_indexer.cpython-312.pyc`
- `backend/__pycache__/long_thinking.cpython-312.pyc`
- `backend/__pycache__/p049_monitoring.cpython-312.pyc`
- `backend/__pycache__/perception_agent.cpython-312.pyc`
- `backend/__pycache__/person_company_routes.cpython-312.pyc`
- `backend/__pycache__/person_tabs_routes.cpython-312.pyc`
- `backend/__pycache__/strategic_map_routes.cpython-312.pyc`
- `backend/routes/sds_crew/__pycache__/__init__.cpython-312.pyc`
- `backend/routes/sds_crew/__pycache__/agents.cpython-312.pyc`
- `backend/routes/sds_crew/__pycache__/framework.cpython-312.pyc`
- `backend/routes/sds_crew/__pycache__/scheduler.cpython-312.pyc`
- `backend/src/websocket/__pycache__/__init__.cpython-312.pyc`
- ... +14 more; full list in `tracked_generated_candidates_20260624.tsv`

### runtime_data_uploads
- `backend/Files/output/task-1000068/validate_json_schema.py`
- `backend/Files/output/task-1000068/validation_result.md`
- `"backend/Files/output/task-1000076/\344\273\243\347\240\201\346\240\274\345\274\217\345\214\226\346\240\207\345\207\206_v3.md"`
- `"backend/Files/output/task-1000076/\346\240\274\345\274\217\345\214\226\351\205\215\347\275\256\346\226\207\344\273\266\347\244\272\344\276\213.md"`
- `"backend/Files/output/task-1000078/\351\205\215\347\275\256\346\226\207\344\273\266\347\211\210\346\234\254\345\217\267\346\230\240\345\260\204\344\270\216\350\247\204\350\214\203.md"`
- `"backend/Files/output/task-1000114/V4_\350\260\203\345\272\246\351\230\262\346\232\264\350\265\260\346\234\272\345\210\266\350\257\264\346\230\216.md"`
- `"backend/Files/output/task-1000121/v4_\345\216\206\345\217\262\346\211\247\350\241\214\345\210\206\346\236\220\346\212\245\345\221\212.md"`
- `backend/Files/output/task-1000122/deployment_and_operations_guide.md`
- `backend/Files/output/task-1000122/pid_lock.sh.py`
- `backend/Files/output/task-1000135/backup_guide.md`
- `backend/Files/output/task-1000135/backup_manifest.md`
- `backend/Files/output/task-1000141/execution_log_template_spec.md`
- `"backend/Files/output/task-1000147/SDS\350\277\220\350\241\214\346\227\266\351\227\264\347\272\277_v7_16.md"`
- `backend/Files/output/task-1000150/resource_quota_config.md`
- `backend/Files/output/task-1000150/resource_quota_design.md`
- `backend/Files/output/task-1000156/adaptive_prompt_shrinker.md`
- `"backend/Files/output/task-1000156/\350\207\252\351\200\202\345\272\224\351\231\215\351\225\277\346\234\272\345\210\266\346\212\200\346\234\257\350\256\276\350\256\241.md"`
- `"backend/Files/output/task-1000156/\351\233\206\346\210\220\351\252\214\350\257\201\344\270\216\346\265\213\350\257\225\346\212\245\345\221\212.md"`
- `backend/Files/output/task-1000158/weekly_data_snapshot_report.md`
- `backend/Files/output/task-1000162/active_task_board.md`
- `backend/Files/output/task-1000164/ResourceDashboardAPI.md`
- `backend/Files/output/task-1000164/SystemResourceDashboard.py`
- `backend/Files/output/task-1000171/README.md`
- `backend/Files/output/task-1000171/alarm_channel_module.py`
- `backend/Files/output/task-1000171/api_documentation.md`
- `backend/Files/output/task-1000171/config_example.md`
- `backend/Files/output/task-1000171/test_alarm_channel.py`
- `backend/Files/output/task-1000174/cross_project_dependency_tech_spec.md`
- `backend/Files/output/task-1000178/llm-cost-weekly-report-example.md`
- `backend/Files/output/task-1000178/llm-cost-weekly-report-template.md`
- ... +3364 more; full list in `tracked_generated_candidates_20260624.tsv`

### secrets_env
- `backend.backup.20260315_073954/.env`
- `backend.backup.20260315_073954/.env.sqlite.backup.20260314_095912`
- `backend.backup.20260330_2345/.env`
- `backend.backup.20260330_2345/.env.sqlite.backup.20260314_095912`
- `backend/.env`
- `backend/.env.sqlite.backup.20260314_095912`
- `frontend.backup.20260330_2345/.env`
- `frontend/.env`
- `frontend/dist/uploads/docs/sds1-docs/.env`
- `frontend/public/uploads/docs/sds1-docs/.env`

### temp_patch_work
- `frontend/public/file:/tmp/task_1154_strategic_review_report.md`
- `static/file:/tmp/task_1154_strategic_review_report.md`

## Safe cleanup sequence
1. Keep this manifest branch separate from `master`.
2. Review `secrets_env` first; do not expose file contents in chat/logs.
3. Create `engineering/source-cleanup-YYYYMMDD` from this branch.
4. Run `git rm --cached -- <paths>` only for confirmed generated/runtime paths.
5. Confirm files remain on disk for production runtime where needed.
6. Run backend import smoke test + frontend build.
7. Push cleanup branch; merge to GitLab master only after verification.

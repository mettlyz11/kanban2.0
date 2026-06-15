#!/usr/bin/env python3
"""Auto-backup: daily snapshot of all SproutOS gardens"""
import json, shutil, os, datetime
from pathlib import Path

BACKUP_DIR = Path.home() / '.sprout_backups'
SPROUT_DIR = Path.home() / '.sprout'
BACKUP_DIR.mkdir(exist_ok=True)

def backup():
    today = datetime.date.today().isoformat()
    dest = BACKUP_DIR / today
    dest.mkdir(exist_ok=True)
    
    # Backup SQLite
    if (SPROUT_DIR / 'sprout.db').exists():
        shutil.copy2(SPROUT_DIR / 'sprout.db', dest / 'sprout.db')
    
    # Backup config
    config = os.path.expanduser('~/.openclaw/workspace/sds1/config/actor_enhancements.json')
    if os.path.exists(config):
        shutil.copy2(config, dest / 'actor_config.json')
    
    # Backup engine
    engine = os.path.expanduser('~/.openclaw/workspace/scripts/sprout_engine.py')
    if os.path.exists(engine):
        shutil.copy2(engine, dest / 'sprout_engine.py')
    
    # Cleanup old backups (keep 30 days)
    for d in sorted(BACKUP_DIR.iterdir()):
        if d.is_dir() and (datetime.date.today() - datetime.date.fromisoformat(d.name)).days > 30:
            shutil.rmtree(d)
    
    # print(f'Backup complete: {dest}')
    return dest

if __name__ == '__main__':
    backup()

#!/usr/bin/env python3
"""Deprecated one-off patch script.

Original file was syntactically invalid due nested triple-quoted SQL snippets.
It has been backed up under ../backups/syntax_fix_*/fix_api.py before this repair.
Do not run this script for production patching; modify app.py through reviewed diffs instead.
"""

if __name__ == "__main__":
    print("fix_api.py is deprecated; original invalid script preserved in backups/syntax_fix_*/")

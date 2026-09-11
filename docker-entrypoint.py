#!/usr/bin/env python3
"""Fix ownership of the bind-mounted data dir, then drop to appuser.

Runs as root only long enough to chown /app/data, so the container
works regardless of which UID owns ./data on the host.
"""
import os
import pwd
import sys

DATA_DIR = "/app/data"
USER = "appuser"


def main():
    if os.geteuid() == 0:
        pw = pwd.getpwnam(USER)
        os.makedirs(DATA_DIR, exist_ok=True)
        for root, dirs, files in os.walk(DATA_DIR):
            os.chown(root, pw.pw_uid, pw.pw_gid)
            for name in files:
                os.chown(os.path.join(root, name), pw.pw_uid, pw.pw_gid)
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)

    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
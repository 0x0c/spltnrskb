"""Smoke test (docs/specs/fusion-case.md step 1): runs inside Fusion and writes case/fusion/NrskSmoke.log."""
import datetime
import os
import sys
import traceback

import adsk.core

# the script is linked into Fusion's Scripts folder: resolve the link to reach the repository
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
LOG = os.path.join(ROOT, 'case', 'fusion', 'NrskSmoke.log')


def run(context):
    app = adsk.core.Application.get()
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'w') as f:
            f.write(f'ok {datetime.datetime.now().isoformat(timespec="seconds")}\n')
            f.write(f'fusion {app.version}\n')
            f.write(f'python {sys.version.split()[0]}\n')
            f.write(f'root {ROOT}\n')
        app.userInterface.messageBox(f'nrsk smoke: wrote {LOG}')
    except Exception:
        app.userInterface.messageBox('nrsk smoke failed:\n' + traceback.format_exc())

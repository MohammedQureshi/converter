#!/bin/sh
# Prepares writable runtime directories, then hands over to the given command.
#
# The default command is uvicorn. The app's lifespan startup launches the unoserver
# pool and Chromium and waits until they answer, and uvicorn does not accept requests
# until that finishes. The pool stays inside the app because the app must hand
# instances out through its asyncio queue and kill or restart hung ones.
set -eu

umask 077
mkdir -p "${WORK_DIR:-/tmp/work}" /tmp/home/.cache/fontconfig /tmp/lo

# Index mounted custom fonts before any engine starts.
if [ -d /fonts/custom ] && [ -n "$(ls -A /fonts/custom 2>/dev/null)" ]; then
    fc-cache -f /fonts/custom >/dev/null 2>&1 || echo "warning: fc-cache failed for /fonts/custom" >&2
fi

exec "$@"

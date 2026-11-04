#!/bin/sh
# Points apt at the given mirror, replacing the Debian default, and enables backports.
# The mirror must serve both /debian and /debian-security.
set -eu

mirror="${1:-http://deb.debian.org}"
sed -i "s#http://deb.debian.org#${mirror}#g" /etc/apt/sources.list.d/debian.sources
echo "deb ${mirror}/debian trixie-backports main" > /etc/apt/sources.list.d/backports.list

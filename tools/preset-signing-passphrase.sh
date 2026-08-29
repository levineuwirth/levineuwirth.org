#!/usr/bin/env bash
# preset-signing-passphrase.sh — Cache the signing subkey passphrase in the
# dedicated signing agent so that automated builds can sign without a prompt.
#
# Run this ONCE in an interactive terminal after system boot (or after the
# agent cache expires).  The passphrase is cached for 24 h (see gpg-agent.conf).
#
# Usage:
#   ./tools/preset-signing-passphrase.sh
#
# The script will prompt for the passphrase via the terminal (not pinentry).

set -euo pipefail

GNUPGHOME="${GNUPGHOME:-$HOME/.gnupg-signing}"
KEYGRIP="619844703EC398E70B0045D7150F08179CFEEFE3"
GPG_PRESET="/usr/lib/gnupg/gpg-preset-passphrase"

if [ ! -x "$GPG_PRESET" ]; then
    echo "Error: gpg-preset-passphrase not found at $GPG_PRESET" >&2
    exit 1
fi

# Ensure the agent is running with our config.
GNUPGHOME="$GNUPGHOME" gpg-connect-agent --homedir "$GNUPGHOME" /bye >/dev/null 2>&1 || true

echo -n "Signing subkey passphrase: "
read -rs PASSPHRASE
echo

# printf, not `echo -n`: a passphrase starting with -e/-n/-E would be
# eaten as an echo option.
printf '%s' "$PASSPHRASE" | GNUPGHOME="$GNUPGHOME" "$GPG_PRESET" --homedir "$GNUPGHOME" --preset "$KEYGRIP"

echo "Passphrase cached for keygrip $KEYGRIP (24 h TTL)."
echo "Test: GNUPGHOME=$GNUPGHOME gpg --homedir $GNUPGHOME --batch --detach-sign --armor --output /dev/null /dev/null"

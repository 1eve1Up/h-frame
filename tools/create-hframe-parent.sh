#!/usr/bin/env bash
# Bootstrap a vault H-Frame parent layout. Usage: ./create-hframe-parent.sh <git-url>
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <git-url>" >&2
  exit 2
fi

GIT_URL="$1"
SLUG=$(basename "${GIT_URL%.git}")
PROJECT_NAME="${SLUG}-parent"

HFRAME_SRC="${HFRAME_SRC:-$HOME/Documents/Code/1eve1Up/H-Frame}"

mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "${HFRAME_SRC}[vault]"

python -c "import hframe.vault_cli"

export HFRAME_BOOTSTRAP_DEBUG=1
hframe-bootstrap --vault "$GIT_URL"

echo ""
echo "Bootstrap parent: $(pwd)"
echo "Save the vault password printed above, then:"
echo "  export HFRAME_VAULT_PASS='<that value>'"
echo "  ./hframe-vault decrypt allowlist   # edit policy, then encrypt"
echo "  cd <slug>_workspace_repo && ./hframe in|out   # no HFRAME_VAULT_PASS needed"

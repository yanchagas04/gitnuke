#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "Erro: uv não encontrado. Instale em https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

uv sync
exec uv run delete-github-repos

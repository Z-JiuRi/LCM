#!/usr/bin/env bash

set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
manifest="$script_dir/公开代码仓库.tsv"
destination_root="$script_dir/codes"
mkdir -p "$destination_root"

if ! command -v git >/dev/null 2>&1; then
  printf 'git is required but was not found in PATH.\n' >&2
  exit 127
fi

cloned=0
skipped=0
failed=0

while IFS=$'\t' read -r paper_id repository target_name branch evidence_type license_status; do
  [[ -z "${paper_id:-}" || "$paper_id" == "paper_id" ]] && continue
  branch="${branch# }"
  if [[ ! "$target_name" =~ ^[A-Za-z0-9._-]+$ || ! "$repository" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    printf 'Invalid manifest entry for %s: %s\n' "$paper_id" "$repository" >&2
    failed=$((failed + 1))
    continue
  fi

  target="$destination_root/$target_name"
  repository_url="https://github.com/$repository.git"

  if [[ -d "$target/.git" ]]; then
    existing_url="$(git -C "$target" config --get remote.origin.url || true)"
    if [[ "$existing_url" == "$repository_url" || "$existing_url" == "$repository" || "$existing_url" == "git@github.com:$repository.git" ]]; then
      printf 'Already present: %s -> %s\n' "$paper_id" "$target"
      skipped=$((skipped + 1))
    else
      printf 'Refusing to overwrite %s: origin is %s\n' "$target" "${existing_url:-unknown}" >&2
      failed=$((failed + 1))
    fi
    continue
  fi

  if [[ -e "$target" ]]; then
    printf 'Refusing to overwrite existing non-repository path: %s\n' "$target" >&2
    failed=$((failed + 1))
    continue
  fi

  clone_args=(clone --depth 1)
  if [[ -n "$branch" && "$branch" != "-" ]]; then
    clone_args+=(--branch "$branch" --single-branch)
  fi
  clone_args+=("$repository_url" "$target")

  printf 'Cloning %s (%s) into %s\n' "$repository" "$paper_id" "$target"
  printf 'Source: %s | license status: %s\n' "$evidence_type" "$license_status"
  if git "${clone_args[@]}"; then
    cloned=$((cloned + 1))
  else
    failed=$((failed + 1))
    printf 'Clone failed: %s\n' "$repository" >&2
  fi
done < "$manifest"

printf 'Done: %s cloned, %s already present, %s failed.\n' "$cloned" "$skipped" "$failed"
if (( failed > 0 )); then
  exit 1
fi

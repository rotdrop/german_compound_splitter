#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 VERSION (for example: 0.1.5 or 0.1.5-rc1)" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
version=$1
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || usage

repo_root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$repo_root"

if [[ $(git branch --show-current) != master ]]; then
  echo "Release must be run from the master branch." >&2
  exit 1
fi

if [[ -n $(git status --porcelain) ]]; then
  echo "Working tree must be clean before releasing." >&2
  exit 1
fi

tag="v$version"
package_version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
normalized_version=${version/-rc/rc}
if [[ $package_version != "$version" && $package_version != "$normalized_version" ]]; then
  echo "Release version $version does not match pyproject.toml version $package_version." >&2
  exit 1
fi

release_notes=$(awk -v v="$version" '
  /^## / {
    if (found) exit
    h = $0
    sub(/^## +\[?/, "", h)
    split(h, a, /[] ]/)
    if (a[1] == v) { found = 1; next }
  }
  found { print }
' CHANGELOG.md)
if ! grep -q '[^[:space:]]' <<< "$release_notes"; then
  echo "CHANGELOG.md has no non-empty entry for $version." >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/tags/$tag"; then
  echo "Tag $tag already exists locally." >&2
  exit 1
fi

remote_tag=$(git ls-remote --tags origin "refs/tags/$tag")
if [[ -n $remote_tag ]]; then
  echo "Tag $tag already exists on origin." >&2
  exit 1
fi

git tag -a "$tag" -m "Release $tag"
git push origin "$tag"

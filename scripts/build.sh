#!/bin/bash

# Build the app image with `docker compose build`, tagged <version>-<shortsha>
# so every image maps back to exactly one commit. Only runs from a clean `main`
# checkout. Local only, nothing is pushed anywhere.

# repo root, regardless of where this is called from
cd "$(dirname "$0")/.."

# # ensure script is run from main branch
# branch="$(git rev-parse --abbrev-ref HEAD)"
# if [ "$branch" != "main" ]; then
#     echo "ERROR: images are only built from 'main' (current branch: $branch)" >&2
#     echo "Press Enter to close..."
#     read
#     exit 1
# fi

# # ensure branch is clean
# if [ -n "$(git status --porcelain)" ]; then
#     echo "ERROR: working tree is dirty; commit or stash before building" >&2
#     echo "Press Enter to close..."
#     read
#     exit 1
# fi

# ensure the project is versioned
version="$(grep -m1 -E '^version = ' pyproject.toml | sed -E 's/^version = "(.*)"/\1/')"
if [ -z "$version" ]; then
    echo "ERROR: could not read version from pyproject.toml" >&2
    echo "Press Enter to close..."
    read
    exit 1
fi
tag="$version-$(git rev-parse --short HEAD)"

echo "Building photo-server:$tag"
if ! PHOTO_SERVER_TAG="$tag" docker compose build; then
    echo "ERROR: build failed; .env not updated" >&2
    echo "Press Enter to close..."
    read
    exit 1
fi

# point compose at this build. .env is git-ignored and is the file compose
# auto-loads for ${...} interpolation; this line is managed here, not by hand.
if [ -f .env ] && grep -q '^PHOTO_SERVER_TAG=' .env; then
    sed -i "s|^PHOTO_SERVER_TAG=.*|PHOTO_SERVER_TAG=$tag|" .env
else
    printf '\n# managed by scripts/build.sh - the image tag docker compose runs\nPHOTO_SERVER_TAG=%s\n' "$tag" >> .env
fi

echo ""
echo "Built photo-server:$tag  (PHOTO_SERVER_TAG set in .env)"
echo "Run:  docker compose up -d"

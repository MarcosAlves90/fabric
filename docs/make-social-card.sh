#!/usr/bin/env bash
# The social card's layout and hero artwork are in docs/social-preview.svg and
# docs/hero-character.png. Run from the repo root.
set -euo pipefail
sips -s format png docs/social-preview.svg --out "$TMPDIR/fabric-social-base.png"
magick "$TMPDIR/fabric-social-base.png" \
  \( docs/hero-character.png -resize x600 \) -gravity southwest -geometry +56+6 -composite \
  docs/social-preview.png
magick docs/social-preview.png -resize 1200x600! docs/banner.png
echo "wrote docs/social-preview.png and docs/banner.png"

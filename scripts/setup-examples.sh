#!/bin/bash
# setup-examples.sh — fetch a real-world example project for trying out Lumos.
#
# Lumos ships without bundled example data to keep the plugin lean. This
# script clones Microsoft's FLAML repo into examples/FLAML/ so you can run
# /lumos:everything against a substantial Python + notebook codebase.

set -e

EXAMPLES_DIR="examples"
FLAML_DIR="$EXAMPLES_DIR/FLAML"

mkdir -p "$EXAMPLES_DIR"

if [ -d "$FLAML_DIR" ]; then
  echo "FLAML already cloned at $FLAML_DIR — skipping."
else
  echo "Cloning microsoft/FLAML into $FLAML_DIR ..."
  git clone --depth 1 https://github.com/microsoft/FLAML "$FLAML_DIR"
fi

echo ""
echo "Done. Try it out:"
echo "  /lumos:everything $FLAML_DIR"

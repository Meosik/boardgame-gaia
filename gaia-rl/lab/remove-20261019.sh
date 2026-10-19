#!/bin/sh
# Remove the specs and tests of the teacher factories deleted on 2026-10-19 (HANDOFF 5a D7).
# Run by the user (the bot does not delete files):
#   cd ~/projects/gaia-work && sh gaia-rl/lab/remove-20261019.sh
# Removes itself at the end, commits and pushes.
set -e
cd "$(dirname "$0")/.."
git rm -q \
  tools/test_distinct_search.py \
  tools/geodens_pi4_check.py \
  tools/teacher-a-search2-h1-booster.json \
  tools/teacher-a-search2-h1-distinct-cap5.json \
  tools/teacher-a-search4-h1-distinct-cap10.json \
  tools/teacher-a-search4-h1-distinct-cap20.json \
  tools/teacher-a-search4-h1-distinct-openings-cap10.json \
  tools/teacher-a-search4-h1-distinct-openings-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-ac-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-sh-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-vp1-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-plus-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-focus-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-setup-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-former-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-when-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-defend-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-fix-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-when-all-tech-fix-setup-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-geodens-prior-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-label-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-label-value-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-noformer-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-noacademy-cap20.json \
  tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-label-cap20.json \
  lab/remove-20261019.sh
git commit -q -m "tools: remove specs and tests of the factories deleted on 2026-10-19"
git push origin HEAD:claude/epic-goodall-0ot55w
echo "removed 29 files and this script; pushed"

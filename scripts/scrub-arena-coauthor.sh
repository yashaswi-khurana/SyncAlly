#!/usr/bin/env bash
#
# Remove the "Co-authored-by: arena-agent <...>" trailer from every commit.
#
# GitHub builds its contributor list (and the "Co-authored-by" credit) from
# `Co-authored-by:` trailers in commit messages, so stripping the trailer is
# enough: no code, author, committer, date or message text changes, and the
# resulting trees are byte-identical.
#
# Usage:
#   scripts/scrub-arena-coauthor.sh                 # dry run, report only
#   scripts/scrub-arena-coauthor.sh --apply         # rewrite current branch
#   scripts/scrub-arena-coauthor.sh --apply --all   # rewrite every local branch
#
# Then force-push the rewritten branches (see the reminder the script prints).
#
# Notes
#  * Rewriting history changes every commit id from the first patched commit
#    onwards, so open PRs and other clones have to be re-synced/rebased.
#  * GitHub caches contributor statistics; the old name may linger in the
#    sidebar for a few hours to a day after the push.
#
set -euo pipefail

APPLY=0
ALL=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --all) ALL=1 ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg (try --help)" >&2; exit 2 ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"

if [ "$ALL" -eq 1 ]; then
  BRANCHES=$(git for-each-ref --format='%(refname:short)' refs/heads)
else
  BRANCHES=$(git rev-parse --abbrev-ref HEAD)
  [ "$BRANCHES" = "HEAD" ] && { echo "detached HEAD; check out a branch or pass --all" >&2; exit 1; }
fi

echo "Commits carrying an arena-agent Co-authored-by trailer:"
git log --format='  %h  %ad  %s' --date=short --grep='arena-agent' $BRANCHES | cat || true
echo

if [ "$APPLY" -eq 0 ]; then
  echo "Dry run only. Re-run with --apply (add --all for every local branch)."
  exit 0
fi

FILTER=$(mktemp)
trap 'rm -f "$FILTER"' EXIT
cat > "$FILTER" <<'PY'
import re, sys

msg = sys.stdin.read()
trailer = re.compile(r'^[ \t]*co-authored-by:[ \t]*arena-agent[ \t]*<[^>\n]*>[ \t]*$', re.I)
lines = [line for line in msg.split('\n') if not trailer.match(line)]
out = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).rstrip() + '\n'
sys.stdout.write(out)
PY

before_trees=$(git log --format='%T' $BRANCHES | sort | md5sum)

# filter-branch writes a "Rewrite <sha>" progress line per commit on stderr;
# keep only the interesting lines so the output stays readable.
LOGFILE=$(mktemp)
trap 'rm -f "$FILTER" "$LOGFILE"' EXIT

FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --msg-filter "python3 '$FILTER'" \
  -- $BRANCHES >/dev/null 2>"$LOGFILE" || {
    tr '\r' '\n' < "$LOGFILE" >&2
    exit 1
  }
tr '\r' '\n' < "$LOGFILE" | grep -v '^Rewrite ' | sed '/^$/d; s/^/  /' || true

after_trees=$(git log --format='%T' $BRANCHES | sort | md5sum)
if [ "$before_trees" != "$after_trees" ]; then
  echo "!! trees changed unexpectedly - restore with: git reset --hard refs/original/refs/heads/<branch>" >&2
  exit 1
fi

echo
echo "Trailers left in history: $(git log --format=%H --grep='arena-agent' $BRANCHES | wc -l | tr -d ' ')"
echo "File content unchanged (tree ids match)."
echo
echo "Now force-push (only after you are happy with the rewrite):"
echo "  git push --force-with-lease origin $BRANCHES"
echo "Drop the backup refs when done: git for-each-ref --format='%(refname)' refs/original | xargs -n1 git update-ref -d"

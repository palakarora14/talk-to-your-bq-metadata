---
name: github-cli
description: |
  Interact with REA's GitHub Enterprise (git.realestate.com.au) only — not github.com.
  Use for: reading code, searching repos, exploring issues and PRs.
  Trigger on: "look at the repo", "check the PR", "what's in that file",
  "find the code for", "list issues", "browse the codebase",
  "what changed in that PR", "clone the repo", "search for X in <repo>".
  Read operations only. Write operations (PRs, issues, comments) are not permitted.
---

# GitHub Enterprise CLI (github-cli) Skill

Target host: `git.realestate.com.au` (REA GitHub Enterprise) via SSH.
**Read-only** — write operations are not permitted.

> **Important:** This skill is for `git.realestate.com.au` only. Do not use it for `github.com` repos.

---

## Setup (check before every use)

Always verify `gh` is available and authenticated before running any `gh` command:

```bash
# 1. Check gh is installed
if ! command -v gh &>/dev/null; then
  echo "gh CLI not found — install it first"
fi

# 2. Check authentication status for REA GHE
gh auth status --hostname git.realestate.com.au 2>&1
```

If `gh` is **not installed**, tell the user and suggest:

```bash
# macOS (Homebrew)
brew install gh

# Then authenticate against REA GHE
gh auth login --hostname git.realestate.com.au --git-protocol ssh
```

If `gh` is installed but **not authenticated** to `git.realestate.com.au`, tell the user:

```bash
gh auth login --hostname git.realestate.com.au --git-protocol ssh
```

If authentication succeeds, discover the current user — **do not assume or hardcode the username**, always read it:

```bash
GH_USER=$(gh api --hostname git.realestate.com.au user --jq '.login')
echo "Authenticated as: $GH_USER"
```

Use `$GH_USER` in subsequent commands wherever the authenticated user's login is needed.

---

## Discover

```bash
gh repo view <owner>/<repo> --hostname git.realestate.com.au   # overview
gh repo list <owner> --hostname git.realestate.com.au --limit 50
gh search repos --owner <owner> --hostname git.realestate.com.au
gh search issues --repo <owner>/<repo> --hostname git.realestate.com.au "query" is:open label:bug
gh search code --repo <owner>/<repo> --hostname git.realestate.com.au "SearchService"
```

## Read

For code exploration, clone to `/tmp/` and use the `read` tool.

```bash
# Replace <owner>/<repo> with the actual org/repo (ask the user if unknown)
REPO=<owner>/<repo>
REPO_NAME=$(basename $REPO)
if [ -d "/tmp/$REPO_NAME" ]; then
  git -C "/tmp/$REPO_NAME" pull
else
  git clone git@git.realestate.com.au:$REPO.git /tmp/$REPO_NAME
fi
# then use the `read` tool on /tmp/$REPO_NAME/...
```

## Issues & PRs

```bash
gh issue view 42 --repo <owner>/<repo> --hostname git.realestate.com.au --json title,body,labels,assignees,comments
gh pr list --repo <owner>/<repo> --hostname git.realestate.com.au --state open
gh pr view 15 --repo <owner>/<repo> --hostname git.realestate.com.au --json title,body,files,reviews,mergeable
gh pr diff 15 --repo <owner>/<repo> --hostname git.realestate.com.au
gh pr checks 15 --repo <owner>/<repo> --hostname git.realestate.com.au
```

---

**Troubleshooting:** Always pass `--hostname git.realestate.com.au` explicitly — some environments have a default host set to `github.com`. Run `gh auth status` to inspect all configured hosts.
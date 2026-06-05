# Setup — pushing this to GitHub

The folder you're holding is git-ready. To get it live on GitHub:

## 1. Move the folder onto your local machine

If you've been working in a sandbox / Cowork environment, copy the entire `public-release/` folder to your local machine first. Rename it to whatever you want the project to be called (suggestion: `indie-publishing-pipeline/` or `kdp-pipeline/`).

```bash
mv public-release indie-publishing-pipeline
cd indie-publishing-pipeline
```

## 2. Initialize git (if not already initialized)

If you transferred a `.git/` directory along with the files, remove it first to start fresh:

```bash
rm -rf .git
git init
git branch -M main
```

## 3. Set your git identity (skip if already configured globally)

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
```

## 4. Stage and commit

```bash
git add .
git status     # confirm everything you expect is there

git commit -m "Initial release — indie book publishing pipeline v1.0.0"
```

## 5. Create a new GitHub repo

Go to [github.com/new](https://github.com/new) and create a new repository:

- **Name:** `indie-publishing-pipeline` (or whatever you chose)
- **Description:** *"Open-source self-publishing toolkit for KDP — docx to print PDF + Kindle EPUB, with full pre-flight validation. Battle-tested on a 60,000-word book launched in 2026."*
- **Public** or **Private** — your call
- **Do NOT** initialize with a README, .gitignore, or LICENSE (you already have those)

## 6. Push

GitHub will show you the exact remote URL after you click Create. Paste those two commands (yours will look like this with your username/repo):

```bash
git remote add origin https://github.com/rgupta0419/indie-publishing-pipeline.git
git push -u origin main
```

That's it. The repo is live.

---

## After it's live — recommended next steps

### Add topics / tags on GitHub

In the repo's main page, click the ⚙️ next to "About" and add topics:

- `kdp`
- `kindle-direct-publishing`
- `self-publishing`
- `indie-author`
- `epub`
- `book-publishing`
- `amazon-kdp`
- `python`

Topics show up in GitHub's discovery and help your repo reach the indie authors who'd use it.

### Pin the repo to your profile

Pinned repos appear at the top of your GitHub profile. If this is the project you want indie authors to find, pin it.

### Optional: Enable GitHub Discussions

Settings → Features → Discussions. Lets users ask questions without filing formal issues. Useful for an open-source author tool.

### Optional: Add a CITATION.cff

If you'd like academic / writing-tool citations:

```yaml
cff-version: 1.2.0
message: "If you use this software in your published book, please cite it."
authors:
  - family-names: "Your Last Name"
    given-names: "Your First Name"
title: "Indie Publishing Pipeline"
version: 1.0.0
date-released: 2026-06-XX
url: "https://github.com/rgupta0419/indie-publishing-pipeline"
```

### Announce it

Now you can share it. Suggested channels:

- **r/selfpublishing**, **r/PubTips**, **r/KDP** — short post linking the repo, lead with "I just published my first book and open-sourced the production pipeline. Here are the 15 problems I hit that nobody warns you about." Link to STORY.md.
- **Hacker News** — submit the repo. Title format: *"Show HN: Open-source publishing pipeline (KDP, Kindle EPUB, cover wraps) — from my first book"*. First comment: post a short version of the STORY.md "Where this started" section.
- **Indie Hackers** — community of solo creators; the toolkit fits.
- **X / Twitter** — short thread, 5-7 tweets. Lead with one of the receipts (the spine rejection, the broken TOC, the $200 vanity quote). End with link to repo + book.
- **Substack** — write a longer-form post mirroring STORY.md, but tighter. Link to the repo at the close.

Don't make the announcement about you — make it about the receipts. Authors who hit the same problems will find the repo through the problems, not through your name.

---

## If you have an existing `.git/` directory from the source folder

Sandboxes sometimes create partial git directories that don't have a clean commit history. If `git log` returns "fatal: your current branch 'main' does not have any commits yet" or behaves strangely, just nuke `.git/` and start over:

```bash
rm -rf .git
git init
git branch -M main
git add .
git commit -m "Initial release — indie book publishing pipeline v1.0.0"
```

You won't lose any work — the actual files are untouched; only the git metadata gets refreshed.

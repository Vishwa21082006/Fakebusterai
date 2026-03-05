# 🤝 FakeBuster AI — Team Collaboration Guide

> **For:** Vishwa + 3 team members working on this project together.

---

## 📋 Table of Contents
1. [Initial Setup (Each Team Member)](#1-initial-setup-each-team-member)
2. [Team Workflow — Golden Rules](#2-team-workflow--golden-rules)
3. [Step-by-Step: Making Changes](#3-step-by-step-making-changes)
4. [Pull Requests (PR) Guide](#4-pull-requests-pr-guide)
5. [Reviewing & Merging PRs](#5-reviewing--merging-prs)
6. [Handling Merge Conflicts](#6-handling-merge-conflicts)
7. [Team Role Suggestions](#7-team-role-suggestions)

---

## 1. Initial Setup (Each Team Member)

### Step 1: Clone the repo
```bash
git clone https://github.com/Vishwa21082006/Fakebusterai.git
cd Fakebusterai
```

### Step 2: Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Run the project locally
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Open **http://localhost:8000** in your browser.

### Step 4: Run tests
```bash
cd backend
python -m pytest tests/ -v
```

---

## 2. Team Workflow — Golden Rules

```
⚠️  NEVER push directly to the `main` branch!
```

### The Branch Workflow

```
main (protected - always working code)
 │
 ├── feature/add-login-page        ← Team Member 1
 ├── feature/upload-api-fix         ← Team Member 2
 ├── bugfix/fix-auth-error          ← Team Member 3
 └── feature/add-ml-model           ← Team Member 4
```

### Branch Naming Convention

| Type | Format | Example |
|------|--------|---------|
| New feature | `feature/short-description` | `feature/add-video-analysis` |
| Bug fix | `bugfix/short-description` | `bugfix/fix-login-error` |
| Improvement | `improve/short-description` | `improve/faster-upload` |
| Documentation | `docs/short-description` | `docs/update-readme` |

---

## 3. Step-by-Step: Making Changes

### Step 1: Always start by pulling the latest code
```bash
git checkout main
git pull origin main
```

### Step 2: Create a new branch for your work
```bash
git checkout -b feature/your-feature-name
```
Example:
```bash
git checkout -b feature/add-dashboard-charts
```

### Step 3: Make your changes
Edit the files you need. Save your work.

### Step 4: Check what you changed
```bash
git status          # Shows modified files
git diff            # Shows exact changes
```

### Step 5: Stage your changes
```bash
git add .                   # Stage ALL changes
# OR
git add backend/app/api/auth.py   # Stage specific file
```

### Step 6: Commit with a clear message
```bash
git commit -m "feat: add pie chart to dashboard for analysis results"
```

**Commit message format:**
| Prefix | When to use |
|--------|-------------|
| `feat:` | Adding new feature |
| `fix:` | Fixing a bug |
| `docs:` | Documentation changes |
| `style:` | CSS/formatting changes |
| `refactor:` | Code restructuring |
| `test:` | Adding/fixing tests |

### Step 7: Push your branch to GitHub
```bash
git push origin feature/your-feature-name
```

---

## 4. Pull Requests (PR) Guide

### Creating a Pull Request

1. **Go to** https://github.com/Vishwa21082006/Fakebusterai
2. You'll see a banner: **"feature/your-branch had recent pushes — Compare & pull request"**
3. Click **"Compare & pull request"**
4. Fill in the PR form:

```markdown
## What does this PR do?
- Added pie chart visualization to the dashboard
- Shows analysis result breakdown by status (queued, done, failed)

## How to test?
1. Login to the app
2. Upload a few images
3. Check the dashboard — pie chart should appear

## Screenshots (if UI changes)
[Paste screenshots here]
```

5. **Assign reviewers** — tag at least 1 team member to review
6. Click **"Create Pull Request"**

### PR Checklist (before creating)
- [ ] Code works locally
- [ ] Tests pass (`python -m pytest tests/ -v`)
- [ ] No unnecessary files committed (check `.gitignore`)
- [ ] Clear commit messages
- [ ] PR description explains what you did

---

## 5. Reviewing & Merging PRs

### As a Reviewer

1. Go to the PR on GitHub
2. Click **"Files changed"** tab to see the code
3. **Add comments** on specific lines if you see issues
4. Click **"Review changes"** and select:
   - ✅ **Approve** — Code looks good
   - 💬 **Comment** — Just leaving feedback
   - ❌ **Request changes** — Something needs to be fixed
5. Submit your review

### Merging (after approval)

1. Make sure at least **1 team member** has approved
2. Click **"Merge pull request"** → **"Confirm merge"**
3. Click **"Delete branch"** (keeps repo clean)

### After someone else merges a PR

Everyone should update their local code:
```bash
git checkout main
git pull origin main
```

If you're working on a branch, also update it:
```bash
git checkout your-branch-name
git merge main
```

---

## 6. Handling Merge Conflicts

If Git says **"merge conflict"**, don't panic!

### Step 1: Pull latest main into your branch
```bash
git checkout your-branch
git merge main
```

### Step 2: Open conflicting files
You'll see sections like:
```
<<<<<<< HEAD
your code here
=======
their code here
>>>>>>> main
```

### Step 3: Fix it
- Keep the code you want
- Delete the `<<<<<<<`, `=======`, `>>>>>>>` markers
- Save the file

### Step 4: Complete the merge
```bash
git add .
git commit -m "fix: resolve merge conflict in auth.py"
git push origin your-branch
```

### 💡 Tips to avoid conflicts
- **Pull from main frequently** (at least once daily)
- **Work on different files** when possible
- **Communicate** with your team about what you're working on

---

## 7. Team Role Suggestions

| Role | Person | Responsibility |
|------|--------|----------------|
| **Project Lead** | Vishwa | Manages repo, reviews PRs, merges to main |
| **Backend Dev** | Friend 1 | API routes, database, authentication |
| **Frontend Dev** | Friend 2 | HTML/CSS/JS, UI components, styling |
| **ML / Testing** | Friend 3 | ML model integration, writing tests |

### Divide the codebase to avoid conflicts:

```
fakebuster/
├── backend/
│   ├── app/api/          ← Backend Dev works here
│   ├── app/core/         ← Backend Dev works here
│   ├── app/models/       ← Backend Dev works here
│   ├── tests/            ← ML/Testing works here
│   └── ...
├── frontend/
│   ├── index.html        ← Frontend Dev works here
│   ├── styles.css        ← Frontend Dev works here
│   └── app.js            ← Frontend Dev works here
└── ml/
    └── detector_stub.py  ← ML/Testing works here
```

---

## 🏁 Quick Reference Card

```bash
# === Daily Start ===
git checkout main
git pull origin main
git checkout -b feature/my-new-feature

# === While Working ===
git add .
git commit -m "feat: describe what you did"

# === When Done ===
git push origin feature/my-new-feature
# Then create PR on GitHub

# === After PR is Merged ===
git checkout main
git pull origin main
git branch -d feature/my-new-feature    # delete local branch
```

---

**Questions?** Ask Vishwa or check [GitHub Docs](https://docs.github.com/en/pull-requests).

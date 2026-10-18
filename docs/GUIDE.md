# From zip to live app: VS Code, GitHub, Streamlit Cloud

Do the parts in order. Each ends with a check so you know it worked before moving on.

---

## Part 0. One-time installs

You need: **Python 3.11 or newer**, **Git**, **VS Code** (with the *Python* extension), and a free **GitHub** account.

Check in a terminal:

```bash
python --version      # 3.11+  (on macOS/Linux try python3)
git --version
```

Tell Git who you are (once per computer):

```bash
git config --global user.name  "Your Name"
git config --global user.email "the-email-you-used-on-github@example.com"
```

---

## Part 1. Open the project in VS Code and run it locally

1. Unzip `containnet.zip`. You get a folder called `containnet`.
2. VS Code: **File > Open Folder...** and pick that `containnet` folder (the one containing `app.py`, not its parent).
3. Open the terminal: **Terminal > New Terminal**.
4. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
     (if it says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry)
   - Windows (cmd): `.venv\Scripts\activate.bat`
   - macOS / Linux: `source .venv/bin/activate`

   You should see `(.venv)` at the start of the prompt. If VS Code asks "use this environment?", click **Yes**.
5. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```
6. Run the app:

   ```bash
   streamlit run app.py
   ```
   Your browser opens at `http://localhost:8501`.

**Check:** you see the ContainNet header and a sentence like "Protect 8 of 75 people ...". Click through Plan, Replay, Groups, Evidence, About.
Stop the app with `Ctrl+C`.

Optional, but worth doing once:

```bash
python tests/test_core.py        # five lines starting with "ok"
python scripts/run_all.py        # regenerates everything in results/ (about a minute)
```

The `results/` folder is already filled in, so you can skip `run_all.py`. Re-run it whenever you change settings in
`containnet/config.py`, then commit the new files.

---

## Part 2. Put it on GitHub

### 2a. Create the empty repository on github.com

1. Click **+ > New repository**.
2. Name: `containnet`. Visibility: **Public** (Streamlit's free tier deploys from public repos).
3. **Do not** tick "Add a README", ".gitignore" or "license". The project already has them, and ticking them makes the first push fail.
4. Click **Create repository**. Leave the page open: it shows your repo URL, e.g. `https://github.com/YOUR_USERNAME/containnet.git`.

### 2b. Push from VS Code's terminal (inside the `containnet` folder)

```bash
git init
git add .
git status                      # skim it: no .venv, no __pycache__ (the .gitignore handles that)
git commit -m "ContainNet: initial version"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/containnet.git
git push -u origin main
```

On the first push, a browser window or prompt asks you to sign in to GitHub. Use the browser sign-in (Git Credential Manager).
If it asks for a password in the terminal, GitHub no longer accepts account passwords: create a token at
GitHub > Settings > Developer settings > Personal access tokens, and paste that instead.

**Check:** refresh the GitHub repo page. You see `app.py`, `containnet/`, `results/`, and the README renders with the results table.

### 2c. Small polish (2 minutes)

- Edit `LICENSE` and replace `<YOUR NAME>`.
- Repo page > the gear next to **About**: add a description and topics such as `network-analysis`, `epidemiology`, `streamlit`, `community-detection`.

---

## Part 3. Deploy on Streamlit Community Cloud

1. Go to **share.streamlit.io** and sign in with GitHub. Authorise access when asked.
2. Click **Create app** (or **New app**) and choose **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `YOUR_USERNAME/containnet`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: pick a short name, e.g. `containnet`
4. Open **Advanced settings** and choose **Python 3.12** (3.11 or 3.13 also work).
5. Click **Deploy**. The first build takes 2 to 4 minutes while it installs `requirements.txt`.

**Check:** your app opens at `https://<your-name>.streamlit.app`.

### 3b. Close the loop

1. Paste the live URL into `README.md` where it says "add your Streamlit URL here".
2. Commit and push:

   ```bash
   git add README.md
   git commit -m "Add live app link"
   git push
   ```

From now on, every `git push` to `main` redeploys the app automatically.

---

## Day-to-day workflow

```bash
# edit code in VS Code, test locally with: streamlit run app.py
git add .
git commit -m "describe what you changed"
git push
```

Changed anything that affects numbers (settings, simulation, strategies)? Run `python scripts/run_all.py` first and commit the new `results/`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `streamlit: command not found` | The virtual environment is not active. Activate it (Part 1, step 4) and retry, or run `python -m streamlit run app.py`. |
| `ModuleNotFoundError: containnet` or `ui` | You started the app from the wrong folder. `cd` into the folder that contains `app.py`. |
| `git push` rejected, "fetch first" | You ticked README/license when creating the repo. Run `git pull origin main --allow-unrelated-histories`, resolve any conflict, push again. |
| `git push` asks for a password | Use a Personal Access Token, or sign in via the browser prompt (see 2b). |
| Streamlit Cloud: `ModuleNotFoundError` | The package is missing from `requirements.txt`. Add it, commit, push. |
| Streamlit Cloud: app is slow on first load only | Normal. Results are cached after the first visitor. |
| Fonts look different | The Google Fonts could not load (offline or blocked). The app falls back to system fonts. |
| `data/hospital_contact_graph.graphml` missing | Run `python scripts/00_build_graph.py` (uses the zip in `data/raw/`; downloads only if the zip is absent). |

---

## Checklist

- [ ] App runs locally
- [ ] Repo created on GitHub (empty, public) and code pushed
- [ ] LICENSE name edited
- [ ] App deployed on Streamlit Cloud
- [ ] Live URL pasted into README and pushed

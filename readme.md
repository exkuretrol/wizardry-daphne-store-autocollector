### Wizardry Variants Daphne Store Autocollector

\[English | [繁體中文](readme.zh-TW.md)\]

A tiny tool that auto-collects the weekly free rewards from the [Wizardry Variants Daphne online store](https://store.wizardry.info/). It targets the international web store, so no VPN is required.

The recommended way to use it is **GitHub Actions** — fork this repo, set one secret, done. Your machine never has to be on.

### Quick start (GitHub Actions, recommended)

1. **Fork** this repo.
2. In your fork, go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Add a secret named `WIZARDRY_USER_ID` with your Wizardry user ID as the value.
4. Go to the **Actions** tab and enable workflows if prompted.
5. Done. The workflow runs every Monday at 11:00 UTC. To verify the setup, manually trigger it from the Actions tab.

To change the schedule, edit the `cron` line in `.github/workflows/python-app.yml`. See [crontab.guru](https://crontab.guru/) — note that GitHub Actions always uses UTC.

A second workflow at `.github/workflows/keep-alive.yml` uses [`pagopa/dx`'s keep-alive action](https://github.com/pagopa/dx/tree/main/actions/keep-alive) to push an empty commit when the repo has been inactive for 55+ days. This prevents GitHub from auto-disabling the autocollector schedule after 60 days of inactivity. No setup needed — it uses the auto-provisioned `GITHUB_TOKEN`.

### Running locally (optional)

If you'd rather run the script on your own machine:

```
pip install -r requirements.txt
python main.py [your_Wizardry_ID]
```

Requires Chrome and a matching Chrome webdriver.

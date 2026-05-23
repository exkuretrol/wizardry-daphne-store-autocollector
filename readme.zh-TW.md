### Wizardry Variants Daphne 商店自動領取工具

\[[English](readme.md) | 繁體中文\]

一個小工具，自動領取 [Wizardry Variants Daphne 線上商店](https://store.wizardry.info/) 每週免費的獎勵。針對國際版網頁商店，**不需要 VPN**。

推薦的使用方式是 **GitHub Actions** —— Fork 一份、設定一個 secret，就完成了，你的電腦完全不用開機。

### 快速設定（GitHub Actions，推薦）

1. **Fork** 本 repo。
2. 在你 fork 的 repo 中前往 **Settings → Secrets and variables → Actions → New repository secret**。
3. 新增一個名為 `WIZARDRY_USER_ID` 的 secret，值為你的 Wizardry ID。
4. 進入 **Actions** 分頁，若有提示請啟用 workflow。
5. 完成。預設每週一 UTC 11:00（台灣時間週一 19:00）自動執行。可在 Actions 分頁手動觸發一次驗證設定。

想改執行時間，編輯 `.github/workflows/python-app.yml` 中的 `cron` 字串即可。格式說明可參考 [crontab.guru](https://crontab.guru/)，注意 **GitHub Actions 一律使用 UTC 時間**。

另外有一個 `.github/workflows/keep-alive.yml` 工作流程，使用 [`pagopa/dx` 的 keep-alive action](https://github.com/pagopa/dx/tree/main/actions/keep-alive)，當 repo 超過 55 天沒有 commit 時自動推一筆空 commit，避免 GitHub 因 60 天閒置而停用排程。不需要額外設定，使用 GitHub 自動提供的 `GITHUB_TOKEN`。

### 本機執行（選用）

如果想直接在自己電腦上跑：

```
pip install -r requirements.txt
python main.py [你的 Wizardry ID]
```

需要 Chrome 瀏覽器以及對應版本的 Chrome webdriver。

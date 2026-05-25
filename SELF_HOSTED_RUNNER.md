# Self-Hosted GitHub Runner Setup

This project’s JP autocollector must run from a Japan IP. Use the Oracle VM as a self-hosted GitHub Actions runner for `.github/workflows/jp-autocollector.yml`.

## 1. Add Runner In GitHub

Open the repository in GitHub:

`Settings -> Actions -> Runners -> New self-hosted runner`

Choose:

- Runner image: `Linux`
- Architecture: `x64` for the current Oracle VM (`uname -m` shows `x86_64`)

GitHub will show a one-time `./config.sh --url ... --token ...` command. Keep that page open.

## 2. Prepare The VM

SSH into the VM:

```sh
ssh oc_gitrunner
```

Create and enter the runner directory:

```sh
mkdir -p ~/actions-runner
cd ~/actions-runner
```

Download and unpack the runner. Use the latest version shown by GitHub if it differs:

```sh
curl -L -o actions-runner-linux-x64-2.334.0.tar.gz \
  https://github.com/actions/runner/releases/download/v2.334.0/actions-runner-linux-x64-2.334.0.tar.gz
tar xzf actions-runner-linux-x64-2.334.0.tar.gz
sudo ./bin/installdependencies.sh || true
```

Oracle Linux may warn about `lttng-ust`; continue and test the runner.

### Cloud-Init Option

For a new Oracle VM, you can paste [cloud-init/oci-github-runner.yml](cloud-init/oci-github-runner.yml) into the instance's cloud-init/user-data field. It installs base packages, downloads the GitHub runner into `/home/opc/actions-runner`, and adds the pre-run reboot cron.

The template does not clone this repository. The GitHub Actions workflow is responsible for checkout via:

```yaml
- uses: actions/checkout@v6
```

By default, the template does not register the runner because GitHub runner registration tokens are short-lived. After boot, finish registration manually:

```sh
ssh oc_gitrunner
cd ~/actions-runner
./config.sh --url https://github.com/exkuretrol/wizardry-daphne-store-autocollector --token YOUR_TOKEN
sudo ./svc.sh install opc
sudo ./svc.sh start
```

If you want one-shot automated registration, edit the template before boot and set `RUNNER_TOKEN=""` to a fresh token from GitHub. Do not store long-lived credentials in cloud-init.

## 3. Register And Install Service

Run GitHub’s generated config command from the runner directory:

```sh
./config.sh --url https://github.com/exkuretrol/wizardry-daphne-store-autocollector --token YOUR_TOKEN
```

Accept default labels. The workflow targets:

```yaml
runs-on: [self-hosted, linux]
```

Install and start the service:

```sh
sudo ./svc.sh install opc
sudo ./svc.sh start
sudo ./svc.sh status
```

On Oracle Linux with SELinux enforcing, systemd may fail with `status=203/EXEC` and `Permission denied` for `/home/opc/actions-runner/runsvc.sh`. Fix the runner tree label and restart:

```sh
sudo chcon -R -t bin_t /home/opc/actions-runner
sudo systemctl restart actions.runner.exkuretrol-wizardry-daphne-store-autocollector.primary.service
sudo systemctl status actions.runner.exkuretrol-wizardry-daphne-store-autocollector.primary.service --no-pager
```

## 4. Add Repository Secrets

In GitHub:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Add:

```text
WIZARDRY_JP_EMAIL
WIZARDRY_JP_PASSWORD
```

The workflow passes secrets directly as environment variables, so passwords containing `$` are safe.

## 5. Test

In GitHub, run:

`Actions -> JP Webstore Autocollector -> Run workflow`

Or manually on the VM:

```sh
cd /root/wizardry-daphne-store-autocollector
set -a; . ./.wvd_jp.env; set +a
timeout 240s nice -n 10 .venv/bin/python main_jp.py
```

Expected already-claimed result:

```text
Summary: {'VvQwG2KoMz82': 'already', 'D6Vj2rYxMjne': 'already'}
exit_code=0
```

## 6. Optional Pre-Run Reboot

On the Oracle VM, root cron can reboot the host one hour before the scheduled collector run. The workflow runs Monday 11:00 UTC, so reboot at Monday 10:00 UTC:

```sh
sudo sh -lc 'tmp=$(mktemp); crontab -l 2>/dev/null | grep -v "wvd-pre-run-reboot" > "$tmp" || true; echo "0 10 * * 1 /usr/sbin/reboot # wvd-pre-run-reboot" >> "$tmp"; crontab "$tmp"; rm -f "$tmp"'
```

Verify:

```sh
sudo crontab -l
```

Expected line:

```cron
0 10 * * 1 /usr/sbin/reboot # wvd-pre-run-reboot
```

## Security Notes

Do not enable this runner for untrusted pull requests. A self-hosted runner executes workflow code on the VM. Keep JP credentials only in GitHub Actions secrets or the root-only `.wvd_jp.env` file.

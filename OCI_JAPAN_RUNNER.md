# OCI Japan Runner SOP

[English | [繁體中文](OCI_JAPAN_RUNNER.zh-TW.md)]

This SOP creates an Oracle Cloud Free Tier VM in Japan and registers it as the GitHub Actions runner for `.github/workflows/jp-autocollector.yml`.

## 1. Create The Oracle VM

Use an Oracle Cloud Free Tier account and do not upgrade to Pay As You Go. A Free Tier account that is not upgraded cannot create paid resources after the trial, which is the safest no-surprise-cost setup. Oracle Always Free resources continue after the trial when they stay within Oracle's limits.

Create one Always Free instance:

- Region: Japan Osaka
- Shape: `VM.Standard.E2.1.Micro`
- Image: Oracle Linux, Always Free-eligible
- Boot volume: default size
- Public SSH access: enabled

If the Oracle account is already pinned to Japan Tokyo, create the same instance there. Do not spend time trying to create `VM.Standard.A1.Flex` for this runner. In 2026, Always Free A1.Flex capacity is usually unavailable in popular regions. Use `VM.Standard.E2.1.Micro` and swap.

## 2. Paste Cloud-Init

During instance creation, paste [cloud-init/oci-github-runner.yml](cloud-init/oci-github-runner.yml) into the Oracle Cloud cloud-init/user-data field.

The cloud-init script:

- installs base packages
- downloads the GitHub runner to `/home/opc/actions-runner`
- applies the Oracle Linux SELinux runner fix
- creates a persistent 2 GB `/swapfile`
- adds a Monday 10:00 UTC pre-run reboot cron

It does not clone this repository. The workflow checks out the repo with `actions/checkout@v6`.

After first boot, SSH in and confirm cloud-init finished:

```sh
ssh oc_gitrunner
sudo tail -n 80 /var/log/cloud-init-output.log
cat /root/wvd-runner-next-steps.txt
```

## 3. Register The GitHub Runner

In GitHub, open:

`Settings -> Actions -> Runners -> New self-hosted runner`

Select:

- Runner image: `Linux`
- Architecture: `x64`

Copy the generated `./config.sh --url ... --token ...` command.

Run it on the VM:

```sh
cd ~/actions-runner
./config.sh --url https://github.com/exkuretrol/wizardry-daphne-store-autocollector --token YOUR_TOKEN --labels oci,jp
```

Install and start the runner service:

```sh
sudo ./svc.sh install opc
sudo chcon -R -t bin_t /home/opc/actions-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

Expected status includes:

```text
Active: active (running)
Runner.Listener run --startuptype service
```

## 4. Add GitHub Secrets

In GitHub, open:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Add both secrets:

```text
WIZARDRY_JP_EMAIL
WIZARDRY_JP_PASSWORD
```

The workflow passes secrets directly as environment variables, so passwords containing `$` are safe.

## 5. Verify Runner Labels

The workflow targets:

```yaml
runs-on: [self-hosted, linux, oci, jp]
```

In GitHub, confirm the runner shows these labels:

```text
self-hosted
linux
oci
jp
```

## 6. Test The Workflow

Run the workflow manually:

`Actions -> Japan Webstore Autocollector -> Run workflow`

Expected successful already-claimed output:

```text
Summary: {'VvQwG2KoMz82': 'already', 'D6Vj2rYxMjne': 'already'}
exit_code=0
```

The workflow includes an `Ensure swap` step before launching Chromium.

## 7. Verify Reboot Cron

The VM should reboot every Monday at 10:00 UTC, one hour before the scheduled collector run at 11:00 UTC.

Verify:

```sh
sudo crontab -l
```

Expected line:

```cron
0 10 * * 1 /usr/sbin/reboot # wvd-pre-run-reboot
```

## Security Notes

Do not enable this self-hosted runner for untrusted pull requests. A self-hosted runner executes workflow code on the VM. Store JP credentials only in GitHub Actions secrets.

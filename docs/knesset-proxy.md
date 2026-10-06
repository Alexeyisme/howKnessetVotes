# Knesset geo-block and the proxy in Israel

## In one paragraph

The Knesset no longer answers computers outside Israel. Our site runs on a Hetzner server outside Israel
(`hkv-1`), so we rented a tiny $4/month server in Tel Aviv (Kamatera, `hkv-il-proxy`). When `hkv-1` fetches
new votes, the requests to the Knesset go through the Israeli server, so the Knesset sees an Israeli address and
answers normally. Everything else (the site, the database, the API, translations) still runs on `hkv-1`. The
Israeli server stores nothing and does one job: it relays traffic to `knesset.gov.il`.

If the Israeli server disappeared, the site would stay up and keep showing the data it has. Only **new** votes
would stop arriving, and the Telegram alert would say the Knesset is blocking us.

## Why this exists

Since about 20:05 Israel time on **2026-10-05**, every Knesset address (open data, the website API, the old
votes service) answers requests from outside Israel with a redirect to
`https://www.knesset.gov.il/maintenance-page-geo`. A check from 40 locations (check-host.net, 2026-10-06) got
through only from Israel. We don't know why the block started or how long it will last.

To see whether the block is still on, ask `hkv-1` to open the Knesset site directly, without the proxy:

```sh
ssh -i ~/.ssh/hkv_hetzner root@<hkv-1 address> \
  "curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://www.knesset.gov.il/"
# 303 https://www.knesset.gov.il/maintenance-page-geo  = still blocked, the proxy is needed
# 200                                                 = direct access works again (see "Undo" below)
```

## The pieces, in plain words

There are three moving parts. Each is a small background service that restarts itself if it stops.

1. **The proxy** (`knesset-proxy` on the Israeli server). A proxy is a middleman: you ask it "please connect
   me to X" and it opens the connection for you, from its own address. Ours is a short Python script,
   [scripts/knesset_proxy.py](../scripts/knesset_proxy.py), which agrees to connect **only** to
   `knesset.gov.il` and refuses everything else. It listens only inside the Israeli server (`127.0.0.1`, port
   8890), so nobody on the internet can talk to it.

2. **The tunnel** (`hkv-il-tunnel` on `hkv-1`). Since the proxy can't be reached from the internet, `hkv-1`
   reaches it through SSH, the same encrypted login you use to manage servers. The tunnel service keeps one
   SSH connection open from `hkv-1` to the Israeli server and makes the proxy appear on `hkv-1` at
   `172.18.0.1:8890`. That address is internal: only our own Docker containers on `hkv-1` can see it. If the
   connection drops, the service reconnects after 30 seconds.

3. **The setting** (`HKV_KNESSET_PROXY=http://172.18.0.1:8890` in `/srv/hkv/.env` on `hkv-1`). This tells our
   update code to use the proxy. The code ([src/hkv/sources/odata.py](../src/hkv/sources/odata.py)) uses it
   **only** for `knesset.gov.il`; Wikidata and the Claude API (title translation) still go direct. If the
   setting is removed or empty, the code goes direct to the Knesset as before.

## What happens during one update

1. A timer on `hkv-1` starts an update: the full one (`hkv-update`) or the 10-minute quick check
   (`hkv-update-quick`). Each starts a fresh `updater` container, which reads `/srv/hkv/.env`.
2. The update code wants, say, `https://knesset.gov.il/Odata/...`. Because `HKV_KNESSET_PROXY` is set, it
   asks `172.18.0.1:8890` instead: "connect me to knesset.gov.il:443".
3. The tunnel carries that request over SSH to the Israeli server, where the proxy checks the name. It's
   `knesset.gov.il`, so the proxy opens the connection from its Israeli address. Any other name gets
   `403 Forbidden`.
4. The Knesset answers. The answer travels back the same way, still encrypted end to end (HTTPS): the
   Israeli server only passes bytes along and can't read or change them.
5. The update saves the new votes to the database on `hkv-1`, as before.

```text
hkv-1 (Hetzner, outside Israel)                         hkv-il-proxy (Kamatera, Tel Aviv)
┌──────────────────────────────────────┐                ┌──────────────────────────────────┐
│ updater container                    │                │                                  │
│   │ "connect me to knesset.gov.il"   │                │                                  │
│   ▼                                  │   SSH tunnel   │                                  │
│ 172.18.0.1:8890 ─ hkv-il-tunnel ─────┼───────────────►│ 127.0.0.1:8890  knesset-proxy    │
│                                      │  (encrypted)   │   │ only knesset.gov.il:443      │
│ Wikidata, Claude API: direct         │                │   ▼                              │
└──────────────────────────────────────┘                └── knesset.gov.il (sees an Israeli address)
```

## Why this is safe

- The Israeli server has one open port to the internet: SSH (22). Password login is off, so only our key
  gets in.
- The tunnel uses its own key and its own user, `tunnel`, which can't log in or run commands (its shell is
  `/usr/sbin/nologin`). That key may only forward to the proxy (`permitopen="127.0.0.1:8890"`). So even if
  `hkv-1` were broken into, this key would reach nothing but the Knesset.
- The proxy relays only to `knesset.gov.il`, so it can't be used as a free relay to the rest of the internet.
- Nothing secret is stored on the Israeli server. Database, API keys and `.env` stay on `hkv-1`.
- Ubuntu installs security updates on it automatically.

## Where everything is

| What | Where |
|---|---|
| Israeli server | Kamatera account, server `hkv-il-proxy`, <il-proxy address>, datacenter IL-TA (Tel Aviv). 1 vCPU, 1 GB RAM, 20 GB disk, Ubuntu 24.04, monthly plan, $4/month |
| Logging in to it | `ssh -i ~/.ssh/hkv_hetzner root@<il-proxy address>` (same key as `hkv-1`) |
| Its root password | Only for the Kamatera web console (an emergency screen in the browser). It is in your macOS Keychain under "hkv-il-proxy root". SSH doesn't use it |
| Kamatera from the command line | `cloudcli` on your Mac; its login is in `~/.cloudcli.yaml` (you entered it with `cloudcli init`) |
| Proxy script | [scripts/knesset_proxy.py](../scripts/knesset_proxy.py) in the repo; installed copy at `/usr/local/bin/knesset_proxy.py` on the Israeli server |
| Proxy service | [infra/il/knesset-proxy.service](../infra/il/knesset-proxy.service); installed at `/etc/systemd/system/` on the Israeli server |
| Tunnel service | [infra/systemd/hkv-il-tunnel.service](../infra/systemd/hkv-il-tunnel.service); installed on `hkv-1`, runs as user `deploy` |
| Tunnel key | `/home/deploy/.ssh/hkv_il_tunnel` on `hkv-1`; its public half is in `/home/tunnel/.ssh/authorized_keys` on the Israeli server |
| Israeli server's identity | Pinned in `/home/deploy/.ssh/known_hosts` on `hkv-1`, so the tunnel won't connect to an impostor |
| The setting | `HKV_KNESSET_PROXY` in `/srv/hkv/.env` on `hkv-1`, passed to the `updater` container by `infra/compose.prod.yaml` |
| SSH settings | `/etc/ssh/sshd_config` on the Israeli server (Kamatera's image doesn't read `sshd_config.d`); the original is saved as `sshd_config.kamatera-orig` |

## How much we ask the Knesset

All requests go one at a time with a pause between them (at most about 40 a minute). Measured on 2026-10-06:

| Run | When | Knesset requests |
|---|---|---|
| Full update (`hkv-update`) | daily 05:30; every 2 h on sitting days (Mon–Wed afternoons, Tue–Thu nights) | about 130 with reference data (MKs, factions, government posts); without it, 1 if there are no new votes |
| Quick check (`hkv-update-quick`) | every 10 minutes during sittings | 1 when nothing is new |

In a recess (no vote for 14 days) only the 05:30 run reloads reference data; on sitting days every full run does,
so new MKs are known before their votes. That is roughly 1,200 requests a week in a recess and 3,900 in a sitting
week. The Knesset has only throttled us after hours of non-stop history loading. If it throttles (HTTP 429/481)
the code backs off and retries; if it blocks us, the code stops at once and does not retry.

Please don't use the proxy for history loads (`hkv backfill`, `hkv legacy`) unless you need to. The Knesset
throttles heavy users, and this is our only Israeli address.

## If something looks wrong

Usually you'll notice through a Telegram alert that the update failed. Run this one check from your Mac. It
shows all three pieces and the latest update:

```sh
ssh -i ~/.ssh/hkv_hetzner root@<hkv-1 address> 'echo "tunnel: $(systemctl is-active hkv-il-tunnel)";
  echo "setting: $(grep -c "^HKV_KNESSET_PROXY=" /srv/hkv/.env)"; journalctl -u hkv-update -n 3 --no-pager -o cat'
ssh -i ~/.ssh/hkv_hetzner root@<il-proxy address> 'echo "proxy: $(systemctl is-active knesset-proxy)";
  journalctl -u knesset-proxy -n 5 --no-pager -o cat'
```

When everything is healthy you'll see `tunnel: active`, `setting: 1` and `proxy: active`, the update log
ends with `hkv.update done: N votes in window`, and the proxy log has recent `tunnel knesset.gov.il:443` lines.
If an update is running right now, the log ends with a progress line instead (e.g. `hkv.update reference data`);
wait a few minutes and check again.

To rerun an update by hand after a fix: `ssh -i ~/.ssh/hkv_hetzner root@<hkv-1 address> 'systemctl start hkv-update'`.

| What you see | What it means | What to do |
|---|---|---|
| Update log: `redirected to …maintenance-page-geo` | The update went direct, not through the proxy | Check `setting:` is 1. If it's 0, add `HKV_KNESSET_PROXY=http://172.18.0.1:8890` to `/srv/hkv/.env`; the next run picks it up |
| Update log: `Connection refused` to 172.18.0.1:8890; `tunnel:` not `active` | The tunnel is down | `journalctl -u hkv-il-tunnel -n 20` on `hkv-1` shows why. It retries every 30 s; it can't connect while the Israeli server is off or unreachable (check it in the Kamatera console) |
| `Connection refused` but the tunnel is `active` | Docker gave its network a different address (e.g. after it was recreated) | `docker network inspect hkv_default` on `hkv-1` shows the gateway; put it in the unit and in `HKV_KNESSET_PROXY`, then `systemctl daemon-reload && systemctl restart hkv-il-tunnel` |
| Tunnel log: `Host key verification failed` | The Israeli server was reinstalled and has a new identity | Check its new key in the Kamatera console (`cat /etc/ssh/ssh_host_ed25519_key.pub`), then replace its line in `/home/deploy/.ssh/known_hosts` on `hkv-1` |
| Tunnel log: `Permission denied (publickey)` | The tunnel key is missing from the Israeli server | Restore the `authorized_keys` line (see "Rebuilding" below) |
| Update log: proxy answered `502`; `proxy:` active | The Israeli server can't reach the Knesset (the Knesset is down, or it now blocks this address too) | On the Israeli server: `curl -sI https://www.knesset.gov.il/` |
| Proxy log: `refused CONNECT …` for a Knesset host | The Knesset moved data to a domain outside `knesset.gov.il` | Add the domain to `ALLOWED` in `scripts/knesset_proxy.py`, copy it to `/usr/local/bin/` there, `systemctl restart knesset-proxy` |
| `ssh` to <il-proxy address> times out | The Israeli server is off, or Kamatera has a problem (e.g. billing) | Kamatera web console: power state, then the browser console with the root password from Keychain |

## Rebuilding the Israeli server

If it is lost, create a new Ubuntu server in Kamatera's IL-TA datacenter with the `~/.ssh/hkv_hetzner` key for
root, then from the repo:

```sh
IL=root@<new address>
scp -i ~/.ssh/hkv_hetzner scripts/knesset_proxy.py $IL:/usr/local/bin/
scp -i ~/.ssh/hkv_hetzner infra/il/knesset-proxy.service $IL:/etc/systemd/system/
ssh -i ~/.ssh/hkv_hetzner $IL 'chmod 755 /usr/local/bin/knesset_proxy.py && systemctl daemon-reload &&
  systemctl enable --now knesset-proxy && ufw allow 22/tcp && ufw --force enable &&
  useradd -m -s /usr/sbin/nologin tunnel && install -d -m 700 -o tunnel -g tunnel /home/tunnel/.ssh'
```

Then:

1. On the new server, put this one line in `/home/tunnel/.ssh/authorized_keys` (owner `tunnel`, mode 600):
   `restrict,port-forwarding,permitopen="127.0.0.1:8890"`, a space, then the contents of
   `/home/deploy/.ssh/hkv_il_tunnel.pub` from `hkv-1`.
2. Turn off SSH password login there (`PasswordAuthentication no` in `/etc/ssh/sshd_config`, then
   `systemctl restart ssh`).
3. Put the new address in [infra/systemd/hkv-il-tunnel.service](../infra/systemd/hkv-il-tunnel.service) and
   copy the unit to `/etc/systemd/system/` on `hkv-1`.
4. On `hkv-1`, pin the new server's key: `ssh-keyscan -t ed25519 <new address>` and check it against
   `/etc/ssh/ssh_host_ed25519_key.pub` on the new server, then replace the line in
   `/home/deploy/.ssh/known_hosts`.
5. `systemctl daemon-reload && systemctl restart hkv-il-tunnel` on `hkv-1`, then run the check above.
6. Update the address here and in `CLAUDE.md`.

## Undo

When direct access works again (see the check at the top), turn the proxy off:

```sh
ssh -i ~/.ssh/hkv_hetzner root@<hkv-1 address> 'sed -i "/^HKV_KNESSET_PROXY=/d" /srv/hkv/.env &&
  systemctl disable --now hkv-il-tunnel'
```

Updates go direct again from the next run. Then you can delete the Kamatera server in the Kamatera console, or
keep it for $4/month in case the block returns. Turning it back on means undoing those two steps.

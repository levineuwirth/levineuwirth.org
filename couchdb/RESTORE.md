# Restoring the LiveSync CouchDB

`tools/couchdb-backup.sh` writes one archive per night to
`/root/couchdb-backups/couchdb-<TS>.tar.gz` and to borg as `couchdb-<TS>`.
An archive holds everything a restore needs:

| File | What |
|---|---|
| `<db>.jsonl`, `manifest` | each vault's documents (couchbackup) and its document count |
| `security/<db>.json` | who may use the database |
| `users.json`, `users/*.json` | the scoped `org.couchdb.user:*` accounts, password hashes included |
| `server.json`, `node-config.json` | the server's uuid, version and effective configuration, including the cookie-auth secret |

The vaults also live on every device, so a restore is about the server,
its accounts and its identity, not about rescuing notes. Pause LiveSync on
the devices before starting, and resume one device at a time afterwards.

## The server's identity

A CouchDB server is its uuid plus its cookie-auth secret. The image's
entrypoint writes both into the container's own `local.d/docker.ini`, so a
recreated container (any image update) would come up as a different server
unless they are configured. `instance.ini`, mounted as
`local.d/20-instance.ini` by `couchdb/docker-compose.yml`, fixes them: the
entrypoint keeps a secret it finds in `local.d`, and CouchDB keeps a
configured uuid.

Create it once from the live server, before deploying a compose file that
mounts it (a missing file becomes a directory, and CouchDB will not start):

```bash
couchdb-backup.sh --instance-ini > /root/couchdb-server/instance.ini
chmod 600 /root/couchdb-server/instance.ini
```

`docker.ini` has a second lesson: CouchDB writes runtime configuration
changes (a LiveSync "fix" button, a `PUT /_node/_local/_config/…`) into the
*last* file in its chain, which is `docker.ini`, and its keys then override
`local.ini`. That is how a wildcard CORS origin survived the 2026-10-02
change to `local.ini`. After any restore or recreate, check the effective
configuration, not just the files (step 5 below).

## A. Same host, damaged or lost data

```bash
cd /root/couchdb-server
docker compose down
mv couchdb-data couchdb-data.broken-$(date -u +%Y%m%d)   # keep it until the restore is proven
docker compose up -d                                     # empty server, same identity (instance.ini)
couchdb-backup.sh --restore                              # newest archive; or give one explicitly
```

## B. A rebuilt host

1. Get the newest archive out of borg (environment as in
   `/etc/default/couchdb-backup`; the passphrase is in the password manager):

   ```bash
   cd /var/tmp
   borg list --short --last 1 --glob-archives 'couchdb-*'
   borg extract ::couchdb-<TS>          # writes root/couchdb-backups/couchdb-<TS>.tar.gz{,.sha256}
   ```

2. Put `couchdb/docker-compose.yml` and `couchdb/local.ini` in
   `/root/couchdb-server/`, and `server.env` from the password manager.
3. Recreate the identity from the archive, then start an empty server:

   ```bash
   couchdb-backup.sh --instance-ini /var/tmp/root/couchdb-backups/couchdb-<TS>.tar.gz > /root/couchdb-server/instance.ini
   chmod 600 /root/couchdb-server/instance.ini
   cd /root/couchdb-server && docker compose up -d
   ```

4. Restore: `couchdb-backup.sh --restore /var/tmp/root/couchdb-backups/couchdb-<TS>.tar.gz`.

## Either way, then

5. Check:
   - `--restore` itself checks that each database's document count matches
     the manifest, and that `_security` and every account read back as
     archived. It refuses a target whose databases already hold documents
     (`RESTORE_OVER=1` overrides).
   - The identity: `curl -su admin http://127.0.0.1:5984/` shows the uuid in
     the archive's `server.json`.
   - The effective CORS: `curl -su admin http://127.0.0.1:5984/_node/_local/_config/cors`
     shows exactly the three LiveSync origins of `local.ini`, and a request
     with a foreign `Origin` gets no `Access-Control-Allow-Origin` (W02).
6. Resume LiveSync on one device and check that it syncs. If it reports
   that the remote database was rebuilt, use its own recovery on that
   device, then bring in the others.
7. Remove `couchdb-data.broken-*` once the devices sync.

## Rehearsed

On 2026-10-02 the whole path ran against a production-like `couchdb:3.4.2`:
the repository's `local.ini` mounted; two vaults of 211 documents; two
scoped accounts with `_security` membership; an admin password containing
`" \ @ : /`.

1. Backup.
2. `--verify`.
3. `--instance-ini` from the live server and from the archive, compared
   byte for byte.
4. Container and data destroyed.
5. Rebuilt from the archive alone: `--instance-ini` from the archive, then
   `--restore`.

Results:
- Both accounts logged in with their original passwords and read both vaults.
- A wrong password got 401.
- uuid and secret were unchanged.
- A foreign Origin was not reflected.
- A second `--restore` over the restored server was refused.
- No curl invocation carried a password in its argv.

# Trino overlay for Docker Compose

Optional add-on that brings a single-node Trino with the KairosDB connector
into the ExaMon Compose stack. Trino stays a separate component: lifecycle,
upgrades, and tuning are decoupled from the core stack.

## Layout

- `../../../compose.trino.yml` — overlay file applied on top of `docker-compose.yml`.
- `catalog/examon_ts_timestamps.properties` — KairosDB catalog, mounted into Trino at `/etc/trino/catalog`.

The connector JAR is fetched at startup by a one-shot init service
(`trino-connector-init`) into a named volume (`trino_kairosdb_plugin`),
which is then mounted into Trino at `/usr/lib/trino/plugin/kairosdb`. The
JAR is downloaded once and cached in the volume across restarts.

## Usage

From the repository root, with the core stack already configured:

```bash
docker compose -f docker-compose.yml -f compose.trino.yml up -d
```

Trino is reachable on `http://localhost:8080`. Inside the Compose network
the catalog reaches KairosDB at `http://kairosdb:8083`.

To remove only the Trino overlay (keeping the core stack):

```bash
docker compose -f docker-compose.yml -f compose.trino.yml stop trino trino-connector-init
docker compose -f docker-compose.yml -f compose.trino.yml rm -f trino trino-connector-init
```

## Pin policy

- Trino image tag and connector version are pinned in `compose.trino.yml`.
- The Kubernetes overlay in `deploy/trino/values-examon.yaml` tracks the
  same pins; both files should move together on a connector or Trino bump.

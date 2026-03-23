# Multi-Environment Setup (UAT + Prod)

Run separate UAT and Prod instances of LinkCentral behind a single Caddy reverse proxy using path-based routing.

## Directory Layout

```
/opt/linkcentral/
  uat/                          # UAT instance
    app/
    scripts/
    config/
      connections.yaml          # UAT database connections
    data/
    .env                        # PORT=8001
  prod/                         # Prod instance
    app/
    scripts/
    config/
      connections.yaml          # Prod database connections
    data/
    .env                        # PORT=8000
  Caddyfile
```

Each instance has its own `config/`, `data/`, `scripts/`, and `.env`, so they are fully isolated.

## Caddyfile

```caddyfile
your.server.ip {
    tls internal

    handle_path /uat/* {
        reverse_proxy localhost:8001
    }

    handle_path /prod/* {
        reverse_proxy localhost:8000
    }
}
```

`handle_path` strips the prefix before proxying, so `/uat/ScriptLinkService.asmx` arrives at the UAT instance as `/ScriptLinkService.asmx`.

## systemd Units

### linkcentral-uat.service

```ini
[Unit]
Description=LinkCentral ScriptLink (UAT)
After=network.target

[Service]
Type=simple
User=linkcentral
WorkingDirectory=/opt/linkcentral/uat
ExecStart=/opt/linkcentral/uat/venv/bin/python -m app.main
Restart=on-failure
RestartSec=5

Environment=HOST=0.0.0.0
Environment=PORT=8001

[Install]
WantedBy=multi-user.target
```

### linkcentral-prod.service

```ini
[Unit]
Description=LinkCentral ScriptLink (Prod)
After=network.target

[Service]
Type=simple
User=linkcentral
WorkingDirectory=/opt/linkcentral/prod
ExecStart=/opt/linkcentral/prod/venv/bin/python -m app.main
Restart=on-failure
RestartSec=5

Environment=HOST=0.0.0.0
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
```

### Caddy

If Caddy is installed via package manager, it already has a systemd unit. Just place the Caddyfile at `/opt/linkcentral/Caddyfile` and override the config path:

```bash
sudo systemctl edit caddy
```

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/caddy run --config /opt/linkcentral/Caddyfile
```

Or if running Caddy standalone:

```ini
[Unit]
Description=Caddy Web Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/caddy run --config /opt/linkcentral/Caddyfile
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Setup Steps

1. Create the directory layout with two copies of LinkCentral:
   ```bash
   sudo mkdir -p /opt/linkcentral/{uat,prod}
   ```

2. Create a virtual environment and install dependencies in each:
   ```bash
   cd /opt/linkcentral/uat
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   deactivate

   cd /opt/linkcentral/prod
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   deactivate
   ```

3. Configure each instance's `.env` and `config/connections.yaml` to point to the appropriate databases

4. Place the Caddyfile at `/opt/linkcentral/Caddyfile`

5. Copy the unit files and enable all three services:
   ```bash
   sudo cp linkcentral-uat.service /etc/systemd/system/
   sudo cp linkcentral-prod.service /etc/systemd/system/

   sudo systemctl daemon-reload

   sudo systemctl enable --now linkcentral-uat
   sudo systemctl enable --now linkcentral-prod
   sudo systemctl enable --now caddy
   ```

6. Check status:
   ```bash
   sudo systemctl status linkcentral-uat linkcentral-prod caddy
   ```

## myAvatar Configuration

Configure ScriptLink URLs in myAvatar using the path prefix:

- **Prod:** `https://your.server.ip/prod/ScriptLinkService.asmx`
- **UAT:** `https://your.server.ip/uat/ScriptLinkService.asmx`

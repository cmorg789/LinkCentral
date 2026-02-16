# Windows Deployment

LinkCentral can run as a Windows service using [WinSW](https://github.com/winsw/winsw).

## Setup

1. Download `WinSW-x64.exe` from the [WinSW releases page](https://github.com/winsw/winsw/releases)
2. Copy the example XML configs from this directory to the project root:
   ```
   copy docs\windows\LinkCentral-Service.xml .
   copy docs\windows\Caddy-Service.xml .
   ```
3. Rename the WinSW executable to match each service XML:
   ```
   copy WinSW-x64.exe LinkCentral-Service.exe
   copy WinSW-x64.exe Caddy-Service.exe
   ```
4. Edit the XML files to match your environment (paths, ports, credentials, etc.)

## Configuration

Environment variables can be set in the service XML or in a `.env` file. Uncomment the `<env>` block in the XML to use service-level environment variables:

```xml
<!-- <env name="SECRET_KEY" value="your_secret_key_here"/> -->  <!-- Only needed if using password_encrypted -->
<env name="HOST" value="0.0.0.0"/>
<env name="PORT" value="8080"/>
```

## Managing Services

```bash
# Install
LinkCentral-Service.exe install

# Start / Stop
LinkCentral-Service.exe start
LinkCentral-Service.exe stop

# Uninstall
LinkCentral-Service.exe uninstall
```

## Services

### LinkCentral-Service.xml

The main application service. Runs `python -m app.main` using the project's virtual environment.

### Caddy-Service.xml

Optional reverse proxy using [Caddy](https://caddyserver.com/). Handles HTTPS termination and forwards requests to LinkCentral. Requires a `Caddyfile` in the project root.

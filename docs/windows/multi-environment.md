# Multi-Environment Setup (UAT + Prod)

Run separate UAT and Prod instances of LinkCentral behind a single Caddy reverse proxy using path-based routing.

## Directory Layout

```
linkcentral/
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
  caddy.exe
  Caddy-Service.exe             # WinSW exe for Caddy
  Caddy-Service.xml
  LinkCentral-UAT-Service.exe   # WinSW exe for UAT
  LinkCentral-UAT-Service.xml
  LinkCentral-Prod-Service.exe  # WinSW exe for Prod
  LinkCentral-Prod-Service.xml
```

Each instance has its own `config/`, `data/`, `scripts/`, and `.env`, so they are fully isolated.

## Caddyfile

```caddyfile
your.server.ip {
    tls internal
    log

    handle_path /uat/* {
        reverse_proxy localhost:8001 {
            header_up X-Forwarded-Prefix /uat
            header_up Host {host}
        }
    }

    handle_path /prod/* {
        reverse_proxy localhost:8000 {
            header_up X-Forwarded-Prefix /prod
            header_up Host {host}
        }
    }
}
```

`handle_path` strips the prefix before proxying, so `/uat/ScriptLinkService.asmx` arrives at the UAT instance as `/ScriptLinkService.asmx`.

The `X-Forwarded-Prefix` header tells LinkCentral which path prefix to include in the WSDL `soap:address`, so myAvatar sends subsequent requests through Caddy. The `Host` header ensures the WSDL uses the correct server IP.

## Service XMLs

### LinkCentral-UAT-Service.xml

```xml
<service>
  <id>LinkCentral-UAT</id>
  <name>LinkCentral ScriptLink (UAT)</name>
  <description>SOAP middleware for myAvatar ScriptLink API (UAT)</description>

  <executable>%BASE%\uat\venv\Scripts\python.exe</executable>
  <arguments>-m app.main</arguments>
  <workingdirectory>%BASE%\uat</workingdirectory>

  <env name="HOST" value="0.0.0.0"/>
  <env name="PORT" value="8001"/>

  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>5</keepFiles>
  </log>
  <logpath>%BASE%\uat\logs</logpath>

  <onfailure action="restart" delay="5 sec"/>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="restart" delay="30 sec"/>
</service>
```

### LinkCentral-Prod-Service.xml

```xml
<service>
  <id>LinkCentral-Prod</id>
  <name>LinkCentral ScriptLink (Prod)</name>
  <description>SOAP middleware for myAvatar ScriptLink API (Prod)</description>

  <executable>%BASE%\prod\venv\Scripts\python.exe</executable>
  <arguments>-m app.main</arguments>
  <workingdirectory>%BASE%\prod</workingdirectory>

  <env name="HOST" value="0.0.0.0"/>
  <env name="PORT" value="8000"/>

  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>5</keepFiles>
  </log>
  <logpath>%BASE%\prod\logs</logpath>

  <onfailure action="restart" delay="5 sec"/>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="restart" delay="30 sec"/>
</service>
```

### Caddy-Service.xml

```xml
<service>
  <id>Caddy</id>
  <name>Caddy Web Server</name>
  <description>Reverse proxy for LinkCentral</description>

  <executable>%BASE%\caddy.exe</executable>
  <arguments>run --config "%BASE%\Caddyfile"</arguments>

  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>5</keepFiles>
  </log>
  <logpath>%BASE%\logs</logpath>

  <onfailure action="restart" delay="5 sec"/>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="restart" delay="30 sec"/>
</service>
```

## Setup Steps

1. Create the directory layout with two copies of LinkCentral (`uat/` and `prod/`)

2. Create a virtual environment and install dependencies in each:
   ```
   cd uat
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   deactivate

   cd ..\prod
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   deactivate
   ```

3. Configure each instance's `.env` and `config/connections.yaml` to point to the appropriate databases

4. Place the Caddyfile, service XMLs, and WinSW exes in the parent `linkcentral/` directory

5. Download [WinSW](https://github.com/winsw/winsw/releases) and create a copy for each service:
   ```
   copy WinSW-x64.exe LinkCentral-UAT-Service.exe
   copy WinSW-x64.exe LinkCentral-Prod-Service.exe
   copy WinSW-x64.exe Caddy-Service.exe
   ```

6. Install and start all three services:
   ```
   LinkCentral-UAT-Service.exe install
   LinkCentral-Prod-Service.exe install
   Caddy-Service.exe install

   LinkCentral-UAT-Service.exe start
   LinkCentral-Prod-Service.exe start
   Caddy-Service.exe start
   ```

## myAvatar Configuration

Configure ScriptLink URLs in myAvatar using the path prefix:

- **Prod:** `https://your.server.ip/prod/ScriptLinkService.asmx`
- **UAT:** `https://your.server.ip/uat/ScriptLinkService.asmx`

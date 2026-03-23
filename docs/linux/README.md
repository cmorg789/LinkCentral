# Linux Deployment

LinkCentral can run as a systemd service on Linux.

## Setup

1. Install dependencies into a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a systemd unit file at `/etc/systemd/system/linkcentral.service`:
   ```ini
   [Unit]
   Description=LinkCentral ScriptLink Service
   After=network.target

   [Service]
   Type=simple
   User=linkcentral
   WorkingDirectory=/opt/linkcentral
   ExecStart=/opt/linkcentral/venv/bin/python -m app.main
   Restart=on-failure
   RestartSec=5

   # Environment variables (or use .env file in WorkingDirectory)
   Environment=HOST=0.0.0.0
   Environment=PORT=8000

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable linkcentral
   sudo systemctl start linkcentral
   ```

## Managing the Service

```bash
sudo systemctl start linkcentral
sudo systemctl stop linkcentral
sudo systemctl restart linkcentral
sudo systemctl status linkcentral

# View logs
journalctl -u linkcentral -f
```

# Eufy Robomow — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration for the **Eufy E15** and **E18** robotic lawn mowers.

Control and monitor your Eufy mower directly from Home Assistant over your local network, with cloud-synced settings pulled straight from your Eufy account — no extra tools or manual key extraction required.

---

## Features

| Entity | Type | Description |
|--------|------|-------------|
| Mower | `lawn_mower` | Start, pause, dock — with activity state (mowing / returning / docked / paused) |
| Battery | `sensor` | Battery level (%) |
| Mowed Area | `sensor` | Area covered in the current or last session |
| Progress | `sensor` | Return-to-base progress (%) |
| Network | `sensor` | WiFi / Cellular connection type |
| Cut Height | `number` | Blade height 25–75 mm, step 5 mm (local, instant) |
| Edge Distance | `number` | −15 to +15 cm — how far inside/outside the border wire the mower cuts |
| Pad Direction | `number` | Mowing path angle 0–359° |
| Travel Speed | `select` | Mower driving speed: slow / normal / fast |
| Blade Speed | `select` | Blade motor speed: slow / normal / fast |
| Path Distance | `select` | Lane spacing: 8 cm / 10 cm / 12 cm |

> **Cloud entities** (edge distance, pad direction, speeds, path distance) require your Eufy account credentials. They are polled every 5 minutes and written back via the Tuya mobile API.

---

## Prerequisites

- **Local network access** — the mower and Home Assistant must be on the same LAN (or the mower reachable via IP).
- **Eufy account** — required for cloud-managed settings. The same email/password you use in the Eufy Home app.
- HA **2024.1** or newer.

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add URL: `https://github.com/jnicolaes/eufy-robomow-ha` — category: **Integration**
3. Search for **Eufy Robomow** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/eufy_robomow/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

Go to **Settings → Devices & Services → Add Integration → Eufy Robomow**.

**Step 1 — Sign in:**
Enter your Eufy account email and password. The integration will automatically discover all your devices and fetch their local keys.

**Step 2 — Select mower:**
Pick your mower from the dropdown and enter its local IP address (find it in your router's DHCP table or the Eufy app's device info screen).

That's it — no external tools, no manual key extraction.

---

## How it works

- **Local polling** (every 30 s) via the [Tuya local protocol](https://github.com/jasonacox/tinytuya) for real-time status (battery, activity state, etc.).
- **Cloud polling** (every 5 min) via the Tuya mobile API for settings stored as protobuf blobs in DP154/DP155.
- **Writes** go directly to the cloud API and are immediately reflected in the Eufy app.

---

## Known limitations

- **Zone mowing** — the E15/E18 supports zone-specific settings in the app; this is not yet implemented.
- **Map display** — live GPS map is not yet supported.
- **Pad direction unit** — the app shows a rotary dial; the integration exposes it as 0–359°. Verify the degree → direction mapping matches your app if the direction appears off.

---

## Troubleshooting

- **Entities unavailable** — check that the IP address is correct and the mower is on WiFi (not cellular only).
- **Cloud settings not updating** — cloud data refreshes every 5 minutes; changes made in the Eufy app will appear after the next refresh cycle.
- Enable **debug logging** for detailed output:

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.eufy_robomow: debug
```

---

## Credits

Authentication and local-key discovery based on [eufy-clean-local-key-grabber](https://github.com/albaintor/eufy-clean-local-key-grabber).
Local protocol via [tinytuya](https://github.com/jasonacox/tinytuya).

# Eufy Robomow — Developer Notes

Forked from `jnicolaes/eufy-robomow-ha`. Goal: add zone-specific mowing support to the Eufy E18, keeping all real-time control local (no cloud required for start/pause/dock/zone).

---

## Architecture

```
Home Assistant
  └── EufyMowerCoordinator (coordinator.py)
        ├── tinytuya Device  ── TCP:6668 ── Eufy E18 (Tuya v3.5 local)
        └── EufyCloudClient  ── HTTPS    ── Eufy/Tuya cloud API (settings only)
```

**Local** (tinytuya, port 6668, every 30 s): battery, activity state, progress, cut height, area, time.  
**Cloud** (Tuya mobile API, every 5 min): edge distance, path distance, travel speed, blade speed, pad direction — all packed into a base64 protobuf blob at DP155.

---

## Key Files

| File | Role |
|------|------|
| `coordinator.py` | Polling hub. `async_send_command(dp, val)` for local writes. `async_set_cloud_setting(**kw)` for cloud writes. |
| `lawn_mower.py` | `LawnMowerEntity` — start/pause/dock. Activity derived from DP1 + DP2 + DP118. |
| `cloud.py` | `EufyCloudClient` — Eufy REST login → Tuya session → DP155 read/write. Hand-rolled protobuf encoder/decoder (no external proto dep). |
| `const.py` | All DPS numbers, command tuples, ranges, cloud key names. |
| `config_flow.py` | Two-step UI: cloud login → device select → IP entry. Auto-discovers `device_id` + `local_key`. |
| `select.py` | Travel speed / blade speed / path distance selectors (cloud-backed). |
| `number.py` | Cut height (local), edge distance, pad direction (cloud-backed). |
| `sensor.py` | Battery, mowed area, progress %, total time, network type. |

---

## DPS Map (Eufy E18 / E15, Tuya v3.5)

| DP | Direction | Type | Meaning |
|----|-----------|------|---------|
| 1 | R/W | bool | Task active — `True`=start, `False`=dock |
| 2 | R/W | bool | Paused — `True`=pause, `False`=resume |
| 8 | R | int | Battery % |
| 110 | R/W | int | Cut height mm (25–75, step 5) |
| 118 | R | int | Progress: 0=mowing, 5–99=returning, 100=docked |
| 125 | R | int | Total mow time (~6.6 s/unit) |
| 126 | R | int | Mowed area counter |
| 134 | R | str | Network: `"Wifi"` or `"Cellular"` |
| 155 | R/W (cloud) | str | Base64 protobuf: edge dist, path dist, speeds, pad direction |

**Unknown / TBD**: zone selection DPS, if it exists. Discovery requires MITM capture (see roadmap below).

---

## DP155 Protobuf Layout

```
field 1 (msg)  : const sub-msg {f1: 40}
field 2 (msg)  : travel speed   — empty=slow, {f1:1}=normal, {f1:2}=fast
field 3 (msg)  : edge distance  — {f1: mm} (signed int32, negative = beyond wire)
field 4 (msg)  : pad direction  — {f2:{f1: angle_deg}, f3: fixed, f5: fixed}
field 5 (msg)  : path distance  — {f1: mm}
field 6 (msg)  : blade speed    — empty=slow, {f1:1}=normal, {f1:2}=fast
field 7 (varint): mirrors path_mm
```

Encoding/decoding is in `cloud.py` without any external proto library.

---

## Activity State Logic

```
DP1 absent/False                        → DOCKED
DP1=True, DP2=True                      → PAUSED
DP1=True, DP2=False, DP118 < 5         → MOWING
DP1=True, DP2=False, DP118 5–99        → RETURNING
DP1=True, DP2=False, DP118 >= 100      → DOCKED
```

---

## Development Setup

```bash
# Install deps for local testing
pip install tinytuya requests cryptography

# Quick local poll test (replace with real values)
python3 - <<'EOF'
import tinytuya
d = tinytuya.Device("DEVICE_ID", "10.0.3.147", "LOCAL_KEY", version=3.5)
d.set_socketTimeout(5)
d.set_socketPersistent(False)
print(d.status())
EOF
```

Deploy to HA by copying (or symlinking) `custom_components/eufy_robomow/` into the HA `config/custom_components/` directory, then restart HA.

Enable debug logging in `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.eufy_robomow: debug
```

---

## Roadmap

### Phase 1 — Fix status update bug
After issuing a start command the mower state can get stuck on DOCKED.  
Root cause: the 30 s poll window may miss the DP1 transition.  
Fix: after `async_send_command` succeeds, add a short delay (~2 s) + second `async_request_refresh()`.

### Phase 2 — MITM zone protocol discovery
Zone control has no documented local DPS. Capture the Eufy app's traffic when starting a zone to find:
- What endpoint is called (Tuya cloud? `api.eufylife.com`? local?)
- Zone ID format (UUID, index, polygon coordinates?)
- Whether it's a new DPS write or a REST call

Setup: `mitmproxy` on a LAN host, phone WiFi proxy → mitmproxy, install CA cert.  
If the app uses cert pinning, patch the APK with `apk-mitm`.

### Phase 3 — Implement zone control
Depending on Phase 2 findings:

**Path A — new local DPS** (preferred): add DPS constant in `const.py`, `async_start_zone(zone_id)` in `coordinator.py`, zone selector `select` entity in `select.py`.

**Path B — cloud REST**: extend `EufyCloudClient` in `cloud.py` with `list_zones()` + `start_zone(zone_id)`. Cache zone list in coordinator. Add zone selector + HA service `eufy_robomow.start_zone`.

Either path: register a `eufy_robomow.start_zone` service so automations can trigger zone mowing by name.

### Phase 4 — HA service + automation support
```yaml
service: eufy_robomow.start_zone
data:
  zone_name: "Front Lawn"
```

---

## Mower Details

- **Model**: Eufy E18
- **Local IP**: 10.0.3.147 (static DHCP lease recommended)
- **Protocol**: Tuya v3.5, port 6668
- **Upstream repo**: https://github.com/jnicolaes/eufy-robomow-ha

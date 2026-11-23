# Building the firmware

Docker-based builds for UV-K1 / UV-K5 V3. Use `compile-firmware.sh` (preferred).
`compile-with-docker.sh` is a thin forwarder kept for compatibility.

## Prerequisites

- Docker Desktop or Docker Engine running
- Bash (macOS, Linux, WSL, or Git Bash on Windows)

```bash
cd /path/to/uv-k1-k5v3-firmware-custom
chmod +x compile-firmware.sh compile-app.sh
```

The first run builds the `uvk1-uvk5v3` image (slow once). Later runs reuse it.

## Compile firmware

```bash
./compile-firmware.sh [Preset] [extra CMake options...]
```

Default preset: **Fusion**.

| Preset | Description |
|--------|-------------|
| `Custom` | Manual / base feature set |
| `Fusion` | Main multiboot edition (default) |
| `Transfer` | Fusion variant |
| `FieldOps` | Fusion + Fox Hunt / Beacon / Rescue Ops |
| `Labs` | Fusion labs variant |
| `Max` | Fusion max feature set |
| `CW` | NR7Y CW edition (keyer, macros, CPO, …) |
| `All` | Builds Fusion, Transfer, FieldOps, Labs, Max |

### Examples

```bash
# Fusion (default)
./compile-firmware.sh
./compile-firmware.sh Fusion

# NR7Y CW edition
./compile-firmware.sh CW

# All release presets (not including CW)
./compile-firmware.sh All

# Extra CMake options
./compile-firmware.sh FieldOps -DENABLE_VOX=OFF
./compile-firmware.sh Fusion -DENABLE_FEAT_F4HWN_GAME=ON
./compile-firmware.sh Fusion -DSQL_TONE=600
```

### Outputs

| Preset | Binaries |
|--------|----------|
| Fusion | `build/Fusion/f4hwn.fusion.bin`, `build/Fusion/f4hwn.fusion.uf2` |
| CW | `build/CW/nr7y.cw.bin`, `build/CW/nr7y.cw.uf2` |
| others | `build/<Preset>/<target>.bin` and `.uf2` |

Flash/RAM usage is printed at the end of each successful build.

## Version number and splash screen

The welcome / flash screen line is:

```text
AUTHOR_STRING_2 + " " + DISPLAY_VERSION_STRING_2
```

Example: `NR7Y v6.1.0`

| CMake variable | Default (this fork) | Role |
|----------------|---------------------|------|
| `AUTHOR_STRING_2` | `NR7Y` | Author label next to the version |
| `VERSION_STRING_1` | `v0.22` | Secondary version line (where used) |
| `VERSION_STRING_2` | `v6.1.0` (from `default` preset) | Main version on splash / EEPROM |
| `EDITION_STRING` | e.g. `Fusion` / `F4HWN 6.1.0` (CW) | Edition name (separate from author+version) |
| `DEV` | off | Fusion only: appends ` Dev` on display and updates `archive/f4hwn.fusion.development.bin` |

`VERSION_STRING_2` is limited to **15 characters** (EEPROM field); longer values are truncated.

### Fusion with a custom version

```bash
# Change version only → still "NR7Y v6.1.1"
./compile-firmware.sh Fusion -DVERSION_STRING_2=v6.1.1

# Change both → e.g. "F4HWN v6.1.1"
./compile-firmware.sh Fusion \
  -DAUTHOR_STRING_2=F4HWN \
  -DVERSION_STRING_2=v6.1.1

# Full example
./compile-firmware.sh Fusion \
  -DVERSION_STRING_1=v0.22 \
  -DVERSION_STRING_2=v6.1.1 \
  -DEDITION_STRING=Fusion
```

### CW with a version / tag

```bash
./compile-firmware.sh CW -DVERSION_STRING_2=v6.1.1
```

(CI tags often pass `-DVERSION_STRING_2=${{ github.ref_name }}` for CW releases.)

### Development Fusion build

```bash
./compile-firmware.sh Fusion -DVERSION_STRING_2=v6.1.1 -DDEV=ON
```

Regular output stays in `build/Fusion/`. Publishing the updated archive file is a separate git step.

**Note:** Building Fusion does **not** clear `NR7Y` by itself. That string is the CMake default for `AUTHOR_STRING_2` in this fork. Override it with `-DAUTHOR_STRING_2=...` if you want a different splash author.

## Overlay apps (multiboot)

Companion to firmware builds. Apps land under `build/Apps/`.

```bash
./compile-app.sh All              # every App/apps/*/build.sh
./compile-app.sh aprsrx sstv      # selected apps
./compile-app.sh breakout
```

## Tips

- Host toolchain is not required; everything runs in Docker.
- On Windows Git Bash, the scripts set `MSYS_NO_PATHCONV=1` so Docker path mapping works.
- For a deeper feature overview, see [README.md](README.md).

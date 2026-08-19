# wayscreen

GTK3 popup with real-time sliders for display calibration via `wl-gammarelay` D-Bus — brightness, temperature, and gamma.

Designed as a Waybar click-to-open menu.

## Features

- **Brilho** — 0–100% → `wl-gammarelay Brightness`
- **Temperatura** — 1000–10000K → `wl-gammarelay Temperature`
- **Gamma** — 0.50–3.00 → `wl-gammarelay Gamma`
- Real-time updates during drag (`Gtk.Scale.value-changed`)
- Integrated calibration reference area (grayscale ramp, 50% gray, color bars)
- Undecorated, always-on-top window with close button
- Escape to dismiss

## Dependencies

- `python3-gi` (PyGObject + GTK3)
- `busctl` (systemd)
- `wl-gammarelay` (running as user service)

## Usage

```bash
./wayscreen
```

### Command-line interface

Sem abrir a UI, para scripts, keybinds e Waybar:

```bash
./wayscreen --status                # estado atual
./wayscreen --get temperature       # valor individual (brightness|temperature|gamma)
./wayscreen --set brightness=50     # escreve e imprime o novo estado
./wayscreen --set temperature=4000
./wayscreen --set gamma=1.2
```

Exemplo de keybind no Hyprland:

```ini
bind = SUPER, F5, exec, /path/to/wayscreen --set brightness=80
bind = SUPER, F6, exec, /path/to/wayscreen --status
```

### Persistência (autostart)

Para restaurar a última config na inicialização sem abrir a UI:

```bash
/path/to/wayscreen --apply
```

Adicione ao `exec-once` do Hyprland.

### Profiles

Perfis nomeados podem ser salvos/carregados pelo dropdown na UI.

### Waybar integration

Add to your `~/.config/waybar/config.jsonc`:

```jsonc
"custom/display": {
    "format": "󰍹",
    "on-click": "/path/to/wayscreen",
    "tooltip": false
}
```

## Data locations

- Config: `~/.config/wayscreen/config.json`
- Profiles: `~/.config/wayscreen/profiles/<name>.json`
- Override com `WAYSCREEN_CONFIG_DIR=/path` (útil para testes/portabilidade)

## Tests

```bash
python3 -m unittest discover -s tests -v
```

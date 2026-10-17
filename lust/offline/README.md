# Lust Offline

Lust Offline lets players appear offline to their friends. It is
[Deceive](https://github.com/molenzwiebel/Deceive) by molenzwiebel, renamed to
Lust and licensed, like Deceive, under the GNU GPL v3 (`src/LICENSE`). Lust
itself stays MIT; Lust Offline ships next to it as a separate program.

Changes from Deceive (all made by `build_offline.py`):

- Everything players see says Lust instead of Deceive.
- No welcome messages in chat, no tray balloon and no update prompt on start.
- Settings live in `%APPDATA%\Lust Offline`.

`src/` is the modified source of the shipped `LustOffline.exe`, as the GPL
requires. To rebuild from a newer Deceive:

```
git clone https://github.com/molenzwiebel/Deceive.git
python lust/offline/build_offline.py Deceive
```

Lust starts League through it (`overlay/launcher/lust_offline.py`). Players
switch between online and offline from the Lust Offline tray icon, or by
messaging the "Lust Active!" friend `online`, `offline` or `mobile`.

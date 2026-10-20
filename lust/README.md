# Lust on top of Rose

Lust is generated from [Rose](https://github.com/Alban1911/Rose) releases.
Everything that makes Lust different from Rose lives in this folder:

- `sync.py` rebuilds every file outside `.github/` and `lust/` from a Rose tag:
  Rose → Lust renaming, GitHub links pointed at this repo, the Pengu
  `core.dll` labels, then `overlay/` and the `EDITS` list.
- `overlay/` holds files copied as-is: Kai'Sa icons and the lobby reveal code.

`.github/workflows/rose-sync.yml` runs every 3 hours: when Rose has a release
Lust doesn't, it runs `sync.py`, tests, builds the installer and publishes
`vX.Y.Z` here. Installed copies of Lust then update themselves.

## Shipping Lust fixes between Rose releases

`lust_patch.txt` holds `<rose version> <patch>`, e.g. `1.4.9 2`: sync then
stamps Lust as 1.4.9.2, and the release workflow publishes `v1.4.9.2`, which
installed copies offer as an update. Raise the patch to ship a fix. A newer
Rose release builds as its own version again, without a patch number.

## Changing Lust

Edits made directly to Rose-derived files are overwritten by the next sync.
Put new files in `overlay/`, and changes to Rose files in `EDITS` in `sync.py`.

To check locally against a Rose tag:

```
git fetch --no-tags https://github.com/Alban1911/Rose.git refs/tags/1.4.9:refs/rose/1.4.9
python lust/sync.py refs/rose/1.4.9
git status   # should show only the changes you meant to make
```

## Client theme (LUST-Theme)

`overlay/Pengu Loader/plugins/LUST-Theme` is the MIT-licensed
[Elaina theme](https://github.com/Elaina69/Elaina-theme) renamed to Lust, built
by `theme/build_theme.py` from the release zip and the matching
`elaina-theme-data` npm package. The script swaps the remote data module
(tracking, cloud backup) for the stub in `theme/data`, replaces the Elaina
artwork with Lust's (`theme/art` holds the default wallpaper) and fails if any
"Elaina" is left. To move to a new Elaina release:

```
python lust/theme/build_theme.py ElainaV4.zip elaina-theme-data-X.Y.Z.tgz
```

## Appearing offline (Lust Offline)

`offline/` holds Lust Offline, a renamed Deceive (GPL-3.0) that Lust uses to
start League so players can appear offline. See `offline/README.md`.

## Lobby Reveal and reveal updates

Lobby Reveal follows [reveal](https://github.com/steele123/reveal) with its own
code. `.github/workflows/reveal-watch.yml` checks reveal daily and opens an issue
when it has changes past `reveal_version.txt`; port them, then update that file.

## When an automatic update fails

The workflow opens an issue and releases nothing. Usually Rose changed code
that an `EDITS` entry looks for: update that entry, push, then re-run the
workflow from the Actions tab.

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

## Changing Lust

Edits made directly to Rose-derived files are overwritten by the next sync.
Put new files in `overlay/`, and changes to Rose files in `EDITS` in `sync.py`.

To check locally against a Rose tag:

```
git fetch --no-tags https://github.com/Alban1911/Rose.git refs/tags/1.4.9:refs/rose/1.4.9
python lust/sync.py refs/rose/1.4.9
git status   # should show only the changes you meant to make
```

## When an automatic update fails

The workflow opens an issue and releases nothing. Usually Rose changed code
that an `EDITS` entry looks for: update that entry, push, then re-run the
workflow from the Actions tab.

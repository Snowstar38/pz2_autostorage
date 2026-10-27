# Autostorage 1.0

Store juveniles when they mature in Planet Zoo 2.

[Download the latest release](https://github.com/Snowstar38/pz2_autostorage/releases/latest). The release ZIP is for players; this repository contains the mod source, tests and build wrappers.

## Install

1. Close Planet Zoo 2 and extract the release ZIP.
2. Copy its `Autostorage` folder into `<Planet Zoo 2>\Win64\ovldata\`.
3. Launch the game, load your zoo, click the box-arrow launcher, choose habitat or exhibit groups, and click **Enable**.
4. Save your zoo to retain rules and the global Active/Paused setting.

**Pause** preserves rule choices. All/None affects all listed groups in the selected tab, across pages. Refresh discovers newly added groups. X closes the panel; Escape and camera controls remain native. To uninstall, close the game and remove `ovldata\Autostorage`. Back up saves first; local backups do not cover Franchise server state.

## Behavior and compatibility

Tested on Windows with Planet Zoo 2 **1.0.7.1031590 / Steam build 26164034**. Franchise habitat transfers, zoo/reserve/zoo returns and settings through a full restart were verified live. Wildlife reserves are excluded.

Habitats respond to fresh maturity events while Active; existing adults are not swept into storage. Exhibits move tracked juveniles when adulthood is detected. **Exhibit transfer logic is offline-tested; a live exhibit transfer has not yet been confirmed.** Hybrid exhibit animals with a habitat representation require manual transfer.

The mod accepts at most one storage request per five seconds. Full storage, a game refusal or failed validation pauses automation; resolve the issue and re-enable. There is no indefinite automatic retry, so missed mature animals may need manual storage. Transport delay means prevention of every inbreeding event is not guaranteed.

Rules and Active/Paused are stored in the zoo's normal save. A saved Active zoo resumes Active; a missing legacy flag defaults to Paused. Pending transfers are not saved. Habitat monitoring uses native maturity events rather than repeated whole-zoo scans. Initial load/Refresh and exhibit baselines still read animals; exhibit signals use bounded juvenile checks and a watched-juvenile fallback. Displayed counts are cached observations.

Native UI styles and images are referenced from the installed game, not distributed here. Unknown portraits are hidden. Compatibility identifiers in the Lua modules and serializer are intentionally stable.

## Build and test

The commands below were checked on Windows with **Python 3.14.4**, **Node.js 22.16.0** and Git. Players do not need these dependencies.

```powershell
git clone https://github.com/Snowstar38/pz2_autostorage.git
cd pz2_autostorage
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
git clone --no-checkout https://github.com/OpenNaja/cobra-tools.git .tools/cobra-tools
git -C .tools/cobra-tools checkout 2dd9d1445608d6171c1ec1f2333cefb4d81a1317
.\.venv\Scripts\python.exe tools/run_tests.py --node node
.\.venv\Scripts\python.exe tools/pz2_build_pack.py --cobra-tools .tools/cobra-tools --src src/Autostorage --out build --python .venv/Scripts/python.exe
```

Run cobra-tools as the external CLI shown above; do not install its package into this environment. Its upstream package metadata targets Python 3.11, while this plain-Lua build path is tested with the pinned CLI dependencies in `requirements-dev.txt`. No game extraction, luadec runtime, GUI package or proprietary asset is required to build this mod.

Output is `build/Autostorage`: `Manifest.xml`, `Main.ovl` and `UI/AutostorageUI.ovl`. The builder uses the Planet Coaster 2 container profile with the Planet Zoo 2 version flag, then extracts both archives again and compares every authored file with source. The test runner runs all Python checks and both Node UI checks; it fails if a dependency or check is missing. These harnesses do not replace live game testing.

The manifest UUID, integer pack version and serializer client must remain stable for saved settings. The database entry filename follows the manifest name. Do not install multiple copies of the same content pack.

## License and credits

Original Autostorage code is MIT-licensed; see [LICENSE](LICENSE). The boot/require-hook foundation and build wrappers derive from Mike's Studios' MIT PZ2ModdingKit; its exact notice is in [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt). Unlicensed mod implementation code was not copied.

[cobra-tools](https://github.com/OpenNaja/cobra-tools) is a separate GPL-licensed build dependency and is not vendored or relicensed here. Planet Zoo 2 code, assets and trademarks remain their owners' property; the MIT license grants no rights to them. This is an unofficial mod, not a Frontier release.

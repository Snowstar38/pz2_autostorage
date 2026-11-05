# Autostorage 1.2.1

Store maturing habitat juveniles and younger exhibit offspring in Planet Zoo 2.

[Download the latest release](https://github.com/Snowstar38/pz2_autostorage/releases/latest). The release ZIP is for players; this repository contains the mod source, tests and build wrappers.

## Install

1. Close Planet Zoo 2 and extract the release ZIP.
2. Copy its `Autostorage` folder into `<Planet Zoo 2>\Win64\ovldata\`.
3. Launch the game, load your zoo, click the box-arrow launcher, choose habitat or exhibit groups, and click **Enable**.
4. Save your zoo to retain rules and the global Active/Paused setting.

**Pause** preserves rule choices. The master checkbox enables or disables all listed groups in the selected tab, across pages; a mixed mark means some groups are enabled. Opening the launcher menu refreshes the list to discover newly added habitats and exhibits; Refresh also updates it manually. X closes the panel; Escape and camera controls remain native. To uninstall, close the game and remove `ovldata\Autostorage`. Back up saves first; local backups do not cover Franchise server state.

**Advanced** reveals two saved option columns, both off by default. Hover over their native icons for labels:

- **Males only:** apply automated offspring actions only to males, leaving females unchanged.
- **Contraception instead of storage:** enable contraception on eligible offspring and leave them in their enclosure. Combine with Males only to treat male offspring only.

Click either option's header icon to toggle that option for every group in the current tab, across all pages. If any group is off, the click turns them all on; if all are on, it turns them all off. Each group's enabled state and the other option stay as selected.

These options follow the same maturity/birth triggers as storage. Enabling them alone does not act on existing animals. A later exhibit birth checks the current population and may include older excess offspring, while preserving the oldest living male and female. Turning contraception mode off does not remove contraception already applied. Save the zoo to retain option changes; the master checkbox preserves them. Hiding Advanced also preserves the options and their effect.

## Behavior and compatibility

Tested on Windows with Planet Zoo 2 **1.0.7.1031590 / Steam build 26164034**. Franchise habitat transfers, zoo/reserve/zoo returns and settings through a full restart were verified live. Wildlife reserves are excluded.

Version 1.2 preserves Mike's QoL Toolbox 3.2.1's HUD initialization and loads both interfaces together when that mod is installed. Toolbox remains a separate download. Both hook orders pass regression checks and checks against the original Toolbox loader. Both interfaces were verified together in a loaded zoo: Toolbox's Species board and Kin planner populated the zoo's five habitats, and Autostorage's Advanced columns acknowledged both option changes. Both options also restored after saving and a full game restart. Opaque tooltip colors were verified live; the final tooltip sizing and punctuation adjustment passed automated checks but has not been visually rechecked in game. All four sex/action combinations pass automated tests. The user also confirmed a live male maturity test successfully applied contraception. Exhibit birth-triggered contraception has not been verified live; pregnancy established before processing is not prevented.

Habitats respond to fresh maturity events while Active; existing adults are not swept into storage. Exhibit birth events trigger a population check: retain the oldest living male and female of each species in the exhibit and store younger extras. Exact age in years determines retention, with stable animal ID breaking equal-age ties. Age changes alone never trigger exhibit transfers. **Exhibit transfer logic is offline-tested; a live exhibit transfer has not yet been confirmed.** Hybrid exhibit animals with a habitat representation require manual transfer.

The mod accepts at most one storage request per five seconds. Full storage or failed validation pauses automation; resolve the issue and re-enable. Animals that the game explicitly reports as not ready (including a temporary aging animation) are retried at five-second intervals, at most four attempts, with a twenty-second readiness window. Queued animals are revalidated before a later request; an animal that has become ready can still succeed after waiting behind other transfers. Persistent refusal pauses automation. Accepted transfers are never retried. Missed animals may need manual storage. Transport delay means prevention of every inbreeding event is not guaranteed.

Rules and Active/Paused are stored in the zoo's normal save. A saved Active zoo resumes Active; a missing legacy flag defaults to Paused. Pending transfers are not saved. Habitat monitoring uses native maturity events rather than repeated whole-zoo scans. Initial load/Refresh and exhibit baselines still read animals; exhibit births use bounded population checks. Displayed counts are cached observations. If a habitat animal's UI record is temporarily unavailable, the scan retries up to three times, at least a quarter-second apart. Persistently unavailable animals are omitted without automated action; a discovery warning suggests Refresh. This fix passed a regression with a different zoo population and delayed/missing records; the user also reported successful live zoo switching after installation.

The menu updates cached animal entries by identity, skips redraws for diagnostic counters, and leaves idle rule lists untouched. Accepted commands publish the updated state once processed. These optimizations and option-header bulk actions pass automated regression checks. After installing this build, the user independently loaded the zoo, selected options using the new header controls, and reported that the controls looked good. Performance measurements use synthetic work counts rather than live frame-rate benchmarks.

Native UI styles and images are referenced from the installed game, not distributed here. Unknown portraits are hidden.

The Guardian compatibility update hosts Guardian 1.2.3 through its shared HUD registry, using Guardian's separately installed scripts. Its actual loader passes checks in both load orders, including ready callbacks and HUD reloads. The original conflict was reproduced in a loaded zoo on game version **1.0.8.1033600**: Autostorage opened with saved rules, while Guardian's interface was missing. With the patch, both panels opened together: Autostorage retained its 21 enabled habitat rules and Guardian displayed populated status and counters while paused. This verifies HUD coexistence, not every animal action or the cause of every reported Autostorage failure.

Authored Lua, JavaScript, CSS and HUD filenames now use Autostorage. The native save-client identifier remains `BreederKeeperState` so existing zoo rules, Active/Paused state and advanced options remain readable; the content-pack UUID and save schema are also unchanged.

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

Output is `build/Autostorage`: `Manifest.xml`, `Main.ovl` and `UI/AutostorageUI.ovl`. The builder uses the Planet Coaster 2 container profile with the Planet Zoo 2 version flag, then extracts both archives again and compares every authored file with source. The test runner runs all Python checks and all four Node UI checks; it fails if a dependency or check is missing. These harnesses do not replace live game testing.

The manifest UUID, integer pack version and serializer client must remain stable for saved settings. The database entry filename follows the manifest name. Do not install multiple copies of the same content pack.

## License and credits

Original Autostorage code is MIT-licensed; see [LICENSE](LICENSE). The boot/require-hook foundation and build wrappers derive from Mike's Studios' MIT PZ2ModdingKit; its exact notice is in [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt). Unlicensed mod implementation code was not copied.

[cobra-tools](https://github.com/OpenNaja/cobra-tools) is a separate GPL-licensed build dependency and is not vendored or relicensed here. Planet Zoo 2 code, assets and trademarks remain their owners' property; the MIT license grants no rights to them. This is an unofficial mod, not a Frontier release.

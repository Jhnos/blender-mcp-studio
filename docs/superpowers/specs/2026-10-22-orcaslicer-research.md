# OrcaSlicer research (first-hand, via GitHub API; nothing downloaded or executed)
Pinned: tag v2.4.2 = commit 8500fcdccaa10b5099ac20d252af3a7c560046f1. Repo: https://github.com/OrcaSlicer/OrcaSlicer (main HEAD checked 2026-10-22: 14a1aa333b6d, 2026-10-21).
Source citation base: https://github.com/OrcaSlicer/OrcaSlicer/blob/v2.4.2/<path>

## 1. Latest stable release
- v2.4.2, published 2026-07-07T03:33:49Z, prerelease=false. https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.4.2
- macOS asset: NO separate arm64 asset. Only `OrcaSlicer_Mac_universal_V2.4.2.dmg`, 246088803 bytes,
  https://github.com/OrcaSlicer/OrcaSlicer/releases/download/v2.4.2/OrcaSlicer_Mac_universal_V2.4.2.dmg (universal = arm64+x86_64).
- Licence: AGPL-3.0 (SPDX AGPL-3.0; GitHub API `license.spdx_id`).
- Signing: evidence in .github/workflows/build_orca.yml @v2.4.2 (step "Sign app and notary"): `codesign --deep --force --options runtime --timestamp --entitlements ... --sign "$CERTIFICATE_ID"` on the .app and the DMG, then `xcrun notarytool submit ... --wait` and `xcrun stapler staple` on the DMG. Condition: repo == OrcaSlicer/OrcaSlicer and ref is main / belt-printer / release/*. Non-main refs get "Create DMG without notary". So the official pipeline is Developer ID signed + notarized + stapled (hardened runtime). UNVERIFIED for the actual v2.4.2 binary: I did not download it or run spctl/codesign -dv; no release-note statement found. Whether the v2.4.2 build ran from a release/* ref is not confirmed.

## 2. CLI
Source: src/libslic3r/PrintConfig.cpp @v2.4.2 (CLIActionsConfigDef l.10588, CLITransformConfigDef l.10743, CLIMiscConfigDef l.10864) and src/OrcaSlicer.cpp. Rule (Config.cpp ConfigOptionDef::cli_args, l.238-255): an option with empty `cli` is exposed as `--<key with _ replaced by ->`; so every option below is spelled with dashes.
| Your flag | Orca v2.4.2 | Evidence |
|---|---|---|
| --datadir <dir> | yes | PrintConfig l.10960 `datadir` |
| --debug <n> | yes, int; 0 fatal,1 error,2 warning,3 info,4 debug,5 trace | l.10971 |
| --load-settings "a.json;b.json" | yes (machine;process, `;`-separated) | l.10890, cli_params "setting1.json;setting2.json" |
| --load-filaments "a;b" | yes | l.10896 |
| --curr-bed-type <name> | yes, ordinary print option `curr_bed_type` (enum), auto-spelled --curr-bed-type. Prior art AFKFelix/orca-slicer-api passes it (slicing.service.ts l.109). | PrintConfig l.1080 |
| --arrange 0/1 | yes (0 disable, 1 enable, others auto); cli line commented out so default dash spelling | l.10780 |
| --orient 0/1 | yes, same | l.10819 |
| --slice 0 | yes: 0 all plates, i = plate i | l.10657 |
| --outputdir <dir> | yes | l.10965 |
| --export-3mf <name> | yes; OrcaSlicer.cpp l.6376 prefixes outputdir + "/" | l.10611 |
| --export-settings <file> | yes; writes m_print_config as project_settings JSON (OrcaSlicer.cpp l.5572-5576) | l.10729 |
Other options seen: --uptodate, --uptodate-settings, --uptodate-filaments, --load-defaultfila, --min-save, --mtcpp, --mstpp, --no-check, --skip-objects, --clone-objects, --downward-check, --load-assemble-list, --export-slicedata/--load-slicedata, --export-stl(s), --pipe, --logfile. On main (not v2.4.2) the tests also use --allow-rotations and --strict; AFKFelix also passes --allow-newer-file and --allow-multicolor-oneplate (UNVERIFIED which tag introduced these).
Differences vs Bambu CLI: (a) Orca's loader requires each settings JSON to have `type` (machine/process/filament) and `from` in {system,User,user}, else CLI_CONFIG_FILE_ERROR (OrcaSlicer.cpp l.1960-2000). (b) `inherits` is NOT resolved for --load-settings JSON (config.erase("inherits") is commented out l.2012; BBL-specific `profiles/BBL/{machine,process,filament}_full` lookups l.2053/2371/2412 only serve BBL 3mf input, and those *_full dirs are absent from the v2.4.2 tree), so keep flattening inherits. main-branch test test_cli_strict.sh says "Standalone presets: without inherits the CLI loads them as-is". (c) Orca adds result.json (see failure).
Failure reporting:
- Exit codes: macros in src/libslic3r/Utils.hpp: SUCCESS 0, INVALID_PARAMS -2, FILE_NOTFOUND -3, CONFIG_FILE_ERROR -5, EXPORT_3MF_ERROR -13, PROCESS_NOT_COMPATIBLE -17, NO_SUITABLE_OBJECTS -50, VALIDATE_ERROR -51, NO_SUITABLE_OBJECTS_AFTER_SKIP -60, FILAMENT_NOT_MATCH_BED_TYPE -61, SLICING_ERROR -100. main-branch tests/cli/*.sh note the shell sees them modulo 256 (-50 -> 206, -100 -> 156).
- result.json {return_code, error_string, plate_index, sliced_plates...}: in v2.4.2 record_exit_reson() body is inside `#if defined(__linux__)` (OrcaSlicer.cpp l.416-455) so macOS may not write it at v2.4.2. UNVERIFIED on macOS; AFKFelix's service reads it. Treat exit code + stderr as the macOS contract until tested.
- 3MF on failure: slicing errors call flush_and_exit(CLI_SLICING_ERROR) at l.6193/6291, before the export_project call at l.7058. So no 3MF is written on slice failure (code-reading, not run). An export failure itself exits -13.
- Not tested by running: no binary executed.

## 3. Profiles
- Repo layout @v2.4.2: resources/profiles/<Vendor>/{machine,process,filament}/*.json plus resources/profiles/<Vendor>.json index. Vendor dir for Creality is `Creality` (resources/profiles/Creality/, 1078 files; index Creality.json v02.03.02.75). BBL.json also bundled; BBL has 2537 files.
- Inside the macOS .app: bundled path is expected to be OrcaSlicer.app/Contents/Resources/profiles/<Vendor>/..., UNVERIFIED (searched utils.cpp resources_dir; no download allowed). A third-party cookbook says first-run copies live under ~/Library/Application Support/OrcaSlicer/system/<Vendor>/ (https://github.com/CapitanaIcoachai/orcaslicer-cli-cookbook, README).
- Keys: profiles use `type`, `name`, `inherits`, `from`:"system", `instantiation`:"true"/"false", `setting_id`, `compatible_printers`. Same `inherits`/`instantiation` as Bambu. Top-level `include` key: UNVERIFIED (content search for "include": matched 1732 files but the heads I read show none; likely text). Machine instance files vs `machine_model` files (e.g. `Creality K1.json`, type machine_model) which carry default_bed_type.
- IMPORTANT: the CLI name is the JSON `name`, not the filename, and compatibility is by `compatible_printers` name.
- BBL in Orca: yes, includes P2S: resources/profiles/BBL/machine/Bambu Lab P2S{,0.2,0.4,0.6,0.8 nozzle}.json (0.4: inherits fdm_bbl_3dp_001_common, default_print_profile "0.20mm Standard @BBL P2S", default_filament_profile "Bambu PLA Basic @BBL P2S"); process "0.20mm Standard @BBL P2S.json"; filaments "... @BBL P2S ..." exist; machine_model default_bed_type "Textured PEI Plate".
Creality leaves (0.4 nozzle), all under resources/profiles/Creality/. File name | JSON name | inherits:
| Model | machine file (name) | 0.20 Standard process file (name) | generic PLA filament file (name) |
|---|---|---|---|
| K1 | machine/Creality K1 (0.4 nozzle).json (same; inherits fdm_creality_common) | process/0.20mm Standard @Creality K1 (0.4 nozzle).json (same; inherits fdm_process_creality_common) | filament/Creality HF Generic PLA.json (compatible_printers lists K1 0.4). NOTE "Creality Generic PLA @K1-all" lists only K1C/K1 SE, NOT K1 |
| K1C | machine/Creality K1C 0.4 nozzle.json | process/0.20mm Standard @Creality K1C 0.4 nozzle.json (name "0.20mm Standard @Creality K1C") | filament/Generic PLA @K1C-all.json (inherits fdm_filament_pla) or "Creality Generic PLA @K1-all" |
| K1 Max | machine/Creality K1 Max (0.4 nozzle).json | process/0.20mm Standard @Creality K1Max (0.4 nozzle).json | filament/Creality HF Generic PLA.json (K1 Max 0.4 compatible) |
| K2 Plus | machine/Creality K2 Plus 0.4 nozzle.json | process/0.20mm Standard @Creality K2 Plus 0.4 nozzle.json | filament/Generic PLA @K2 Plus-all.json |
| Ender-3 V3 | machine/Creality Ender-3 V3 0.4 nozzle.json | process/0.20mm Standard @Creality Ender3V3 0.4 nozzle.json (name "0.20mm Standard @Creality Ender-3 V3"; inherits fdm_process_common_klipper) | filament/Creality Generic PLA @Ender-3V3-all.json |
| Ender-3 V3 KE | machine/Creality Ender-3 V3 KE 0.4 nozzle.json | process/0.20mm Standard @Creality Ender3V3KE.json | filament/Creality Generic PLA @Ender-3V3-all.json |
Each machine's default_print_profile/default_filament_profile fields exist but do not always match the above (K2 Plus default process is 0.16mm Optimal; K1/K1 Max default filament is "Creality HF Generic PLA"). Inherit chain depth is >1 (e.g. K1 machine -> fdm_creality_common -> fdm_machine_common), so a flattener is required.

## 4. Bed types
- curr_bed_type enum values @v2.4.2 (PrintConfig l.1080-1100): "Cool Plate", "Engineering Plate", "High Temp Plate", "Textured PEI Plate", "Textured Cool Plate", "Supertack Plate" (a "SuperTack Plate" spelling is special-cased at l.8036).
- Creality: machine_model files for K1, K1C, K1 Max, K2 Plus set default_bed_type "Textured PEI Plate"; Ender-3 V3 and Ender-3 V3 KE models set none. Creality machine instances set support_multi_bed_types "1" (K1, K1C, K1 Max, K2 Plus, Ender-3 V3; not KE, which has no such key). Creality filaments carry per-plate temps for cool/eng/hot/textured (fdm_filament_pla: all 60). I did not find a per-model restricted list of curr_bed_type values; "Textured PEI Plate" is the safe value for the K1 family and K2 Plus. For Ender-3 V3 / KE the applicable plate is UNVERIFIED (no default declared; source has no restriction).

## 5. Prior art (queries run via `gh search repos`, 2026-10-22)
Queries: "orcaslicer headless in:readme,description"; "orcaslicer cli server in:readme,description"; "orca-slicer api slicing service in:readme,description"; "orcaslicer docker in:name,description"; "orcaslicer slice command line wrapper in:readme".
| repo | stars | last commit | licence | note |
|---|---|---|---|---|
| AFKFelix/orca-slicer-api | 78 | 2026-09-30 | AGPL-3.0 | REST API, execFile with --load-settings, --load-filaments, --curr-bed-type, --export-3mf, --slice, --arrange, --orient, --allow-newer-file, --outputdir; reads result.json on failure. Closest match. |
| DMontgomery40/mcp-3D-printer-server | 255 | 2026-10-20 | GPL-2.0 | MCP server, Orca/Bambu slicing |
| DMontgomery40/bambu-printer-mcp | 221 | 2026-10-20 (pushed) | ? | MCP, BambuStudio/Orca slicing |
| CapitanaIcoachai/orcaslicer-cli-cookbook | 3 | 2026-07-03 | MIT | macOS binary path /Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer; quirks: raft values must be strings, `machine;process` load order |
| 3DCreationsByChad/orca-auto | 2 | 2026-08-31 | MIT | batch headless slicing |
| mgomezdev/laminus | 0 | 2026-10-21 | none | Docker REST wrapping Orca CLI |
| linuxserver/docker-orcaslicer | 187 | 2026-10-20 (pushed) | ? | GUI-in-browser, not CLI |
Star counts are GitHub API values at query time.

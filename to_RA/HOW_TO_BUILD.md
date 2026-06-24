# How to (re)create this package

The whole `to_RA/` bundle is built by one script. From the repo root:

```bash
bash build_to_RA.sh
```

That copies the code, zips the data, and writes the checksums. It does not touch
the three hand-written docs (`README.md`, `MANIFEST.md`, this file), so edit
those by hand when the contents change.

## What the script does, step by step

1. **Make the folders** `to_RA/code/{02_parse,03_mappings,05_tables,06_figures,microdata-scripts}`, `to_RA/server_code_readonly`, `to_RA/outputs/tables`.
2. **Copy the aggregated pipeline code** (the commented `.py`/`.R` scripts that turn the parsed CSVs into the paper's tables and figures).
3. **Copy the read-only scripts**: the microdata.no `.mdata` extraction scripts and the individual-level secure-server pipeline (`analysis-indiv/scripts/*.R`). The RA reads these; they do not run off-platform.
4. **Copy the frozen mapping CSVs and the 9 LaTeX tables** the paper `\input`s.
5. **Zip the input data** into `to_RA/data_aggregated.zip` — the parsed cell-level CSVs and the two exposure-mapping CSVs, stored with their repo-relative paths so they extract back into place. This is the stable snapshot for the RA in case the live files change later.
6. **Write `CHECKSUMS.txt`**: SHA-256 of every bundled code/output file, of the frozen parsed inputs in the repo, and of the data zip.

## To extract the data snapshot

From the repo root:

```bash
unzip to_RA/data_aggregated.zip      # restores microdata-output/*.csv and data/ai_exposure/*.csv
```

## To verify the snapshot is intact

```bash
cd to_RA && shasum -c <(grep -A99 'Data snapshot' CHECKSUMS.txt | grep data_aggregated.zip)
```

## When the analysis changes

If a script, table, or input changes, rerun `bash build_to_RA.sh` to refresh the
copies, the zip, and the checksums. Then update `README.md`/`MANIFEST.md` if the
file list or the paper-to-code map changed.

## Adding the package to a new file list

If the set of input CSVs changes, edit the `zip` block in `build_to_RA.sh` to
list the new files, and update the "Frozen aggregated inputs" section of the
checksum block to match.

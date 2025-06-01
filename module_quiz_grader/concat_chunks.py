import pandas as pd, glob, pathlib

dfs = []
for csv in glob.glob("../chunks_processed/*_chunks.csv"):
    dfs.append(pd.read_csv(csv, encoding="utf-8"))
master = pd.concat(dfs, ignore_index=True)
out = pathlib.Path("../chunks_processed/all_chunks_processed.csv")
master.to_csv(out, index=False, encoding="utf-8")
print(f"Wrote {len(master)} rows to {out} (UTF-8)")

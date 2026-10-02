# A1 Provenance

Every json output (`lacunae.json`, `canaliculi_measurements.json`) now ends with a `provenance` block,
made by `lacunae.provenance()`:

| key | content |
|---|---|
| git_commit | `git rev-parse HEAD` of the repository, or null without git |
| git_dirty | true if tracked files differ from that commit (untracked files ignored), or null without git |
| versions | python, numpy, scipy, scikit-image, skan, networkx, pandas |
| config_hash | first 16 hex digits of SHA-256 over every upper-case setting in config.py except paths |
| config_hash_covers | the names of the settings in that hash |

No timestamps, so the same code on the same data writes the same file. `regression` ignores the block.

`requirements.txt` pins the installed versions of numpy, scipy, scikit-image, networkx, skan, openpyxl,
tifffile, imageio, pillow, matplotlib and pandas, with the Python version (3.9.10) in a comment.

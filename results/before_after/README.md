# Before and after

Whole-frame verification pictures that document one change each, so a rule can
be seen rather than read about. Each lacuna is outlined in its own colour and
drawn with the skeleton it owns; unowned skeleton is not drawn, and the
unattached dim tier is grey.

| pair | change |
|---|---|
| `<label>_before.png`, `<label>_after.png` | the four lacuna rules of METHODS section 9, which found lacunae the filters used to miss |
| `<label>_contact_before.png`, `<label>_contact_after.png` | the contact rule of METHODS section 8: a lacuna within `config.CONTACT_REACH_PX` of a thread owns it, with no signal test and before the shortest path assignment |
| `<label>_glow_before.png`, `<label>_glow_after.png`, and `_skeleton` beside each | the glow zone of METHODS section 18: inside each lacuna's own glow, a lower cut seeded from the mask the global cut already produced, because one global cut empties a ring around every body |

The contact pair is made with the pipeline's own picture, from two runs of the
same diagnostic, so nothing but the rule differs between them:

```
python src/diagnostics.py contact -i "data/WT/543_3.tif" -o OUT --tag contact_before \
    --contact-reach 0 --verification results/before_after
python src/diagnostics.py contact -i "data/WT/543_3.tif" -o OUT --tag contact_after \
    --verification results/before_after
```

`results/contact_census/pictures/` has the same comparison close up, around each
of the four lacunae the rule was opened on.

The glow pair is made the same way, from two runs that differ only in the rule:

```
python src/diagnostics.py glow-check -d data/WT -o results/glow_zone --pictures 543-2,543_3
```

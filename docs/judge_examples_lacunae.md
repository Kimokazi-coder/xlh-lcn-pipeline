<!--
Worked rules and examples for the AI lacuna judge (docs/EXPERIMENT_AI.md, "The
lacuna judge").

src/ai_judge.py loads whatever is OUTSIDE these html comments into the fixed
prompt, after the rules of src/judge_prompt_lacunae.md and before the image, on
every call for every image of every group. Everything inside a comment is
stripped before the prompt is built, so a note to the reader costs nothing. Both
files' sha256 go into every log record, so a changed set of rules or examples is
visible in the log for ever after.

The file holds the rules in words and no example drawn from an image. An
example added below is sent for every image of every group, so it has to be
written in words, with no image name, file path, mouse, genotype, diet or group
in it: the judge stays blind, and an example drawn from one group is shown to
the judge for all of them.

2026-11-09: the rules follow the working POL definition (docs/METHODS.md 24.0
and 29). Before, rule 3 also rejected "vessels and large saturated areas" and
"outlines that cut a body in pieces" in general; now only the four kinds of
rule 4 are rejected, and enlarged lacunae and clusters are kept.
-->

THE RULES, IN WORDS

**1. A lacuna is an osteocyte body:** a bright, dye-filled, compact or
irregular body in bone, often with fine processes.

**2. Enlarged lacunae are lacunae and must be kept.** An enlarged, irregular,
dye-filled lacunar space is the footprint of a periosteocytic lesion, which is
what the study measures. Size, irregular shape and bright filling are never a
reason to reject a body. Answer yes with reason "enlarged".

**3. Merged clusters are lacunae and must be kept.** An outline holding two or
more lacunae merged into one dye-filled space counts. Answer yes with reason
"cluster".

**4. Reject only these four:** a fragment (a speck, a crumb, or a small piece
split off a body another outline holds), a band piece (part of a bright sheet
or band along a bone surface), a tissue piece (soft tissue, a vessel, a diffuse
bright patch that is no cell body), and a saturated border piece (part of a
flat white saturated area at the edge of the tissue or of the picture).

**5. When in doubt between "enlarged lacuna" and "not a lacuna", look for a
body:** a bounded dye-filled space in bone, with bone around it and threads
leaving it, is a lacuna however large; a bright area with no boundary of its
own that continues along a surface or out of the picture is a band, tissue or
border piece.

<!--
Examples go below this comment, one per paragraph, in words.
-->

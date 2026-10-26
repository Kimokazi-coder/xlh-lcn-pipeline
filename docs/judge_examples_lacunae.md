<!--
Worked rules and examples for the AI lacuna judge (docs/EXPERIMENT_AI.md, "The
lacuna judge").

src/ai_judge.py loads whatever is OUTSIDE these html comments into the fixed
prompt, after the rules of src/judge_prompt_lacunae.md and before the image, on
every call for every image of every group. Everything inside a comment is
stripped before the prompt is built, so a note to the reader costs nothing. Both
files' sha256 go into every log record, so a changed set of rules or examples is
visible in the log for ever after.

The file starts with the rules of the brief in words and holds no example yet.
An example added below is sent for every image of every group, so it has to be
written in words, with no image name, file path, mouse, genotype, diet or group
in it: the judge stays blind, and an example drawn from one group is shown to
the judge for all of them.
-->

THE RULES, IN WORDS

**1. A lacuna is an osteocyte body:** a bright compact or irregular body in
bone, often with fine processes.

**2. Lacunae can be enlarged and irregular and still count.**

**3. Not lacunae:** bright sheets or bands along a bone surface, vessels and
large saturated areas, patches of soft tissue, tiny fragments or specks, and
outlines that cut a body in pieces.

<!--
Examples go below this comment, one per paragraph, in words.
-->

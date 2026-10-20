<!--
Worked rules and examples for the AI judge (branch exp-ai-layer,
docs/EXPERIMENT_AI.md).

src/ai_judge.py loads whatever is OUTSIDE these html comments into the fixed
prompt, after the rules of src/judge_prompt.md and before the case, on every
call for every image. Everything inside a comment is stripped before the prompt
is built, so a note to the reader costs nothing.

The three rules below are the ones the brief asks for in words. Karim adds
examples under them; nothing else is needed to make them take effect, and both
files' sha256 go into every log record, so a changed set of rules is visible in
the log for ever after.

Nothing here is sent anywhere other than to the judge, and no image name, file
path or genotype may be written here: the judge stays blind
(docs/EXPERIMENT_AI.md, "Privacy, keys and cost").
-->

THREE RULES THAT DECIDE MOST CASES

**1. A thread that visibly touches an osteocyte belongs to that osteocyte.**
If a numbered piece reaches the outline of a candidate body, it is that
candidate's. Nothing else in the picture outweighs that: not how faint the piece
is, not how far it runs afterwards, and not which cell the rest of the network it
joins belongs to. If it touches one candidate body, answer that candidate.

**2. A thread belongs to the osteocyte it starts from, even if it later joins a
network that another osteocyte also reaches.** Threads from different cells meet
and run on together; a shared network says nothing about where any one thread
began. Follow the numbered piece back towards the bodies and ask which candidate
it leaves: whose other threads it continues in line and in spacing, whose body it
points at, and which body it is nearer to at its own near end. That the other
candidate can be reached by going the long way round through the network is not
evidence, because that is the very thing the tracing program gets wrong and the
reason you are being asked.

**3. Not every dendrite belongs to an osteocyte, so "none" is a valid answer.**
A thread may enter the picture from a cell that is not in it, or run between two
cells without starting at either. When a real thread starts from neither
candidate, answer "none". It is the right answer and not a failure to decide: a
piece given to no cell keeps the decision the tracing program already made, and a
piece given to the wrong cell moves a cell's whole measured network. Prefer
"none" to a guess.

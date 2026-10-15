<!--
Worked examples for the AI judge (branch exp-ai-layer, docs/EXPERIMENT_AI.md).

This file is EMPTY on purpose. Karim writes the examples; src/ai_judge.py loads
whatever is here into the fixed prompt, after the rules and before the case, on
every call for every image.

Everything inside an html comment, like these lines, is stripped before the
prompt is built, so a file that holds only comments counts as no examples and
the prompt is then exactly the prompt in src/judge_prompt.md. Write the examples
as ordinary text outside the comment, one example per block, for instance:

  ## Example: a faint thread in the glow

  Segment 4 leaves the yellow body at its lower edge and runs 2 um into the
  glow, dimming as it goes but staying one continuous line of even width.
  real, owner yellow: a thread that touches the body is that cell's, and
  faintness inside the glow is expected.

  ## Example: glow texture

  Segments 11 to 14 are short, lie in a patch rather than a line, point in no
  consistent direction and do not reach any body. artifact: that is the grain
  of the glow, not a thread.

Nothing here is sent anywhere other than to the judge, and no image, file name
or genotype may be written here: the judge stays blind (docs/EXPERIMENT_AI.md,
"Blinding").
-->

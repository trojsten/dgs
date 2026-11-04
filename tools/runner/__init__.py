r"""
A warm interpreter for the build's Python steps.

Every recipe in this build shells out to `python -m something`, and **92 % of what that costs
is the interpreter coming up**: 445 ms of wall and 1.10 s of CPU to import `core.builder.jinja`
and the pint/numpy stack underneath it, against 53 ms to do the actual render once those are in
memory. A volume booklet runs about 320 such steps, so the startup alone is roughly 40 % of the
whole build's CPU.

`server.py` holds the imports once and forks per job; `client.py` is what the build actually
invokes, and imports nothing but `os`, `socket`, `struct` and `sys` so that it starts in 14 ms.

**Fork, not a reused worker.** The expensive state -- the pint registry at `core/builder/jinja.py`
module level, `core.i18n`'s thirteen parsed and schema-validated locales, Jinja's template caches
-- is shared copy-on-write and read only, while anything a job mutates (`sys.argv`, the working
directory, the environment, a global some builder sets) dies with the child. That is what
separates this from a Bazel-style persistent worker, where state leaking from one job into the
next is the standard failure and the reason such pools rot. The fork costs about 2 ms of the 53.
"""

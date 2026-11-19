# Azure Speech F0 candidate renderer (workbench only)

This is a local tool for an approved environment with direct access to the
user-authorized Azure Speech F0 resource. It does not change billing, verify
the account tier, bypass network policy, read saved credentials, or write to
GitHub. If the active environment cannot reach the approved provider, leave
the queue pending and continue offline work. Do not change providers or use a
paid tier. Do not place credentials in plans, command arguments, receipts or
Git; use the approved execution environment's secret injection.

Default is an offline dry run:

    python3 render.py resume-test01-q055.plan.json
    python3 -m unittest -q

Only after confirming the exact resource is F0, available, and approved for
the current synthesis batch, run in an environment already configured with
AZURE_SPEECH_REGION and AZURE_SPEECH_KEY:

    python3 render.py resume-test01-q055.plan.json --execute --confirmed-f0 --out /new/local/directory

A plan must be reviewed exact source text, order and locale, one to 16 items.
Use distinct output slugs; put spoken letters in one turn as A./B./C. or
A./B./C./D. when using optionCount 3 or 4. Use optionCount only for a spoken
choice list, not regular numbered stems. The renderer spacing preset is a
QA starting point; check actual pauses. The standard REST regional endpoint
does not accept a redirect with the credential. Requests are paced, and any
error stops the batch without a retry. A 429 by itself does not prove free
quota is exhausted. Render into a new directory and keep outputs local until
accepted. If resuming only enqueue missing clips, not prior successful ones.

The renderer requires complete RIFF bytes and all 24 kHz mono signed 16-bit PCM
samples; it will not write a truncated HTTP response just because its RIFF
header claims a full duration. A receipt gives exact output bytes/length/SHA,
not perceptual acceptance. Independently verify pronunciation, speaker and
option order, exact formal/practice timing and old-session preservation before
pushing accepted media. Do not push rejected WAVs or intermediate media.

The included Q055 one-stem plan matches the current source draft. The other
three clips for the Q053–055 group were independently checked in the prior
attempt; reuse them only if their exact local hashes match the scoped evidence.
If they are unavailable, rebuild the entire needed candidate from its
existing source draft and recheck all audio. The plan and six automated tests
were verified offline; no network call was made when adding this tool.

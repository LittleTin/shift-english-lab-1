# Test 01 Q098–100 candidate, original render (not publication approval)

Local offline inspection of Azure F0 WAVs. Audio never uploaded for QA. Suite reads exact SHA-bound sources decoded mono PCM at 16 kHz for recognizers; release WAVs untouched, input PCM checked separately. No human listening or browser acceptance. Results are corroboration, not a substitute for the project's final QA.

| Source | SHA-256 | Seconds | Decode assessment |
|---|---|---:|---|
| Shared courier passage | 55e8e0abae7ddc01fdc95128a9674b16578f59cdf0ced6947650e3e4d070fa68 | 37.2125 | Whisper small.en pass except hat→hut; Vosk correctly hears full closing idiom, with other errors. |
| Q98 formal stem | 398d75ff90824efb0a8b6b2b7265edaf4cbb438b3d7413d26275b16ea8428cd7 | 5.7625 | Whisper base.en + Vosk recover exactly (number/punctuation normalized); PocketSphinx recognizes number, misses gasket. |
| Q99 formal stem | 734566f8b2a9fe6b4de041e02c35691b63087ab5113180e8cb3ab7cc4918b7e5 | 6.0875 | Held: Whisper base+small van→ban, Vosk →banned, PocketSphinx →then; no approved pronunciation finding. |
| Q100 formal stem | 1f5ccdddde6ad77545c616ddb7eef1ea2a1b827f6eede8fbe6161f502ffffffd | 6.8 | Whisper base.en + Vosk recover exactly including the negative; PocketSphinx misses the negative. |

All 24 kHz mono signed LE 16-bit PCM. Passage max −3.6 dBFS, RMS −19.7, with 75 ms exact leading zero and 700.04 ms exact trailing zero. It is 1.4045 s longer than the former passage; root already demonstrated timing reallocation preserving speech and Part 4 pauses, so do not trim the speech.

Comparators: whisper.cpp v1.8.3 (2eeeba56e9edd762b4b38467bab96c2517163158) with verified model digests base.en SHA-1 137c40403d78fd54d454da0f9bd998f78703390c and small.en SHA-1 db8a495a91d927739e50b3fc1cc4c6b8f6c2d022, default no prompt; independent Vosk/Kaldi vosk-model-small-en-us-0.15 no phrase constraints; FFmpeg PocketSphinx f20ff1b7a5db64c5e892a798479e20df86e79a35 model with generic English LM no phrase constraints. Small.en recovers exact courier trial, both van contexts, staffed gate, closure/approval times, safety exception and order choices. Vosk recovers exact Q98/Q100 stems and full passage idiom. Punctuation, spacing, and numbers represented as words vs digits are normalization only.

The original Q099 has been superseded as a candidate only. See azure-q099-candidate-repair.json for the exact revised text, audio proof, and new timing. No question counted verified here.

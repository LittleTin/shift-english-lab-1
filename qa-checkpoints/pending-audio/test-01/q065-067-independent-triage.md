# Test01 Q065–067: g043 speech hold triage

Formal and practice use the identical original MP3 and 0.500–38.060 window:
`audio/azure-v1/test-01-23.mp3`, SHA-256
`b042994ee61657165e5416208d8885760019bf614f86db3ba4c4e7bfc11ef16c`.
The audio says all floating licenses are in use and restarting the server
would interrupt active simulations. These agree with Q065 and Q066. The
disputed adjective bearing directly on Q067 is still unresolved, so the shared
group is not called full PASS here.

Unprompted local full-source and word-level Whisper base.en (16 kHz mono
FFmpeg decode, no use of answer text, `-ojf` and `-ml 1 -sow -ojf`)
consistently offer `inused` for the script's `unused`. Full-source word
timing approximately 22.850–23.310 s; the sentence spans roughly 20.620–24.340
s. `inused` is not standard English, which raises a possible ASR confusion
but does not prove which vowel the recording contains.

The local reference scan found the same female voice en-US-JennyNeural
saying `in the training room` and `interrupt` in this recording, and
`under a tree` in Test03 practice g005. There is no verified same-voice
standalone `unused` or same-phonetic-context target elsewhere in the current
corpus. First-syllable formant sampling is confounded by neighboring
`the`/nasal and /j/ glide and by the near-homophonous reductions, so it
does not establish the disputed word. No second local acoustic model found.
Independent qualified listening or a known same-word voice comparison is
still needed. Keep raw audio local.

A second crop of the actual original PCM (20.400–25.550 s requested,
unprompted, atempo 0.72/0.94/1.22 for WAV, padded before ASR) returned
`end-used`, `inused`, and `in-use`, respectively. These inconsistent
guesses all leave lexical certainty insufficient, and 1.22× potentially
indicates the opposite meaning. Do not promote Q067 on semantic expectation;
ideally an independent human/recognizer distinguishes `unused` from
`in-use`, or an authorised rerender replaces the word/line.

# Complete-group practice-filter proof
The pre-release implementation chose individually matching items and then expanded to whole groups; this could silently return a different difficulty than requested. Test 03 has actual mixed-difficulty groups. This proof performs hard section/part/topic/difficulty eligibility at the complete-group level, keeps whole groups intact and separate by exam, and requires every listening voice label to match the selected accent. Unanswered priority ranks entirely new groups, partly answered groups, then seen groups; it does not silently split/dismiss siblings. The session title explains a shortfall.

From the workspace root:
```sh
D=shift-media-migration/practice-filter-proof
python3 "$D/make_patch.py" shift-qa/assets/app.js "$D/candidate-app.js" "$D/practice-filter.patch"
python3 shift-media-migration/resume-compat/make_patch.py "$D/candidate-app.js" "$D/combined-app.js"
node --check "$D/combined-app.js"
node "$D/test_filter.cjs" "$D/combined-app.js"
```

Five scoped logic tests pass, including with the resume prototype composed. Never present as a deployed or browser-accepted feature: the release candidate must include the final groups and pass real practice/locale/navigation smoke, plus the other authoritative release gates. The script and patch only apply to a known app structure and must be regenerated from the agreed candidate when it changes.

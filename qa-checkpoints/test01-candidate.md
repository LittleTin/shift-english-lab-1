# Test 01 candidate checkpoint

Not accepted or deployed. Reading and listening text review yielded revisions for 32 questions; answer letters remain unchanged. The archive preserves old IDs and two replaced illustrations. Actual spoken-audio acceptance and full compatibility acceptance are still outstanding.

Restore from work-branch commit 664920e88316145c1d208f69c37a0d77d2ad5862: from repository root run `gzip -dc qa-checkpoints/test01-candidate.patch.gz > /tmp/test01-candidate.patch`, verify SHA-256 `f95cf41680017675a1342078fd25ce50a69b57d48059aecd8b958ccbc4bedc10`, and then `git apply --check /tmp/test01-candidate.patch` before applying. This changes the source-JSON pack, display support for archived illustrations, and two SVG assets. Rebuild `data/test-01.js` using the JSON serializer in `tools/add_pack.py` and run the full checks before releasing. Do not include this draft checkpoint directory in production.

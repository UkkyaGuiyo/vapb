# First Human Unity 2022.3 Smoke Audit

The first compliant human-started run is complete and was audited locally.
The raw JSON remains private and is not part of Git.

Observed aggregate counts:

- 15 Prefabs
- 3041 observed components: 2716 Transform, 14 Animator, 311
  SkinnedMeshRenderer
- 102 unique mesh identities
- 490 material slots and 51 unique material identities
- 165 property modifications, all resolved by the public Prefab API

Derived counts independently matched the envelope. The observation also showed
that instance GUID/localFileID fields were empty for all records and that the
old checkpoint timestamp fields were identical. These are now treated as
explicit probe/checkpoint limitations, not silently normalized.

The smoke run does not prove Automatic Prefab correctness, whole-corpus
coverage, missing-texture semantic roles, or round-trip parity. The next probe
adds compact structural summaries and public Material texture-property facts;
the next human action is the corpus-folder run.

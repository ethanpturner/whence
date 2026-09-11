# Source

Copied from `huggingface.co/datasets/AwaisAdilKhokhar/lineagebench` at revision
`5f94189b3cd4922ac787df4e387f0c2622903b17` (dataset modified 2026-07-11), licence Apache-2.0.
Three of its five files are kept: `ground_truth.jsonl` (the fifteen suspects and their documented
parents), `parents.json` (the eight candidate parents), and `metrics.json` (the reference
implementation's pool sizes, used here only to check that the pairs were reconstructed correctly).
`reference_results.jsonl` is not copied: it is modelDNA's output, and this measurement is of a
different instrument. The labels are the dataset's; nothing here is authored.

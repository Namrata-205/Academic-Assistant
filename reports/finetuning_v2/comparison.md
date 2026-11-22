# Local fine-tuning development comparison

Actual GPU runs of Qwen3-0.6B. Synthetic draft training content; independent human review pending.

| Method | JSON valid | Source checked | Term present | Validation loss | Train seconds | Peak allocated GiB | Mean generation seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.000 | 0.000 | 0.000 | 0.901 | — | — | 7.746 |
| lora | 0.778 | 0.444 | 0.778 | 0.380 | 213.801 | 2.525 | 9.683 |
| qlora | 0.889 | 0.667 | 0.889 | 0.402 | 60.171 | 2.539 | 10.269 |
| full | 0.444 | 0.222 | 0.333 | 0.526 | 174.515 | 4.738 | 7.442 |

## Language-specific structural checks

| Method | English passes / model cases | Hindi passes / model cases | English latency seconds | Hindi latency seconds |
| --- | ---: | ---: | ---: | ---: |
| baseline | 0 / 4 | 0 / 5 | 5.883 | 9.236 |
| lora | 2 / 4 | 2 / 5 | 4.930 | 13.486 |
| qlora | 3 / 4 | 3 / 5 | 5.429 | 14.140 |
| full | 2 / 4 | 0 / 5 | 4.273 | 9.977 |

## Secondary Markdown-fence diagnostic

The base model often wraps JSON in Markdown. The primary contract requires raw JSON. To avoid treating wrapper compliance as mathematical improvement, the following post-hoc diagnostic removes only a single surrounding Markdown fence from every saved response. It does not repair JSON or content.

| Method | Normalized JSON passes | Normalized source-check passes |
| --- | ---: | ---: |
| baseline | 4 / 9 | 0 / 9 |
| lora | 7 / 9 | 4 / 9 |
| qlora | 8 / 9 | 6 / 9 |
| full | 4 / 9 | 2 / 9 |

## Parameters and saved artifacts

| Method | Trainable parameters | Trainable percent | Saved checkpoint MiB (including tokenizer) |
| --- | ---: | ---: | ---: |
| baseline | 0 | 0 | Base weights shared by all arms |
| lora | 5,046,272 | 0.840 | 34.45 |
| qlora | 5,046,272 | 0.840 | 34.45 |
| full | 596,049,920 | 100.000 | 1152.06 |

Rates are proportions from 0 to 1. 3 deterministic pipeline cases are not attributed to the model.

English and Hindi results, all raw responses, training details and prompt hashes are in the JSON files. The blind review sheet contains no method names; keep its key separate.

## Limits

- Small synthetic development experiment; all human content/support reviews pending.
- Brief one-paragraph generation, not a full teaching-quality or student-learning evaluation.
- The test questions are existing development cases, not a new independent final benchmark.
- Target concept families are excluded from training; textbook domain and model pretraining may overlap.
- Generator-only comparison: diagnosis and retrieved inputs are frozen, not retrained.
- One epoch and one seed with equal learning rate/budget; not separately tuned method optima.
- Full FT updates every BF16 model weight with an 8-bit optimizer to fit the 6 GB GPU; it is not adapter tuning.
- QLoRA trains on NF4 but is evaluated on BF16 base weights plus its adapter, so inference precision is controlled.
- Memory columns are PyTorch peak allocated bytes, not total physical GPU residency. Peak reserved allocator bytes are also recorded; Windows WDDM can use shared system memory.
- Latency is generation-only after one unscored warm-up; it excludes model loading, tokenization, retrieval and diagnosis.
- Source-checked rate is structural citation/evidence/arithmetic validation, not human mathematical accuracy.

## References

- Qwen model: https://huggingface.co/Qwen/Qwen3-0.6B
- PEFT quantization: https://huggingface.co/docs/peft/en/developer_guides/quantization
- bitsandbytes: https://huggingface.co/docs/bitsandbytes/installation

## Observed failure cases

| Method | Validator rejection reasons | Cases reaching output limit |
| --- | --- | --- |
| baseline | invalid_json: 9 | R02, R05, R08, R12 |
| lora | invalid_json: 2; Evidence is not present in cited text: 2; Incorrect angle measure assertion: 1 | R12 |
| qlora | Evidence is not present in cited text: 1; Incorrect angle measure assertion: 1; invalid_json: 1 | R12 |
| full | invalid_json: 5; Canonical technical term missing: 1; Evidence is not present in cited text: 1 | R02, R04, R07, R08, R12 |

These are parser/validator observations, not human correctness labels. In case R06, both adapter models output a Hindi assertion that a right angle measures 180 degrees; the angle-measure guard rejected it (a right angle is 90 degrees). The saved outputs and supporting passages should be reviewed together. R12 remains a failed Hindi digit-sum response in every arm. Do not deploy a method based only on the aggregate rates.

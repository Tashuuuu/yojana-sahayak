# Evaluation question format

`eval/eval_questions.jsonl` must contain exactly 40 JSON objects, one per line:

- 30 answerable questions and 10 unanswerable questions.
- Every answerable item must contain `qid`, `lang` (`hi` or `en`), `question`, `answerable: true`, `gold_scheme_id`, `gold_section`, and `reference_answer`.
- Every unanswerable item must contain `qid`, `lang`, `question`, and `answerable: false`. Set `gold_scheme_id` and `gold_section` to `null`; do not include a fabricated reference answer.
- Use the exact `scheme_id` and `section` values found in `data/schemes.jsonl`.
- Questions must be answerable from the official source records. Unanswerable examples must genuinely be absent from the supported corpus (not merely phrased differently from an available fact).

Example answerable record:

```json
{"qid":"Q01","lang":"en","question":"What is the documented benefit under EXAMPLE scheme?","answerable":true,"gold_scheme_id":"EXAMPLE","gold_section":"Benefits","reference_answer":"Copy or carefully summarize the official source fact here."}
```

Example unanswerable record:

```json
{"qid":"Q31","lang":"hi","question":"अगली किस्त किस तारीख को आएगी?","answerable":false,"gold_scheme_id":null,"gold_section":null,"reference_answer":""}
```

Do not use these examples as factual scheme content. Replace them with questions that match your final 20-scheme corpus.

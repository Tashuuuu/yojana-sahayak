# sentence-level groundedness check with a multilingual NLI model
import re

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

NLI_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
T_ENT = 0.60      # placeholder thresholds: tune on DEV labels on Monday, never on TEST
T_CON = 0.50
MAX_CHUNKS = 4    # how many retrieved chunks the verifier may read (same as k in retrieve)

_tok = None
_model = None
_id2label = None


def _load():
    """Load the NLI model the first time it is needed, then reuse it."""
    global _tok, _model, _id2label
    if _model is None:
        tok = AutoTokenizer.from_pretrained(NLI_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(NLI_NAME).eval()
        id2label = {int(i): name.lower() for i, name in model.config.id2label.items()}
        assert {"entailment", "neutral", "contradiction"} <= set(id2label.values()), id2label
        _tok, _model, _id2label = tok, model, id2label
    return _tok, _model, _id2label


def split_sentences(text: str) -> list[str]:
    """Split on . ! ? and the Hindi danda (।); drop fragments of 3 characters or fewer."""
    parts = re.split(r"(?<=[.!?।])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


@torch.no_grad()
def nli(premise: str, hypothesis: str) -> dict:
    """Return {'entailment': p, 'neutral': p, 'contradiction': p} for one premise/hypothesis pair."""
    tok, model, id2label = _load()
    enc = tok(premise, hypothesis, truncation="only_first", max_length=512, return_tensors="pt")
    probs = torch.softmax(model(**enc).logits, dim=-1)[0]
    return {id2label[i]: float(probs[i]) for i in range(len(probs))}


def verify_answer(answer: str, chunks: list[dict], lang: str,
                  t_ent: float = T_ENT, t_con: float = T_CON) -> dict:
    """Label each answer sentence Supported / Unsupported / Contradicted against the chunks."""
    # chunks in the answer's language first, then the rest; read at most MAX_CHUNKS
    same_ids = {c["chunk_id"] for c in chunks if c.get("lang") == lang}
    ordered = ([c for c in chunks if c["chunk_id"] in same_ids]
               + [c for c in chunks if c["chunk_id"] not in same_ids])
    use = ordered[:MAX_CHUNKS]

    results = []
    for sentence in split_sentences(answer):
        best_e, best_c, best_id = 0.0, 0.0, None
        for chunk in use:
            p = nli(chunk["text"], sentence)
            if p.get("entailment", 0.0) > best_e:
                best_e, best_id = p["entailment"], chunk["chunk_id"]
            best_c = max(best_c, p.get("contradiction", 0.0))

        if best_e >= t_ent:
            label = "Supported"
        elif best_c >= t_con:
            label = "Contradicted"
        else:
            label = "Unsupported"

        results.append({"text": sentence, "label": label, "entail": round(best_e, 3),
                        "contra": round(best_c, 3), "best_chunk_id": best_id})

    supported = sum(r["label"] == "Supported" for r in results)
    groundedness = supported / len(results) if results else 0.0
    return {"sentences": results, "groundedness": round(groundedness, 3)}
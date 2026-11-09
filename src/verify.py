"""Sentence-level multilingual NLI verification using mDeBERTa-v3."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
NLI_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
T_ENT = float(os.getenv("T_ENT", "0.60"))
T_CON = float(os.getenv("T_CON", "0.50"))
MAX_CHUNKS = 4
NLI_BATCH_SIZE = 16
_tokenizer = None
_model = None
_id2label = None


def resolve_id2label(raw_mapping: dict, num_labels: int = 3) -> dict[int, str]:
    """Resolve the exact checkpoint labels; its published order is 0=entailment,1=neutral,2=contradiction."""
    mapping = {int(index): str(label).lower() for index, label in raw_mapping.items()}
    required = {"entailment", "neutral", "contradiction"}
    if set(mapping.values()) == required:
        return mapping
    if num_labels == 3:
        # This fallback is specific to MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7.
        return {0: "entailment", 1: "neutral", 2: "contradiction"}
    raise RuntimeError(f"Unexpected NLI label mapping/output size: {mapping}, num_labels={num_labels}")


def _load():
    global _tokenizer, _model, _id2label
    if _model is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(NLI_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(NLI_NAME)
        model.eval()
        model.to("cpu")
        configured = resolve_id2label(model.config.id2label, model.config.num_labels)
        _tokenizer, _model, _id2label = tokenizer, model, configured
    return _tokenizer, _model, _id2label


def split_sentences(text: str) -> list[str]:
    """Split English/Hindi sentences without treating common abbreviations as endings."""
    if not text or not text.strip():
        return []
    marker = "\uE000"
    protected = re.sub(r"\b(Rs|Dr|Mr|Mrs|Ms|No)\.", lambda match: match.group(1) + marker,
                       text.strip(), flags=re.IGNORECASE)
    parts = re.split(r"(?<=[.!?।])\s+|\n+", protected)
    return [part.replace(marker, ".").strip() for part in parts if len(part.replace(marker, ".").strip()) > 3]


def premises_for(text: str) -> list[str]:
    sentences = split_sentences(text)
    candidates = [text.strip(), *sentences]
    candidates.extend(f"{left} {right}" for left, right in zip(sentences, sentences[1:]))
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def nli_batch(premises: list[str], hypothesis: str) -> list[dict[str, float]]:
    if not premises:
        return []
    import torch
    tokenizer, model, id2label = _load()
    encoded = tokenizer(
        premises, [hypothesis] * len(premises), truncation="only_first", max_length=512,
        padding=True, return_tensors="pt",
    )
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits, dim=-1).cpu()
    return [
        {id2label[index]: float(row[index]) for index in range(len(row))}
        for row in probabilities
    ]


def nli(premise: str, hypothesis: str) -> dict[str, float]:
    result = nli_batch([premise], hypothesis)
    return result[0] if result else {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0}


def verify_answer(answer: str, chunks: list[dict], lang: str,
                  t_ent: float = T_ENT, t_con: float = T_CON) -> dict[str, Any]:
    """Label every answer sentence; groundedness is the fraction labelled Supported."""
    sentences = split_sentences(answer)
    if not sentences:
        return {"sentences": [], "groundedness": 0.0}
    if not chunks:
        return {
            "sentences": [{"text": sentence, "label": "Unsupported", "entail": 0.0,
                           "contra": 0.0, "best_chunk_id": None} for sentence in sentences],
            "groundedness": 0.0,
        }

    ordered = sorted(chunks, key=lambda item: item.get("lang") != lang)
    selected = ordered[:MAX_CHUNKS]
    premise_records: list[tuple[str | None, str]] = []
    for chunk in selected:
        premise_records.extend((chunk.get("chunk_id"), premise)
                               for premise in premises_for(chunk.get("text", "")))

    results = []
    for sentence in sentences:
        best_entailment = 0.0
        best_contradiction = 0.0
        best_chunk_id = None
        for start in range(0, len(premise_records), NLI_BATCH_SIZE):
            batch = premise_records[start:start + NLI_BATCH_SIZE]
            scores = nli_batch([premise for _, premise in batch], sentence)
            for (chunk_id, _), score in zip(batch, scores):
                entailment = score.get("entailment", 0.0)
                contradiction = score.get("contradiction", 0.0)
                if entailment > best_entailment:
                    best_entailment = entailment
                    best_chunk_id = chunk_id
                best_contradiction = max(best_contradiction, contradiction)
        # A contradiction in any of the retrieved evidence must override a separate
        # entailment match; otherwise conflicting official text could be spoken as safe.
        if best_contradiction >= t_con:
            label = "Contradicted"
        elif best_entailment >= t_ent:
            label = "Supported"
        else:
            label = "Unsupported"
        results.append({
            "text": sentence, "label": label,
            "entail": round(best_entailment, 4),
            "contra": round(best_contradiction, 4),
            "best_chunk_id": best_chunk_id,
        })
    supported = sum(item["label"] == "Supported" for item in results)
    return {"sentences": results, "groundedness": round(supported / len(results), 4)}

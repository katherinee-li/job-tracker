"""Second pass: hand-picked slug guesses for companies the first probe missed."""

import json
from pathlib import Path

from find_boards import PROBES, count

OUT = Path(__file__).parent / "data" / "boards.json"

GUESSES = {
    "Skild AI": ["skild-ai", "skildrobotics", "skildai-1"],
    "Anduril": ["andurilindustries", "anduril-industries"],
    "Replicate": ["replicateai", "replicate-1"],
    "Groq": ["groqinc", "groq-inc"],
    "Weights & Biases": ["weightsbiases", "wandb-1", "weights-biases"],
    "Hugging Face": ["hugging-face", "huggingfaceinc"],
    "Glean": ["gleanwork", "glean-1", "askscio"],
    "Hebbia": ["hebbia-ai", "hebbiaai"],
    "Clay": ["clayhq", "clay-inc", "clayrun", "clay-2"],
    "Zipline": ["flyzipline", "zipline-1", "ziplineinternational"],
    "Applied Intuition": ["applied", "appliedintuition-1"],
    "Machina Labs": ["machinalabsinc", "machina"],
    "NVIDIA": ["nvidia-1", "nvidiacorp"],
}


def main():
    found = json.loads(OUT.read_text())
    for name, slugs in GUESSES.items():
        for slug in slugs:
            hit = next(((b, count(b, slug)) for b in PROBES if count(b, slug)), None)
            if hit:
                found[name] = {"board": hit[0], "slug": slug, "jobs": hit[1]}
                print(f"{name}: {hit[0]}/{slug} ({hit[1]})")
                break
        else:
            print(f"{name}: none")
    OUT.write_text(json.dumps(found, indent=2))


if __name__ == "__main__":
    main()

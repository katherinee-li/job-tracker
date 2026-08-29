"""Probe Greenhouse / Ashby / Lever for each target company's public job board."""

import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).parent / "data" / "boards.json"

COMPANIES = [
    "OpenAI", "Anthropic", "Cognition", "Fireworks AI", "Datadog", "Databricks",
    "Scale AI", "Palantir", "NVIDIA", "Physical Intelligence", "Skild AI", "Figure",
    "Waymo", "Anduril", "Stripe",
    "Together AI", "Baseten", "Modal", "Replicate", "Anyscale", "CoreWeave", "Groq",
    "Cerebras", "Lambda", "Weights & Biases", "Hugging Face", "LangChain", "LlamaIndex",
    "Pinecone", "Vercel", "Cloudflare", "Exa", "Perplexity",
    "Sierra", "Glean", "Harvey", "Decagon", "Hebbia", "Writer", "Abridge", "Mercor",
    "Clay", "Anysphere", "Replit", "ElevenLabs",
    "FieldAI", "Generalist", "Apptronik", "1X", "Sunday Robotics", "Dexterity",
    "Gecko Robotics", "Zipline", "Nuro", "Skydio", "Waabi", "Applied Intuition",
    "Machina Labs", "GrayMatter Robotics",
    "Google", "Meta", "Microsoft", "Amazon", "Apple", "Snowflake", "Tesla",
]

EXTRA_SLUGS = {
    "Fireworks AI": ["fireworks", "fireworksai"],
    "Scale AI": ["scaleai", "scale"],
    "Together AI": ["togetherai", "together"],
    "Weights & Biases": ["weightsandbiases", "wandb"],
    "Hugging Face": ["huggingface"],
    "Anysphere": ["cursor", "anysphere"],
    "Physical Intelligence": ["physicalintelligence", "physical-intelligence", "pi"],
    "Skild AI": ["skildai", "skild"],
    "FieldAI": ["fieldai", "field-ai"],
    "Applied Intuition": ["appliedintuition", "applied-intuition"],
    "Gecko Robotics": ["geckorobotics", "gecko-robotics"],
    "Machina Labs": ["machinalabs", "machina-labs"],
    "GrayMatter Robotics": ["graymatterrobotics", "graymatter-robotics"],
    "Sunday Robotics": ["sundayrobotics", "sunday"],
    "1X": ["1x", "1xtechnologies"],
    "LangChain": ["langchain"],
    "LlamaIndex": ["llamaindex", "runllama"],
    "Generalist": ["generalist", "generalistai"],
}

PROBES = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
}


def slugs(name):
    base = re.sub(r"[^a-z0-9]", "", name.lower())
    out = [base] + EXTRA_SLUGS.get(name, [])
    hyphen = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if hyphen != base:
        out.append(hyphen)
    return list(dict.fromkeys(out))


def count(board, slug):
    url = PROBES[board].format(slug)
    req = urllib.request.Request(url, headers={"User-Agent": "job-tracker"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=25).read())
    except Exception:  # noqa: BLE001
        return None
    jobs = data if isinstance(data, list) else data.get("jobs")
    if not jobs:
        return None
    return len(jobs)


def probe(name):
    for slug in slugs(name):
        for board in PROBES:
            n = count(board, slug)
            if n:
                return name, {"board": board, "slug": slug, "jobs": n}
    return name, None


def main():
    found, missing = {}, []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for name, hit in pool.map(probe, COMPANIES):
            if hit:
                found[name] = hit
                print(f"{name}: {hit['board']}/{hit['slug']} ({hit['jobs']})", flush=True)
            else:
                missing.append(name)
    OUT.write_text(json.dumps(found, indent=2))
    print(f"\nfound {len(found)}, missing {len(missing)}: {', '.join(missing)}", file=sys.stderr)


if __name__ == "__main__":
    main()

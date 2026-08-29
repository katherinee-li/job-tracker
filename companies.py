"""The company watchlist: who we check daily, and which tier they sit in."""

import json
import re
from pathlib import Path

BOARDS = json.loads((Path(__file__).parent / "data" / "boards.json").read_text())

TIERS = {
    "tier1": [
        "OpenAI", "Anthropic", "Cognition", "Fireworks AI", "Datadog", "Databricks",
        "Scale AI", "Palantir", "NVIDIA", "Physical Intelligence", "Skild AI", "Figure",
        "Waymo", "Anduril", "Stripe",
    ],
    "ai-infra": [
        "Together AI", "Baseten", "Modal", "Replicate", "Anyscale", "CoreWeave", "Groq",
        "Cerebras", "Lambda", "Weights & Biases", "Hugging Face", "LangChain",
        "LlamaIndex", "Pinecone", "Vercel", "Cloudflare", "Exa", "Perplexity",
    ],
    "agents": [
        "Sierra", "Glean", "Harvey", "Decagon", "Hebbia", "Writer", "Abridge", "Mercor",
        "Clay", "Anysphere", "Replit", "ElevenLabs",
    ],
    "robotics": [
        "Physical Intelligence", "Skild AI", "FieldAI", "Generalist", "Figure",
        "Apptronik", "1X", "Sunday Robotics", "Dexterity", "Gecko Robotics", "Zipline",
        "Nuro", "Skydio", "Waabi", "Applied Intuition", "Machina Labs",
        "GrayMatter Robotics", "Amazon Robotics", "Tesla",
    ],
    "big-tech": [
        "Google", "Meta", "Microsoft", "Amazon", "NVIDIA", "Apple", "Stripe", "Datadog",
        "Cloudflare", "Databricks", "Snowflake",
    ],
}

TIER_OF = {}
for tier, names in TIERS.items():
    for name in names:
        TIER_OF.setdefault(name, tier)

NAMES = list(TIER_OF)

ALIASES = {
    "anysphere": "Anysphere",
    "cursor": "Anysphere",
    "scale": "Scale AI",
    "scaleai": "Scale AI",
    "together": "Together AI",
    "togetherai": "Together AI",
    "fireworks": "Fireworks AI",
    "fireworksai": "Fireworks AI",
    "wandb": "Weights & Biases",
    "weightsandbiases": "Weights & Biases",
    "huggingface": "Hugging Face",
    "physicalintelligence": "Physical Intelligence",
    "skild": "Skild AI",
    "skildai": "Skild AI",
    "fieldai": "FieldAI",
    "nvidiacorporation": "NVIDIA",
    "amazonrobotics": "Amazon Robotics",
    "amazonwebservices": "Amazon",
    "aws": "Amazon",
    "googledeepmind": "Google",
    "deepmind": "Google",
    "metaplatforms": "Meta",
    "facebook": "Meta",
    "microsoftcorporation": "Microsoft",
    "appliedintuition": "Applied Intuition",
}

_NORM = {re.sub(r"[^a-z0-9]", "", n.lower()): n for n in NAMES}
_NORM.update(ALIASES)


def canonical(name):
    """Map a scraped company string onto the watchlist, or None if off-list."""
    key = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    return _NORM.get(key)


def tier_of(name):
    return TIER_OF.get(name, "other")

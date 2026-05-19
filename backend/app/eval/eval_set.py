"""Seed evaluation set for the GAIA Translator RAG pipeline.

A *gold* item is one that names the *expected* paper(s) a competent retriever
should surface for a given query. Gold is identified by *normalized title
substring* match (not paper_id) so the eval works regardless of which UUIDs
were assigned at ingest time.

Each item carries:
- query: the text to translate (mimics a real user input)
- source_discipline, target_discipline: passed through to the engine
- gold_title_substrings: list of lowercase substrings; a chunk is "gold" if
  its paper title contains any of them
- persona: optional dict matching the persona schema (used for personalization
  evals)

You can extend this set freely. Quality of evals scales with quality of gold.
"""

from typing import TypedDict


class GoldItem(TypedDict, total=False):
    id: str
    query: str
    source_discipline: str
    target_discipline: str
    gold_title_substrings: list[str]
    persona: dict
    notes: str


# Hand-curated seeds aligned to the 6 starter papers in README.md.
# These are intentionally specific so retrieval has a clear "right answer".
GOLD_SET: list[GoldItem] = [
    {
        "id": "shi-agro-1",
        "query": (
            "We're using ambient seismic noise to monitor soil moisture changes in "
            "agricultural fields. What does dv/v actually tell us about the "
            "near-surface hydrology, and what spatial resolution can we expect?"
        ),
        "source_discipline": "seismology",
        "target_discipline": "hydrology",
        "gold_title_substrings": ["agroseismology", "shi"],
        "notes": "Should retrieve Shi et al. agroseismology paper.",
    },
    {
        "id": "feng-velocity-1",
        "query": (
            "How does pore pressure change after a rainfall event affect seismic "
            "velocity in the top few meters of soil?"
        ),
        "source_discipline": "hydrology",
        "target_discipline": "seismology",
        "gold_title_substrings": ["feng", "near-surface seismic", "hydrological"],
    },
    {
        "id": "denolle-ambient-1",
        "query": (
            "I want to set up an ambient noise monitoring experiment for the "
            "critical zone — what processing pipeline and station spacing should I use?"
        ),
        "source_discipline": "seismology",
        "target_discipline": "hydrology",
        "gold_title_substrings": ["denolle", "ambient field", "critical zone"],
    },
    {
        "id": "makus-msh-1",
        "query": (
            "Temperature and precipitation seasonally modulate seismic velocity at "
            "volcanic edifices — how do you separate environmental signal from magmatic signal?"
        ),
        "source_discipline": "seismology",
        "target_discipline": "atmospheric_science",
        "gold_title_substrings": ["makus", "mt. st. helens", "mount st helens", "environmental influences"],
    },
    {
        "id": "toghram-dense-array-1",
        "query": (
            "Dense urban nodal arrays for seismic hazard — what density and "
            "duration do we need to characterize site response?"
        ),
        "source_discipline": "seismology",
        "target_discipline": "geology",
        "gold_title_substrings": ["toghramadjian", "dense urban", "nodal array"],
    },
    {
        "id": "diewald-coda-1",
        "query": (
            "How sensitive are coda wave measurements to temperature and humidity "
            "variations in shallow rock?"
        ),
        "source_discipline": "atmospheric_science",
        "target_discipline": "seismology",
        "gold_title_substrings": ["diewald", "coda wave", "temperature", "humidity"],
    },
    # --- Persona-overlap pair: same query, two different personas ---
    {
        "id": "persona-cs-1",
        "query": "How can I use seismic ambient noise to build a soil moisture forecasting model?",
        "source_discipline": "seismology",
        "target_discipline": "computer_science",
        "gold_title_substrings": ["agroseismology", "shi", "feng", "denolle"],
        "persona": {
            "discipline": "computer_science",
            "bio": "ML researcher building time-series models for environmental data.",
            "concepts_focus": "time-series forecasting, feature engineering, signal processing",
            "methods_focus": "deep learning, transformers, gradient boosting",
            "tech_stack": "Python, PyTorch, ObsPy, scikit-learn, pandas",
            "papers_of_interest": "agroseismology soil moisture; ambient noise; dv/v",
        },
        "notes": "With persona, expect surfaces with ML/feature-engineering framing.",
    },
    {
        "id": "persona-hydro-1",
        "query": "How can I use seismic ambient noise to build a soil moisture forecasting model?",
        "source_discipline": "seismology",
        "target_discipline": "hydrology",
        "gold_title_substrings": ["agroseismology", "shi", "feng", "denolle"],
        "persona": {
            "discipline": "hydrology",
            "bio": "Hydrologist studying infiltration and unsaturated zone flow.",
            "concepts_focus": "pore pressure, infiltration, soil water content, unsaturated zone",
            "methods_focus": "Richards equation, lysimeter measurements, tensiometers",
            "tech_stack": "HYDRUS, Python, R",
            "papers_of_interest": "agroseismology; hydrological control on seismic velocity",
        },
    },
]


def by_id(item_id: str) -> GoldItem | None:
    for item in GOLD_SET:
        if item.get("id") == item_id:
            return item
    return None

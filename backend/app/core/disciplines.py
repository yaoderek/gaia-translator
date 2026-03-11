from enum import Enum


class Discipline(str, Enum):
    hydrology = "hydrology"
    seismology = "seismology"
    atmospheric_science = "atmospheric_science"
    climatology = "climatology"
    geology = "geology"
    computer_science = "computer_science"
    applied_mathematics = "applied_mathematics"


DISCIPLINE_INFO: dict[Discipline, dict] = {
    Discipline.hydrology: {
        "label": "Hydrology",
        "description": "Studies the movement, distribution, and management of water in the Earth's surface and subsurface systems.",
        "key_concepts": [
            "soil moisture",
            "infiltration capacity",
            "pore water pressure",
            "saturated hydraulic conductivity",
            "water table fluctuation",
            "surface runoff",
            "evapotranspiration",
            "Richards equation",
        ],
    },
    Discipline.seismology: {
        "label": "Seismology",
        "description": "Studies seismic waves, ground motion, and subsurface structure through analysis of vibrations in the Earth.",
        "key_concepts": [
            "seismic velocity",
            "shear wave (Vs)",
            "P-wave attenuation",
            "ground motion amplification",
            "spectral analysis",
            "ambient noise correlation",
            "site response",
            "liquefaction susceptibility",
        ],
    },
    Discipline.atmospheric_science: {
        "label": "Atmospheric Science",
        "description": "Studies atmospheric processes including precipitation, weather systems, and their interactions with the land surface.",
        "key_concepts": [
            "precipitation intensity",
            "antecedent rainfall",
            "atmospheric rivers",
            "orographic enhancement",
            "rainfall duration-frequency",
            "mesoscale convective systems",
            "soil-atmosphere coupling",
        ],
    },
    Discipline.climatology: {
        "label": "Climatology",
        "description": "Studies long-term climate patterns, variability, and change and their effects on Earth surface processes.",
        "key_concepts": [
            "climate change projections",
            "return period analysis",
            "extreme event attribution",
            "drought indices",
            "teleconnection patterns",
            "paleoclimate proxies",
            "climate downscaling",
            "land-use change feedbacks",
        ],
    },
    Discipline.geology: {
        "label": "Geology",
        "description": "Studies Earth materials, structures, and surface processes including slope stability and mass wasting.",
        "key_concepts": [
            "regolith thickness",
            "bedrock weathering",
            "slope angle and aspect",
            "soil cohesion",
            "Mohr-Coulomb failure",
            "clay mineralogy",
            "stratigraphic layering",
            "colluvial deposits",
        ],
    },
    Discipline.computer_science: {
        "label": "Computer Science",
        "description": "Develops computational models, data pipelines, and machine learning methods for geohazard analysis.",
        "key_concepts": [
            "physics-informed neural networks",
            "geospatial data fusion",
            "time-series anomaly detection",
            "graph neural networks",
            "remote sensing classification",
            "uncertainty quantification",
            "digital elevation model processing",
            "real-time sensor data pipelines",
        ],
    },
    Discipline.applied_mathematics: {
        "label": "Applied Mathematics",
        "description": "Develops mathematical frameworks for modeling coupled physical processes in soil and geohazard systems.",
        "key_concepts": [
            "coupled PDE systems",
            "finite element methods",
            "stochastic differential equations",
            "inverse problems",
            "sensitivity analysis",
            "Bayesian inference",
            "multiscale modeling",
            "stability analysis",
        ],
    },
}

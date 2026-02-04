"""
Research Ontology for RIQ Matching v2

Contains:
- ONTOLOGY: domain-specific synonym expansions
- PHRASES: multi-word terms to detect as single units
- Helper functions for term expansion

Keep this lightweight for fast runtime. Expand over time.
"""

from typing import Dict, List, Set

# ============================================================================
# ONTOLOGY: Key research domains mapped to related terms/synonyms
# ============================================================================

ONTOLOGY: Dict[str, List[str]] = {
    # Computer Science / AI / ML
    "machine learning": ["ml", "deep learning", "neural networks", "artificial intelligence", "ai", "statistical learning"],
    "deep learning": ["neural networks", "cnn", "rnn", "transformer", "lstm", "gan", "diffusion"],
    "natural language processing": ["nlp", "language models", "text mining", "computational linguistics", "llm", "information retrieval"],
    "computer vision": ["image processing", "object detection", "image segmentation", "visual recognition", "scene understanding"],
    "reinforcement learning": ["rl", "policy gradient", "q-learning", "multi-agent", "decision making"],
    "robotics": ["autonomous systems", "manipulation", "motion planning", "control systems", "human-robot interaction"],
    "artificial intelligence": ["ai", "machine learning", "intelligent systems", "cognitive computing"],
    
    # Biology / Life Sciences
    "genomics": ["sequencing", "dna", "rna", "genome", "transcriptomics", "whole genome", "exome"],
    "single cell": ["scrna-seq", "single cell rna", "single cell sequencing", "scatac", "single cell analysis"],
    "proteomics": ["mass spectrometry", "protein", "peptide", "proteome", "protein expression"],
    "bioinformatics": ["computational biology", "biological data analysis", "sequence analysis", "biological databases"],
    "systems biology": ["network biology", "pathway analysis", "biological networks", "omics integration"],
    "synthetic biology": ["genetic engineering", "metabolic engineering", "bioengineering", "gene circuits"],
    "immunology": ["immune system", "t cells", "b cells", "antibodies", "vaccine", "immunotherapy"],
    "neuroscience": ["brain", "neural", "cognitive", "neuroimaging", "neurobiology", "neurons"],
    "cancer": ["oncology", "tumor", "carcinoma", "metastasis", "cancer biology", "oncogene"],
    "microbiology": ["bacteria", "microbiome", "microbial", "pathogen", "infectious disease"],
    "structural biology": ["protein structure", "crystallography", "cryo-em", "structural determination", "molecular structure"],
    "cell biology": ["cellular", "cell signaling", "cell cycle", "membrane biology", "organelles"],
    "developmental biology": ["embryology", "morphogenesis", "stem cells", "differentiation", "organogenesis"],
    "genetics": ["heredity", "gene", "mutation", "inheritance", "mendelian", "genetic variation"],
    "molecular biology": ["dna", "rna", "protein", "gene expression", "molecular mechanisms"],
    "ecology": ["ecosystems", "biodiversity", "conservation", "environmental biology", "population dynamics"],
    "evolution": ["evolutionary biology", "phylogenetics", "natural selection", "adaptation", "speciation"],
    
    # Chemistry / Biochemistry
    "organic chemistry": ["synthesis", "organic synthesis", "chemical reactions", "organic molecules"],
    "biochemistry": ["enzymes", "metabolism", "biochemical", "molecular biology", "protein chemistry"],
    "materials science": ["nanomaterials", "polymers", "materials engineering", "material properties", "composites"],
    "nanotechnology": ["nanoscale", "nanoparticles", "nanomedicine", "nano", "nanofabrication"],
    "drug discovery": ["pharmaceutical", "therapeutics", "drug development", "medicinal chemistry", "pharmacology"],
    
    # Physics / Engineering
    "quantum computing": ["qubits", "quantum algorithms", "quantum information", "quantum mechanics"],
    "photonics": ["optics", "lasers", "optical", "photonic devices", "light"],
    "renewable energy": ["solar", "wind", "sustainable energy", "clean energy", "energy storage"],
    "biomedical engineering": ["medical devices", "biomechanics", "biomedical", "tissue engineering", "bme"],
    "electrical engineering": ["circuits", "electronics", "signals", "embedded systems"],
    "mechanical engineering": ["mechanics", "dynamics", "thermodynamics", "fluid mechanics"],
    
    # Data Science / Statistics
    "data science": ["data analysis", "analytics", "big data", "data mining", "statistical analysis"],
    "statistics": ["statistical methods", "probability", "bayesian", "inference", "regression"],
    "computational": ["computing", "algorithms", "numerical methods", "simulation", "modeling"],
    
    # Medical / Clinical
    "clinical research": ["clinical trials", "patient outcomes", "medical research", "translational research"],
    "epidemiology": ["public health", "disease prevention", "population health", "health outcomes"],
    "medical imaging": ["radiology", "mri", "ct scan", "ultrasound", "diagnostic imaging"],
    
    # Social Sciences (for interdisciplinary)
    "human-computer interaction": ["hci", "user experience", "ux", "interaction design", "usability"],
    "cognitive science": ["cognition", "perception", "attention", "memory", "decision making"],
}

# ============================================================================
# PHRASES: Multi-word terms to detect as single units (bigrams/trigrams)
# These get higher weight in matching
# ============================================================================

PHRASES: List[str] = [
    # AI/ML phrases
    "machine learning",
    "deep learning",
    "neural network",
    "neural networks",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
    "graph neural",
    "language model",
    "language models",
    "large language",
    "generative ai",
    "diffusion model",
    "transformer model",
    "attention mechanism",
    
    # Biology phrases
    "single cell",
    "stem cell",
    "stem cells",
    "gene expression",
    "gene editing",
    "genome wide",
    "protein structure",
    "drug discovery",
    "drug development",
    "clinical trial",
    "clinical trials",
    "cell signaling",
    "immune system",
    "cancer biology",
    "tumor microenvironment",
    "gene therapy",
    "rna sequencing",
    "mass spectrometry",
    "cryo em",
    "x ray",
    
    # Chemistry/Materials phrases
    "organic synthesis",
    "materials science",
    "renewable energy",
    "solar cell",
    "solar cells",
    "energy storage",
    "carbon capture",
    "nanomaterials",
    "drug delivery",
    
    # Engineering phrases
    "biomedical engineering",
    "tissue engineering",
    "medical device",
    "medical devices",
    "control systems",
    "signal processing",
    "image processing",
    
    # Data/Computing phrases
    "data science",
    "data analysis",
    "big data",
    "high performance",
    "distributed systems",
    "cloud computing",
    "quantum computing",
    
    # Medical phrases
    "clinical research",
    "public health",
    "health outcomes",
    "medical imaging",
    "precision medicine",
    "personalized medicine",
    
    # Interdisciplinary
    "human computer",
    "user experience",
    "decision making",
]

# ============================================================================
# SKILL SYNONYMS: Map common skill variations
# ============================================================================

SKILL_SYNONYMS: Dict[str, List[str]] = {
    "python": ["py", "python3", "python programming"],
    "r": ["r programming", "rstats", "r language"],
    "matlab": ["mathworks", "matlab programming"],
    "java": ["java programming", "jvm"],
    "javascript": ["js", "node", "nodejs", "typescript", "ts"],
    "c++": ["cpp", "c plus plus"],
    "sql": ["mysql", "postgresql", "database", "sqlite"],
    "tensorflow": ["tf", "keras"],
    "pytorch": ["torch"],
    "machine learning": ["ml", "sklearn", "scikit-learn"],
    "deep learning": ["dl", "neural networks"],
    "statistics": ["stats", "statistical analysis"],
    "data analysis": ["data analytics", "data science"],
    "bioinformatics": ["computational biology"],
    "microscopy": ["imaging", "confocal", "fluorescence microscopy"],
    "pcr": ["qpcr", "rt-pcr", "polymerase chain reaction"],
    "cell culture": ["tissue culture", "mammalian cell culture"],
    "crispr": ["gene editing", "crispr-cas9", "genome editing"],
    "sequencing": ["ngs", "next generation sequencing", "illumina"],
    "mass spec": ["mass spectrometry", "lcms", "gcms"],
    "western blot": ["immunoblot", "western blotting"],
    "flow cytometry": ["facs", "cell sorting"],
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_ontology() -> Dict[str, List[str]]:
    """Return the ontology dictionary."""
    return ONTOLOGY

def get_phrases() -> List[str]:
    """Return the phrases list."""
    return PHRASES

def get_skill_synonyms() -> Dict[str, List[str]]:
    """Return skill synonym mappings."""
    return SKILL_SYNONYMS

def expand_term(term: str) -> Set[str]:
    """
    Given a term, return a set of related terms from the ontology.
    Includes the original term plus any expansions.
    """
    term_lower = term.lower().strip()
    result = {term_lower}
    
    # Check if term is a key in ontology
    if term_lower in ONTOLOGY:
        result.update(ONTOLOGY[term_lower])
    
    # Check if term appears in any ontology values
    for key, values in ONTOLOGY.items():
        if term_lower in [v.lower() for v in values]:
            result.add(key)
            result.update(values)
    
    return result

def normalize_skill(skill: str) -> str:
    """
    Normalize a skill name to its canonical form.
    """
    skill_lower = skill.lower().strip()
    
    # Check if it's a synonym
    for canonical, synonyms in SKILL_SYNONYMS.items():
        if skill_lower == canonical or skill_lower in [s.lower() for s in synonyms]:
            return canonical
    
    return skill_lower

#!/usr/bin/env python3
"""
Build wiki-style knowledge pages from the verified LLM paper analyses.

Aggregates data/papers/llm_analyses/*.json into canonical, cross-linked
entity pages for genes, mutations, and species:

  web/public/data/wiki_genes.json      — per-gene synthesis (roles, papers, mutations)
  web/public/data/wiki_mutations.json  — per-mutation synthesis (effects, papers)
  web/public/data/wiki_species.json    — per-species evidence synthesis
  web/public/data/wiki_index.json      — compact index for global search

Every aggregated claim keeps its paper_id so the UI can cite the source.
Design doc: docs/PLAN_WIKI.md
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

import sys as _sys
_sys_path = str(PROJECT_ROOT / "scripts" / "papers")
if _sys_path not in _sys.path:
    _sys.path.insert(0, _sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None
LLM_DIR = PROJECT_ROOT / "data" / "papers" / "llm_analyses"
DISCOVERY_PATH = PROJECT_ROOT / "data" / "papers" / "gene_discovery.jsonl"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
CURATED_GENES_JSON = PROJECT_ROOT / "web" / "public" / "data" / "genes.json"
OUT_DIR = PROJECT_ROOT / "web" / "public" / "data"
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
MUT_HOST_CLAIMS = PROJECT_ROOT / "data" / "papers" / "mutation_host_claims.jsonl"
PRESENCE_JSON = PROJECT_ROOT / "web" / "public" / "data" / "gene_catalogue.json"

# ---------------------------------------------------------------------------
# Canonical gene definitions
# ---------------------------------------------------------------------------

# Host genes (canonical symbol -> aliases). Category/tier merge with curated panel.
HOST_GENES = {
    "ANP32A": ["anp32a", "anp32-a", "pp32", "lanp", "acidic nuclear phosphoprotein 32a"],
    "ANP32B": ["anp32b", "anp32-b", "april"],
    "ANP32E": ["anp32e", "anp32-e", "cpd1"],
    "DDX58": ["rig-i", "rig-1", "rig1", "ddx58", "retinoic acid-inducible gene i", "retinoic acid inducible gene i"],
    "IFIH1": ["mda5", "ifih1", "melanoma differentiation-associated gene 5", "melanoma differentiation associated gene 5"],
    "MX1": ["mx1", "mx", "mxa", "mx a", "myxovirus resistance 1", "myxovirus resistance"],
    "IFIT5": ["ifit5", "ifit-5"],
    "IFITM": ["ifitm", "ifitm3", "ifitm5"],
    "TRIM25": ["trim25", "trim 25"],
    "TRIM32": ["trim32"],
    "IRF3": ["irf3"],
    "IRF7": ["irf7"],
    "MAVS": ["mavs", "ips-1", "cardif"],
    "OAS": ["oas", "2'-5' oligoadenylate synthetase", "oligoadenylate synthetase"],
    "OASL": ["oasl", "hoasl", "moasl1", "moasl2", "oasl1", "oasl2",
             "avian oasl", "doasl", "goasl", "choasl", "duck oasl",
             "oligoadenylate synthetase-like", "59-kda p59 oas-like protein"],
    "JAK1": ["jak1", "janus kinase 1", "tyk2-like kinase jak1"],
    "JAK2": ["jak2", "janus kinase 2"],
    "JAK3": ["jak3", "janus kinase 3"],
    "HERC3": ["herc3"],
    "RSAD2": ["rsad2", "viperin"],
    "STING": ["sting", "sting1", "tmem173", "mita", "eris",
              "stimulator of interferon genes",
              "transmembrane protein 173"],
    "IFNA": ["ifn-alpha", "ifn alpha", "ifna", "interferon-alpha", "type i interferon", "ifn-i"],
    "IFNB": ["ifn-beta", "ifn beta", "ifnb", "interferon-beta"],
}

# Viral proteins (canonical -> aliases)
VIRAL_PROTEINS = {
    "HA": ["ha", "hemagglutinin", "haemagglutinin", "h5", "h5n1 ha"],
    "NA": ["na", "neuraminidase", "n1"],
    "NP": ["np", "nucleoprotein", "nucleocapsid protein"],
    "PA": ["pa", "polymerase acidic", "pa-x", "pax"],
    "PB1": ["pb1", "polymerase basic 1"],
    "PB2": ["pb2", "polymerase basic 2"],
    "PB1-F2": ["pb1-f2", "pb1f2"],
    "M1": ["m1", "matrix protein 1", "matrix (m1)", "m (matrix)"],
    "M2": ["m2", "matrix protein 2", "matrix 2", "am2"],
    "NS1": ["ns1", "non-structural protein 1", "nonstructural protein 1"],
    "NEP": ["nep", "ns2", "nuclear export protein"],
}

GENE_ALIASES = {}
for sym, aliases in {**HOST_GENES, **VIRAL_PROTEINS}.items():
    GENE_ALIASES[sym.lower()] = sym
    for a in aliases:
        GENE_ALIASES[a.lower()] = sym

# Extra aliases harvested from LLM extraction noise (after Greek normalization)
EXTRA_ALIASES = {
    "m": "M", "m gene": "M", "matrix gene": "M", "matrix protein": "M",
    "matrix": "M", "mp": "M", "m/m1": "M", "m1/m2": "M",
    "nep/ns2": "NEP", "ns2/nep": "NEP", "ns/ns1": "NS1",
    "polymerase basic protein 2": "PB2", "polymerase basic protein 1": "PB1",
    "polymerase acidic protein": "PA", "polymerase acidic": "PA",
    "ifn-b": "IFNB", "ifn-beta": "IFNB", "interferon beta": "IFNB",
    "ifn-g": "IFNG", "ifn-gamma": "IFNG", "ifng": "IFNG",
    "interferon gamma": "IFNG",
    "il-1b": "IL1B", "il-6": "IL6", "il-18": "IL18", "il-2": "IL2",
    "tnf": "TNF", "tnf-a": "TNF", "tnf-alpha": "TNF",
    "nf-kb": "NFKB", "nfkb": "NFKB", "nf-kappab": "NFKB",
    "importin-a": "KPNA", "importin alpha": "KPNA", "importin-alpha": "KPNA",
    "toll-like receptors": "TLR", "tlr": "TLR",
    "beta-actin": "ACTB", "actb": "ACTB", "tubulin": "TUBB", "tubb": "TUBB",
    "st6gal1": "ST6GAL1",
}
GENE_ALIASES.update(EXTRA_ALIASES)

# Symbol-level synonym fold (literature unification, 2026-10-05):
# legacy names -> current HGNC symbols, shared with build_aggregation via
# data/papers/gene_alias_map.json["synonyms"]
import json as _json
GENE_SYNONYMS = {}
GENE_LLM_ALIASES = {}
_syn_file = PROJECT_ROOT / "data" / "papers" / "gene_alias_map.json"
if _syn_file.exists():
    _am = _json.loads(_syn_file.read_text())
    GENE_SYNONYMS = _am.get("synonyms", {})
    GENE_LLM_ALIASES = _am.get("aliases", {})

# Symbols that are also common English words: the text-mention scanner
# (case-insensitive \b match) picks up prose like "test kit" / "ELISA kit".
# Suppress their text-scan tier entirely; studied/extracted evidence (which
# passes LLM gene extraction) is unaffected. Extend as new collisions appear.
TEXT_SCAN_STOPWORDS = {"KIT"}

# Housekeeping / control / non-gene mentions to exclude from wiki gene pages
NOISE_GENES = {"GAPDH", "ACTB", "TUBB", "IGG", "H7", "H5", "N1", "GFP",
                "SPIKE PROTEIN", "FLAGELLIN", "EBOLA VIRUS GLYCOPROTEIN",
                "TYPE I INTERFERONS", "INTERNAL GENES", "NONSTRUCTURAL PROTEIN",
                "SIALIC_ACID"}  # + panel-junk concepts (2026-10-05 audit)

# Discovery-log noise (GENE_PANEL.md §12.3): non-gene tokens that reach
# gene_discovery.jsonl via the campaign/connections loggers.
DISCOVERY_NOISE_RE = re.compile(
    r"^(12S|16S|18S|28S)(\s|$)|RRNA|RDNA|^LOC\d+|^AC\d{6}|^2A$|^40K$"
    r"|^IG[A-Z]$|^\d+$|^SNOR|^MIR\d|^RNU\d$|^GFP$|^H\d+$|^N\d+$"
)

# Greek letters smuggled out of PDFs: IFN-Β, NF-ΚB, TNF-Α, IFNΓ …
GREEK_TO_LATIN = str.maketrans({
    "Α": "A", "Β": "B", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z",
    "Η": "H", "Θ": "T", "Κ": "K", "Λ": "L", "Μ": "M", "Ν": "N",
    "Ο": "O", "Π": "P", "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y",
    "Φ": "F", "Χ": "X", "Ψ": "P", "Ω": "O",
    "α": "A", "β": "B", "γ": "G", "κ": "K",
})


def normalize_gene_name(raw: str) -> str:
    """Clean an LLM-extracted gene name to a canonical symbol."""
    base = re.sub(r"\s*\([^)]*\)", "", raw).strip()   # "NP (NUCLEOPROTEIN)" -> "NP"
    base = base.translate(GREEK_TO_LATIN)
    sym = GENE_ALIASES.get(base.lower())
    if not sym:
        # fall back to the shared LLM alias map (same file as
        # build_aggregation / build_gene_registry), then default
        hit = GENE_LLM_ALIASES.get(base) or GENE_LLM_ALIASES.get(base.upper())
        sym = ("" if hit == "NOT_A_GENE" else hit) if hit else (
            base.upper() if len(base) <= 6 else base)
    # symbol-level synonym fold (RIG-I->DDX58, IL-17->IL17, ...):
    # data/papers/gene_alias_map.json["synonyms"] — applied last so phrase
    # aliases and this fold chain cleanly
    return GENE_SYNONYMS.get(sym) or GENE_SYNONYMS.get(sym.upper(), sym)


# Category overrides for canonical symbols discovered in the corpus but not
# in the curated panel
CATEGORY_OVERRIDES = {
    "TLR3": "Pattern Recognition", "TLR7": "Pattern Recognition",
    "TLR21": "Pattern Recognition", "TLR": "Pattern Recognition",
    "RNF135": "Pattern Recognition", "CGAS": "Pattern Recognition",
    "TBK1": "Pattern Recognition", "IFI35": "Pattern Recognition",
    "IFNB": "Immune Response", "IFNG": "Immune Response", "IL6": "Immune Response",
    "IL18": "Immune Response", "IL1B": "Immune Response", "IL2": "Immune Response",
    "TNF": "Immune Response", "NFKB": "Immune Response", "IRF9": "Immune Response",
    "MHC": "Immune Response",
    "IFITM": "Antiviral Response", "PARP14": "Antiviral Response",
    "TRIM14": "Antiviral Response",
    "TMPRSS2": "Host Factor", "ST6GAL1": "Host Factor", "KPNA": "Host Factor",
    "BTN3A3": "Host Factor", "ANP32": "Host Factor",
}

# ---------------------------------------------------------------------------
# Species canonicalization
# ---------------------------------------------------------------------------

# Generic group names that are categories, not species pages
SPECIES_CATEGORIES = {
    "wild birds", "wild bird", "poultry", "waterfowl", "seabirds", "sea birds",
    "shorebirds", "raptors", "passerines", "waterbirds", "gamebirds",
    "humans (general)", "mammals", "birds",
}

SPECIES_CANON = {
    "chicken": ("Chicken", "Gallus gallus", True),
    "chickens": ("Chicken", "Gallus gallus", True),
    "duck": ("Duck", None, True),
    "ducks": ("Duck", None, True),
    "mallard": ("Mallard", "Anas platyrhynchos", True),
    "human": ("Human", "Homo sapiens", False),
    "humans": ("Human", "Homo sapiens", False),
    "dairy cattle": ("Cattle", "Bos taurus", False),
    "cattle": ("Cattle", "Bos taurus", False),
    "cow": ("Cattle", "Bos taurus", False),
    "cows": ("Cattle", "Bos taurus", False),
    "turkey": ("Turkey", "Meleagris gallopavo", True),
    "turkeys": ("Turkey", "Meleagris gallopavo", True),
    "mouse": ("Mouse", "Mus musculus", False),
    "mice": ("Mouse", "Mus musculus", False),
    "ferret": ("Ferret", "Mustela putorius furo", False),
    "ferrets": ("Ferret", "Mustela putorius furo", False),
    "cat": ("Cat", "Felis catus", False),
    "cats": ("Cat", "Felis catus", False),
    "dog": ("Dog", "Canis lupus familiaris", False),
    "swine": ("Swine", "Sus scrofa domesticus", False),
    "pig": ("Swine", "Sus scrofa domesticus", False),
    "pigs": ("Swine", "Sus scrofa domesticus", False),
}

BINOMIAL_RE = re.compile(r"\(([A-Z][a-z]+ [a-z-]+)\)")

# Reverse map: scientific name -> (canonical, avian). Raw binomials in LLM
# text ("Gallus gallus", "Homo sapiens") previously became their OWN
# canonicals via the heuristic path, duplicating the common-name entry
# (Chicken 286 + Gallus gallus 44 …). Folding them here keeps one canonical
# per species (2026-10-30 paper-audit fix).
SCI_TO_CANON = {}
for _canon, _sci, _av in SPECIES_CANON.values():
    if _sci:
        SCI_TO_CANON.setdefault(_sci.lower(), (_canon, _av))

# Common English bird words — a second word from this set means the name is a
# common name ("Peregrine falcon"), not a Latin binomial ("Falco peregrinus")
COMMON_BIRD_WORDS = {
    "falcon", "gull", "tern", "eagle", "owl", "penguin", "duck", "goose",
    "swan", "heron", "crane", "sparrow", "hawk", "kite", "harrier", "osprey",
    "pelican", "cormorant", "stork", "ibis", "spoonbill", "flamingo", "pigeon",
    "dove", "parrot", "cockatoo", "woodpecker", "kingfisher", "roller", "hoopoe",
    "hornbill", "raven", "crow", "jay", "magpie", "lark", "swallow", "martin",
    "wagtail", "thrush", "warbler", "robin", "chat", "flycatcher", "nuthatch",
    "treecreeper", "starling", "myna", "weaver", "bunting", "finch", "skua",
    "shearwater", "petrel", "albatross", "frigatebird", "booby", "gannet",
    "anhinga", "grebe", "loon", "rail", "crake", "coot", "moorhen",
    "oystercatcher", "plover", "lapwing", "snipe", "sandpiper", "godwit",
    "curlew", "redshank", "dunlin", "knot", "stint", "phalarope", "auk",
    "puffin", "guillemot", "murre", "razorbill", "kestrel", "vulture", "condor",
    "buzzard", "harrier", "goshawk", "sparrowhawk", "eagleowl", "courser",
    "pratincole", "jaeger", "egret", "ibisbill", "stork", "shag",
    # gamebirds, waterfowl, ratites (AI-relevant additions)
    "quail", "pheasant", "partridge", "grouse", "ptarmigan", "francolin",
    "guineafowl", "guan", "curassow", "chachalaca",
    "teal", "mallard", "eider", "wigeon", "pochard", "scaup", "scoter",
    "merganser", "shoveler", "pintail", "smew", "goldeneye",
    "cassowary", "emu", "rhea", "kiwi", "tinamou",
}


# Mammal words for host classification (avian=False). Complements COMMON_BIRD_WORDS.
MAMMAL_WORDS = {
    "human", "humans", "cattle", "cow", "cows", "mouse", "mice", "ferret", "ferrets",
    "cat", "cats", "dog", "dogs", "swine", "pig", "pigs", "seal", "seals", "whale",
    "whales", "dolphin", "dolphins", "porpoise", "fox", "foxes", "mink", "minks",
    "bear", "bears", "raccoon", "raccoons", "skunk", "skunks", "opossum", "opossums",
    "lion", "lions", "tiger", "tigers", "leopard", "wolf", "wolves", "coyote", "jackal",
    "otter", "otters", "deer", "bison", "alpaca", "llama", "goat", "goats", "sheep",
    "horse", "horses", "donkey", "rabbit", "rabbits", "hamster", "hamsters", "monkey",
    "monkeys", "macaque", "macaques", "bat", "bats", "camel", "camels", "dromedary",
    "pangolin", "vole", "voles", "shrew", "shrews", "mole", "moles", "hedgehog",
    "kangaroo", "koala", "weasel", "stoat", "marten", "badger", "wolverine", "lynx",
    "bobcat", "cougar", "jaguar", "cheetah", "hyena", "mongoose", "walrus", "manatee",
    "gorilla", "chimpanzee", "baboon", "elephant", "elephants", "rat", "rats",
    "squirrel", "squirrels", "marmot", "marmots", "elk", "moose", "ox", "buffalo",
    "yak", "tapir", "hippopotamus", "rhinoceros", "giraffe", "zebra", "antelope", "gazelle",
    "caribou", "reindeer", "muskox", "lemur", "loris", "tarsier", "orangutan", "gorillas",
}


def guess_avian(name: str):
    """Heuristic avian (True) / mammalian (False) / unknown (None) from a name."""
    words = name.lower().replace("-", " ").split()
    if not words:
        return None
    if words[-1] in COMMON_BIRD_WORDS or words[-1] in ("bird", "birds"):
        return True
    if any(w in MAMMAL_WORDS for w in words):
        return False
    return None


def host_scope(avian_papers: int, mammal_papers: int) -> str:
    """Classify an entity's evidence base: avian / both / mammalian / viral."""
    if avian_papers and mammal_papers:
        return "both"
    if avian_papers:
        return "avian"
    if mammal_papers:
        return "mammalian"
    return "viral"


# Sort priority for display: avian resource mission first
SCOPE_PRIORITY = {"avian": 0, "both": 1, "mammalian": 2, "viral": 3, "unknown": 4}


def paper_host_flags(p):
    """(has_avian, has_mammal) for a paper's normalized species rows."""
    has_avian = has_mam = False
    for cname, _, _, _ in p["species"]:
        av = species_meta.get(cname, (None, None))[1]
        if av is None:
            av = guess_avian(cname)
            if av is not None:
                species_meta[cname] = (species_meta.get(cname, (None, None))[0], av)
        if av is True:
            has_avian = True
        elif av is False:
            has_mam = True
    return has_avian, has_mam


def scoped_species(entries, cap=8):
    """Sort species co-occurrence entries avian-first, flag each entry.

    Non-species categories (generic 'goose', genus-level 'Larus sp.') are
    dropped: they can never resolve to a species page (D-quality)."""
    non_species = re.compile(r"\bsp\.?$", re.IGNORECASE)
    generics = {"goose", "geese", "duck", "ducks", "swan", "swans", "gull",
                "raptor", "raptors", "poultry", "waterfowl", "shorebird",
                "shorebirds", "wild bird", "wild birds", "bird", "birds",
                "passerine", "passerines", "seabird", "seabirds"}
    flagged = []
    for cname, count in entries:
        if cname.lower() in generics or non_species.search(cname):
            continue
        sci, av = species_meta.get(cname, (None, None))
        if av is None:
            av = guess_avian(cname)
        flagged.append({"name": cname, "papers": count, "avian": av, "scientific": sci})
    flagged.sort(key=lambda s: (s["avian"] is not True, s["avian"] is not False, -s["papers"]))
    return flagged[:cap]


def canonical_species(raw: str):
    """Return (canonical_name, scientific, avian, qualifier) or None for categories."""
    name = raw.strip()
    if not name:
        return None
    lower = name.lower()

    # Extract qualifier: "Chicken (ANP32A-GE N129I-D130N)" -> qualifier
    qualifier = None
    m = re.match(r"^([A-Za-z .\-']+?)\s*\(([^)]*)\)$", name)
    if m and not BINOMIAL_RE.search(name):
        name = m.group(1).strip()
        qualifier = m.group(2).strip()
        lower = name.lower()

    # Binomial in parentheses: "Peregrine falcon (Falco peregrinus)"
    sci = None
    bm = BINOMIAL_RE.search(name)
    if bm:
        sci = bm.group(1)
        name = re.sub(r"\s*\([^)]*\)", "", name).strip()

    if lower in SPECIES_CATEGORIES:
        return None
    if lower in SPECIES_CANON:
        canon, sci_c, avian = SPECIES_CANON[lower]
        return (canon, sci or sci_c, avian, qualifier)

    # Heuristic binomial: "Falco peregrinus" (no common-name second word).
    # Trinomials ("Gallus gallus domesticus") contribute their leading
    # binomial as the scientific name.
    if sci is None:
        m_tri = re.match(r"^([A-Z][a-z]+ [a-z-]+)(?: [a-z-]+)+$", name)
        m_bi = re.match(r"^[A-Z][a-z]+ [a-z-]+$", name)
        if m_tri:
            sci = m_tri.group(1)
        elif m_bi and m_bi.group(0).split()[1] not in COMMON_BIRD_WORDS:
            sci = name

    # Raw binomial for a species with a common-name canonical — fold it in
    # so both spellings aggregate under ONE wiki entry.
    if sci and sci.lower() in SCI_TO_CANON:
        canon, avian_c = SCI_TO_CANON[sci.lower()]
        return (canon, sci, avian_c, qualifier)

    avian = guess_avian(name)
    # Case-normalize common names so "Peregrine falcon" / "peregrine falcon"
    # / "Peregrine Falcon" aggregate under one canonical (2026-10-30 fix).
    if not BINOMIAL_RE.search(name):
        name = name[0].upper() + name[1:].lower() if name else name
    return (name, sci, avian, qualifier)


# ---------------------------------------------------------------------------
# Mutation canonicalization
# ---------------------------------------------------------------------------

MUT_RE = re.compile(
    r"^(?P<protein>[A-Za-z][A-Za-z0-9]{0,7})\s*[-_ ]?\s*"
    r"(?P<ref>[A-Z])(?P<pos>\d+)(?P<alt>[A-Z*])"
    r"(?:[-\s]*(?P<ref2>[A-Z])(?P<pos2>\d+)(?P<alt2>[A-Z*]))*$"
)


def canonical_mutation(raw: str):
    """'PB2 M631L' / 'PB2-M631L' / 'PB2_E627K' -> 'PB2-M631L' etc."""
    name = raw.strip()
    if not name or len(name) > 40:
        return None
    # Normalize common separators
    norm = re.sub(r"\s*[-_]\s*", "-", name)
    norm = re.sub(r"\s+", " ", norm)
    m = MUT_RE.match(norm)
    if not m:
        return None
    protein = m.group("protein").upper().rstrip("-_ ")
    protein = GENE_ALIASES.get(protein.lower(), protein)
    # species-prefixed host proteins from the literature: chANP32A → ANP32A
    if protein not in HOST_GENES and protein not in VIRAL_PROTEINS:
        for prefix in ("CH", "HUMAN", "BOVINE", "AVIAN", "DUCK"):
            if protein.startswith(prefix) and len(protein) > len(prefix):
                stripped = protein[len(prefix):]
                if stripped.lower() in GENE_ALIASES:
                    protein = GENE_ALIASES[stripped.lower()]
                    break
    # Only scan the mutation portion (after the protein name) so gene names
    # like ANP32A don't yield false "P32A" matches
    mut_part = norm[m.end("protein"):]
    parts = re.findall(r"([A-Z])(\d+)([A-Z*])", mut_part)
    if not parts:
        return None
    mut = "-".join(f"{r}{p}{a}" for r, p, a in parts)
    canon = f"{protein}-{mut}"
    return canon


def mutation_protein(canonical: str) -> str:
    return canonical.split("-")[0]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def load_analyses():
    out = {}
    for path in sorted(LLM_DIR.glob("*.json")):
        try:
            with open(path) as f:
                d = json.load(f)
            out[d["paper_id"]] = d
        except Exception:
            continue
    return out


def paper_meta_from(papers_json):
    meta = {}
    for p in papers_json.get("papers", []):
        meta[p["id"]] = p
    return meta


def extract(step_data, key):
    return step_data.get("extracted", {}).get(key, []) if step_data else []


def brief_paper_row(pid, meta=None):
    m = meta or {}
    return {
        "paper_id": pid,
        "title": m.get("title", ""),
        "year": m.get("year"),
        "journal": m.get("journal", ""),
    }


def attach_findings(target_list, findings_pool, max_per_paper=2, cap=6):
    """Attach cited quantified findings, newest first, max per paper.
    Stamps fh (md5[:12] of the finding text) — the i18n translation key.
    Only infection-category findings qualify for key numbers; methods/QC
    metrics are attached separately via attach_methods."""
    pool = [f for f in findings_pool if f.get("category", "infection") != "methods"]
    seen_per_paper = defaultdict(int)
    out = []
    for f in pool:  # pool sorted newest-first
        pid = f["paper_id"]
        if seen_per_paper[pid] >= max_per_paper:
            continue
        seen_per_paper[pid] += 1
        if f.get("finding") and "fh" not in f:
            import hashlib
            f["fh"] = hashlib.md5(f["finding"].encode("utf-8")).hexdigest()[:12]
        out.append(f)
        if len(out) >= cap:
            break
    target_list.extend(out)


def attach_methods(target_list, findings_pool, cap=3):
    """Attach methods/QC findings (sequencing depth, alignment rates...).
    Kept visible for readers who want the technical picture, capped low."""
    pool = [f for f in findings_pool if f.get("category") == "methods"]
    seen = set()
    out = []
    for f in pool:
        key = (f["paper_id"], f.get("finding", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        if f.get("finding") and "fh" not in f:
            import hashlib
            f["fh"] = hashlib.md5(f["finding"].encode("utf-8")).hexdigest()[:12]
        out.append(f)
        if len(out) >= cap:
            break
    target_list.extend(out)


# Species metadata cache: canonical name -> (scientific, avian_flag)
# Module-level so helpers (paper_host_flags, scoped_species) can update it
species_meta = {}


def check_gene_set_consistency(wiki_genes: dict, curated: dict) -> None:
    """D98 invariant — wiki_genes.json is the canonical gene record.

    Raises SystemExit when a curated gene (genes.json) has no wiki entry.
    Warns (does not fail) when the on-disk presence catalogue's literature
    scope disagrees with wiki membership: the catalogue is downstream —
    export_presence.py derives evidence_scope from this wiki, and the pytest
    suite (test_wiki_consistency.py) fails the build on any drift.
    """
    def _canon(s: str) -> str:
        return (s or "").upper().replace("-", "").replace("_", "").replace(" ", "")

    wiki_host = {_canon(s) for s, w in wiki_genes.items() if w.get("kind") != "viral"}
    wiki_all = {_canon(s) for s in wiki_genes}
    errors = []

    for symbol in curated:
        if _canon(symbol) not in wiki_all:
            errors.append(f"curated gene {symbol} has no wiki entry")

    if PRESENCE_JSON.exists():
        try:
            catalogue = json.loads(PRESENCE_JSON.read_text())["gene_catalogue"]
        except Exception:
            catalogue = {}
        lit_missing = [sym for sym, info in catalogue.items()
                       if info.get("evidence_scope") == "literature"
                       and _canon(sym) not in wiki_host]
        ann_wrong = [sym for sym, info in catalogue.items()
                     if info.get("evidence_scope") != "literature"
                     and _canon(sym) in wiki_host]
        if lit_missing or ann_wrong:
            print(f"[wiki] WARNING: presence catalogue out of sync with wiki — "
                  f"{len(lit_missing)} literature genes missing wiki entries, "
                  f"{len(ann_wrong)} catalogue-annotation genes are in the wiki. "
                  "Rerun scripts/genes/export_presence.py to derive scope from "
                  "this wiki build.")

    if errors:
        raise SystemExit("[wiki] gene-set consistency FAILED:\n  - " + "\n  - ".join(errors))
    print(f"[wiki] gene-set consistency OK "
          f"({len(wiki_host)} host wiki entries; curated + catalogue-lit covered)")


def main():
    # Species-linked eligibility (2026-10-05): genes with >=1 typed claim
    # naming a host species get wiki pages even below the 2-paper threshold —
    # evidence-rich singletons (landscape: ~1.1k genes, page total ~1.5k)
    SPECIES_LINKED_GENES = set()
    _tc = PROJECT_ROOT / "data" / "papers" / "typed_claims.parquet"
    if _tc.exists():
        import polars as _pl
        for _r in _pl.read_parquet(_tc).iter_rows(named=True):
            try:
                _sp = json.loads(_r["species"]) if isinstance(_r["species"], str) else (_r["species"] or [])
            except Exception:
                _sp = []
            if not any(isinstance(s, str) and " " in s for s in _sp):
                continue
            try:
                _gs = json.loads(_r["genes"]) if isinstance(_r["genes"], str) else (_r["genes"] or [])
            except Exception:
                _gs = []
            for _g in _gs:
                _s = normalize_gene_name(str(_g))
                if _s:
                    SPECIES_LINKED_GENES.add(_s)
        print(f"[wiki] species-linked page eligibility: {len(SPECIES_LINKED_GENES)} genes")
    # Load sources
    analyses = load_analyses()
    with open(PAPERS_JSON) as f:
        papers_data = json.load(f)
    pmeta = paper_meta_from(papers_data)

    curated = {}
    if CURATED_GENES_JSON.exists():
        with open(CURATED_GENES_JSON) as f:
            curated = {g["symbol"]: g for g in json.load(f).get("genes", [])}

    # Aggregators
    gene_evidence = defaultdict(list)      # symbol -> [{paper_id, role, importance, ...}]
    mutation_evidence = defaultdict(list)  # canonical -> [{paper_id, effect}]
    mutation_aliases = defaultdict(set)
    species_evidence = defaultdict(list)   # canonical -> [{paper_id, finding, status}]
    gene_paper_sets = defaultdict(set)

    def pid_meta(pid):
        return pmeta.get(pid, {})

    pid_meta_cache = {pid: pmeta.get(pid, {}) for pid in analyses}

    # Per-paper normalized views (reused by every aggregator)
    papers = {}
    for pid, analysis in analyses.items():
        steps = analysis.get("steps", {})

        p_genes = []  # [(symbol, role, importance)]
        for g in extract(steps.get("genes"), "genes"):
            raw = str(g.get("name", "")).strip()
            if not raw:
                continue
            symbol = normalize_gene_name(raw)
            p_genes.append((symbol, g.get("role", ""), g.get("importance", "mentioned")))

        p_species = []  # [(canonical, finding, status, qualifier)]
        for s in extract(steps.get("species"), "species"):
            canon = canonical_species(str(s.get("name", "")))
            if not canon:
                continue
            cname, sci, avian, qualifier = canon
            if cname in species_meta:
                csci, cavian = species_meta[cname]
                species_meta[cname] = (sci or csci, avian if avian is not None else cavian)
            else:
                species_meta[cname] = (sci, avian)
            p_species.append((cname, s.get("finding", ""), s.get("infection_status", "unknown"), qualifier))

        p_muts = []  # [(canonical, effect)]
        for m in extract(steps.get("mutations"), "mutations"):
            raw = str(m.get("name", "")).strip()
            canon = canonical_mutation(raw)
            if not canon:
                continue
            if canon != raw:
                mutation_aliases[canon].add(raw)
            p_muts.append((canon, m.get("effect", "")))

        study = steps.get("study", {}).get("extracted", {})
        year = pid_meta_cache.get(pid, {}).get("year") or 0

        papers[pid] = {
            "genes": p_genes,
            "species": p_species,
            "mutations": p_muts,
            "findings": [
                {**brief_paper_row(pid, pid_meta_cache.get(pid, {})),
                 **{"finding": f.get("finding", ""),
                    "value": f.get("value", ""),
                    "context": f.get("context", ""),
                    "category": f.get("category", "infection")}}
                for f in extract(steps.get("findings"), "findings")
            ],
            "conclusions": study.get("conclusions", []),
            "study_type": study.get("study_type", ""),
            "novel_claims": steps.get("novelty", {}).get("extracted", {}).get("novel_claims", []),
            "year": year,
        }

    # Sort each paper's findings pool handle by year once (used by attach_findings)
    papers_by_year = sorted(papers.items(),
                             key=lambda kv: -(kv[1]["year"] if isinstance(kv[1]["year"], int) else 0))

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------
    def papers_with_gene(symbol):
        return [(pid, p) for pid, p in papers_by_year
                if any(sym == symbol for sym, _, _ in p["genes"])]

    def papers_with_species(cname):
        return [(pid, p) for pid, p in papers_by_year
                if any(c == cname for c, _, _, _ in p["species"])]

    def papers_with_mutation(canon):
        return [(pid, p) for pid, p in papers_by_year
                if any(mc == canon for mc, _ in p["mutations"])]

    # ------------------------------------------------------------------
    # Family/alias layer (D32): corpus symbols like "IFITM" or "MDA5"
    # attribute to their canonical panel gene (gene_config wiki_aliases)
    # ------------------------------------------------------------------
    gene_config_path = PROJECT_ROOT / "data" / "genes" / "gene_config.json"
    wiki_aliases = {}
    if gene_config_path.exists():
        raw_cfg = json.loads(gene_config_path.read_text())
        wiki_aliases = {k: v for k, v in raw_cfg.get("wiki_aliases", {}).items()
                        if not k.startswith("_")}

    # ------------------------------------------------------------------
    # Text-mention tier (D39): panel genes DISCUSSED in a paper but missed
    # by extraction (title-bias etc.) get honest "mentioned" evidence —
    # labelled, weaker than studied-role evidence. e.g. the PB2/JAK1 paper
    # discusses JAK2 but its extraction captured only JAK1.
    # ------------------------------------------------------------------
    import re as _re
    panel_syms = []
    if PRESENCE_JSON.exists():
        _p = json.loads(PRESENCE_JSON.read_text())
        panel_syms = [s for s in _p.get("gene_catalogue", {})
                      if len(s) >= 3 and not s.startswith("LOC") and sum(c.isalpha() for c in s) >= 2]  # skip LOC/odd ids
    mention_counts = {}  # pid -> {sym: n}
    if panel_syms and MD_DIR.exists():
        # One combined alternation, single pass per file. (Per-symbol findall
        # was O(symbols × files × bytes) — ~857K scans over 67MB of markdown.)
        # Longest-first so overlapping symbols (e.g. IFITM vs IFITM3) can't
        # shadow each other; \b boundaries keep matches token-exact.
        alt = _re.compile(
            r"\b(?:" + "|".join(_re.escape(s) for s in
                               sorted(panel_syms, key=len, reverse=True)) + r")\b"
        )
        for pid in analyses:
            md = MD_DIR / f"{pid}.md"
            if not md.exists():
                continue
            try:
                text = md.read_text(errors="ignore").upper()
            except OSError:
                continue
            found = {}
            for m in alt.finditer(text):
                sym = m.group(0)
                found[sym] = found.get(sym, 0) + 1
            found = {s: n for s, n in found.items() if n >= 3}
            if found:
                mention_counts[pid] = found

    # ------------------------------------------------------------------
    # Populate evidence lists from the per-paper views
    # ------------------------------------------------------------------
    for pid, p in papers.items():
        for symbol, role, importance in p["genes"]:
            symbol = GENE_SYNONYMS.get(symbol) or GENE_SYNONYMS.get(symbol.upper(), symbol)  # fold legacy symbols
            evidence_row = {
                "paper_id": pid, **{"title": pid_meta_cache[pid].get("title", ""),
                                    "year": pid_meta_cache[pid].get("year"),
                                    "journal": pid_meta_cache[pid].get("journal", "")},
                "role": role, "importance": importance,
            }
            gene_evidence[symbol].append(evidence_row)
            gene_paper_sets[symbol].add(pid)
            target = wiki_aliases.get(symbol)
            if target and target != symbol:
                alias_row = dict(evidence_row)
                alias_row["via_alias"] = symbol
                gene_evidence[target].append(alias_row)
                gene_paper_sets[target].add(pid)

        # text-mention tier: discussed-but-not-extracted panel genes
        for sym_raw, n in mention_counts.get(pid, {}).items():
            sym = GENE_SYNONYMS.get(sym_raw) or GENE_SYNONYMS.get(sym_raw.upper(), sym_raw)  # fold legacy symbols
            if sym in TEXT_SCAN_STOPWORDS:
                continue  # English-word collision ("test kit") — not evidence
            if sym not in gene_paper_sets or pid not in gene_paper_sets.get(sym, set()):
                if pid not in gene_paper_sets.get(sym, set()):
                    gene_evidence[sym].append({
                        "paper_id": pid,
                        "title": pid_meta_cache[pid].get("title", ""),
                        "year": pid_meta_cache[pid].get("year"),
                        "journal": pid_meta_cache[pid].get("journal", ""),
                        "role": f"discussed in text ({n} mentions — not a primary study subject)",
                        "importance": "supporting",
                        "via": "text_scan",
                    })
                    gene_paper_sets[sym].add(pid)

        for cname, finding, status, qualifier in p["species"]:
            row = {
                "paper_id": pid, **{"title": pid_meta_cache[pid].get("title", ""),
                                    "year": pid_meta_cache[pid].get("year")},
                "finding": finding, "infection_status": status,
            }
            if qualifier:
                row["qualifier"] = qualifier
            species_evidence[cname].append(row)
        for canon, effect in p["mutations"]:
            mutation_evidence[canon].append({
                "paper_id": pid, **{"title": pid_meta_cache[pid].get("title", ""),
                                    "year": pid_meta_cache[pid].get("year"),
                                    "journal": pid_meta_cache[pid].get("journal", "")},
                "effect": effect,
                # md5[:12] of the effect sentence — the i18n findings-map key
                # (same convention as fh; lets Mutations.svelte call ft(eh)).
                "eh": hashlib.md5(effect.encode("utf-8")).hexdigest()[:12],
            })

    # ------------------------------------------------------------------
    # Effect-level host claims (D118): mine_mutation_hosts.py ledger —
    # WHERE each mutation effect was observed (aves/mammal/…). Fixes the
    # paper-species mislabel: a wild-bird surveillance paper reporting
    # 'increased virulence in mice' is MAMMALIAN evidence even though the
    # paper studied ducks. Contradicted (skeptic-refuted) claims never
    # count; unverified ones do (humans review them via the ledger).
    # ------------------------------------------------------------------
    mut_host_claims = defaultdict(lambda: defaultdict(set))  # canon -> class -> pids
    paper_mut_host = {}  # (pid, canon) -> host_class, for per-paper row tags
    if MUT_HOST_CLAIMS.exists():
        for line in MUT_HOST_CLAIMS.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("error") or rec.get("verified") is False:
                continue
            canon = canonical_mutation(str(rec.get("mutation", "")))
            hc = rec.get("host_class")
            if not canon or hc not in ("aves", "mammal", "both", "non_host", "unknown"):
                continue
            pid = rec.get("paper_id")
            mut_host_claims[canon][hc].add(pid)
            paper_mut_host[(pid, canon)] = hc

    # ------------------------------------------------------------------
    # Discovery-log tier (D97): genes recorded by campaign/connections
    # logging that never reached a parsed genes step (133 analyses carry
    # broken genes steps — JSON parse errors). The discovery log is the
    # safety net so corpus evidence cannot silently vanish from the wiki.
    # ------------------------------------------------------------------
    if DISCOVERY_PATH.exists():
        added_disc = 0
        for line in DISCOVERY_PATH.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            pid = d.get("paper_id")
            if not pid or pid not in pid_meta_cache:
                continue  # stale/orphaned paper id — never cite it
            raw = str(d.get("gene", "")).strip()
            if not raw:
                continue
            symbol = normalize_gene_name(raw)
            if not symbol or symbol in NOISE_GENES or DISCOVERY_NOISE_RE.match(symbol):
                continue
            if pid in gene_paper_sets.get(symbol, set()):
                continue  # already captured by a parsed genes step
            gene_evidence[symbol].append({
                "paper_id": pid, **{"title": pid_meta_cache[pid].get("title", ""),
                                    "year": pid_meta_cache[pid].get("year"),
                                    "journal": pid_meta_cache[pid].get("journal", "")},
                "role": (d.get("role") or "reported in the corpus discovery log").strip(),
                "importance": d.get("importance") or "mentioned",
                "via": "discovery_log",
            })
            gene_paper_sets[symbol].add(pid)
            added_disc += 1
        print(f"[wiki] discovery-log evidence rows added: {added_disc}")

    # ------------------------------------------------------------------
    # wiki_genes.json
    # ------------------------------------------------------------------
    wiki_genes = {}
    merged_wiki_dupes: list[tuple[str, str]] = []
    wiki_symbols = set(gene_evidence.keys()) | set(curated.keys())
    for symbol in wiki_symbols:
        ev = gene_evidence.get(symbol, [])
        if symbol in NOISE_GENES:
            continue
        if (len(gene_paper_sets[symbol]) < 2 and symbol not in curated
                and symbol not in SPECIES_LINKED_GENES):
            continue  # single-paper noise unless curated or species-evidenced
        ev.sort(key=lambda e: (
            0 if e["importance"] == "central" else 1,
            -(int(e["year"]) if str(e["year"]).isdigit() else 0),
        ))
        ev = [r for r in ev if (r.get("role") or "").strip()]
        for r in ev:
            r["fh"] = hashlib.md5(r["role"].encode("utf-8")).hexdigest()[:12]
        # Deduplicate roles per paper (aliases can produce multiple rows)
        seen_pids = set()
        deduped = []
        for e in ev:
            if e["paper_id"] in seen_pids:
                continue
            seen_pids.add(e["paper_id"])
            deduped.append(e)
        ev = deduped
        central_count = sum(1 for e in ev if e["importance"] == "central")
        is_viral = symbol in VIRAL_PROTEINS or symbol in ("NS", "M")
        is_segment = symbol in ("NS", "M")
        if symbol in CATEGORY_OVERRIDES:
            category = CATEGORY_OVERRIDES[symbol]
        else:
            category = ("Viral Segment" if is_segment else
                        "Viral Protein" if is_viral else
                        ("Host Factor" if symbol in ("ANP32A", "ANP32B", "ANP32E") else
                         ("Pattern Recognition" if symbol in ("DDX58", "IFIH1") else "Host Gene")))
        entry = {
            "symbol": symbol,
            "name": curated.get(symbol, {}).get("name", symbol),
            "category": curated.get(symbol, {}).get("category", category),
            # top-level split: host gene vs viral protein/segment
            "kind": "viral" if (is_viral) else "host",
            "paper_count": len(gene_paper_sets[symbol]),
            "central_count": central_count,
            "is_viral_protein": is_viral,
            "roles": ev[:12],
        }

        # Quantified findings + conclusions from papers where this gene is central
        central_papers = [(pid, p) for pid, p in papers_with_gene(symbol)
                          if any(sym == symbol and imp == "central"
                                 for sym, _, imp in p["genes"])]
        gene_findings = [f for _, p in central_papers for f in p["findings"]]
        attach_findings(entry.setdefault("key_findings", []), gene_findings, cap=6)
        attach_methods(entry.setdefault("methods_findings", []), gene_findings, cap=3)
        entry["conclusions"] = [
            {**brief_paper_row(pid, pid_meta_cache.get(pid, {})), "conclusion": c,
             "fh": hashlib.md5(c.encode("utf-8")).hexdigest()[:12]}
            for pid, p in central_papers[:4] for c in p["conclusions"][:1]
        ][:4]

        # Species studied alongside this gene (co-occurrence in central papers)
        co_species = Counter()
        avian_papers = mammal_papers = 0
        for _, p in central_papers:
            has_avian, has_mam = paper_host_flags(p)
            if has_avian:
                avian_papers += 1
            if has_mam:
                mammal_papers += 1
            for cname, _, _, _ in p["species"]:
                co_species[cname] += 1
        entry["species_studied"] = scoped_species(co_species.most_common(), cap=6)
        entry["host_scope"] = host_scope(avian_papers, mammal_papers)
        entry["avian_papers"] = avian_papers
        entry["mammalian_papers"] = mammal_papers
        # Attach known mutations on this gene/protein
        muts = [(c, len(v)) for c, v in mutation_evidence.items()
                if mutation_protein(c) == symbol]
        muts.sort(key=lambda x: -x[1])
        entry["mutations"] = [{"mutation": c, "paper_count": n} for c, n in muts[:10]]
        wiki_genes[symbol] = entry

    # canonical-ID merge (D98 equality): hyphenation/case variants such as
    # "IL-15"/"IL15" or "chTLR1b"/"CHTLR1B" must be ONE wiki entry. Keep
    # the richer entry, union the roles, recompute paper_count from distinct
    # papers. (The frontend dedupes cards the same way; this makes the data
    # itself equal.)
    _canon_sym = lambda s: re.sub(r"[-_\s]", "", s.upper())
    _by_canon: dict[str, str] = {}
    for symbol in sorted(wiki_genes, key=lambda s: -wiki_genes[s]["paper_count"]):
        c = _canon_sym(symbol)
        if c not in _by_canon:
            _by_canon[c] = symbol
            continue
        keep, drop = _by_canon[c], symbol
        tgt, src = wiki_genes[keep], wiki_genes.pop(drop)
        seen_papers = {r.get("paper_id") for r in tgt.get("roles", [])}
        for r in src.get("roles", []):
            if r.get("paper_id") not in seen_papers:
                tgt.setdefault("roles", []).append(r)
                seen_papers.add(r.get("paper_id"))
        all_papers = seen_papers | {r.get("paper_id") for r in src.get("roles", [])}
        tgt["paper_count"] = len({p for p in all_papers if p})
        tgt["central_count"] = max(tgt.get("central_count", 0), src.get("central_count", 0))
        if len(str(src.get("name", ""))) > len(str(tgt.get("name", ""))):
            tgt["name"] = src["name"]
        # richer narrative sections survive; richer entry won the sort above
        for field in ("findings", "conclusions", "mutations"):
            if not tgt.get(field) and src.get(field):
                tgt[field] = src[field]
        merged_wiki_dupes.append((drop, keep))
    if merged_wiki_dupes:
        print(f"[wiki] canonical-ID merges: {len(merged_wiki_dupes)} "
              f"(e.g. {merged_wiki_dupes[:4]})")

    # true papers-with-gene-evidence count (uncapped by the 12-role
    # display cap) — the genes page cites this instead of undercounting
    papers_with_genes = set()
    for pids in gene_paper_sets.values():
        papers_with_genes.update(pids)

    with open(OUT_DIR / "wiki_genes.json", "w") as f:
        json.dump({"generated": str(date.today()), "total_genes": len(wiki_genes),
                   "papers_with_genes": len(papers_with_genes),
                   "genes": wiki_genes}, f, indent=1)

    # ------------------------------------------------------------------
    # Gene-set consistency (D98): the wiki is the canonical gene record.
    # Hard error when a gene that must have a wiki entry lacks one.
    # ------------------------------------------------------------------
    check_gene_set_consistency(wiki_genes, curated)

    # ------------------------------------------------------------------
    # wiki_mutations.json
    # ------------------------------------------------------------------
    wiki_mutations = {}
    known_universe = set(HOST_GENES) | set(VIRAL_PROTEINS) | set(wiki_genes)
    for canon, ev in mutation_evidence.items():
        ev.sort(key=lambda e: -(e["year"] or 0))
        protein = mutation_protein(canon)

        # Skip mutations on proteins outside the known gene universe: these
        # are single-paper extraction noise (primer names like HA3F/SMA3F,
        # unlinked host factors) with no gene page to link to.
        if protein not in known_universe:
            continue

        # Species context: species studied in the papers documenting this mutation
        sp_counts = Counter()
        avian_papers = mammal_papers = 0
        for pid, _ in papers_with_mutation(canon):
            p = papers[pid]
            has_avian, has_mam = paper_host_flags(p)
            if has_avian:
                avian_papers += 1
            if has_mam:
                mammal_papers += 1
            for cname, _, _, _ in p["species"]:
                sp_counts[cname] += 1

        # Findings that explicitly mention this mutation (canonical or alias)
        names = {canon.lower()} | {a.lower() for a in mutation_aliases.get(canon, [])}
        # also normalized without dashes for looser text match
        names |= {n.replace("-", " ").replace(" ", " ") for n in list(names)}
        matched_findings = []
        for pid, p in papers_with_mutation(canon):
            for f in p["findings"]:
                text = (f["finding"] + " " + f["context"]).lower()
                if any(n in text for n in names):
                    matched_findings.append(f)

        # Effect-level host classes (D118): when the claims ledger covers
        # this mutation, host evidence = where the effects were OBSERVED,
        # not which species the paper studied. V598T-in-mice becomes
        # mammalian regardless of the paper's duck rows. Unmined mutations
        # keep the legacy paper-species scope.
        claims = mut_host_claims.get(canon)
        host_scope_src = "paper_species"
        if claims:
            host_scope_src = "effect_claims"
            avian_papers = len(claims.get("aves", set()) | claims.get("both", set()))
            mammal_papers = len(claims.get("mammal", set()) | claims.get("both", set()))
        ev_rows = [{**e, "host_class": paper_mut_host.get((e["paper_id"], canon))}
                   for e in ev]

        wiki_mutations[canon] = {
            "canonical": canon,
            "protein": protein,
            "protein_is_host": protein in HOST_GENES,
            "paper_count": len({e["paper_id"] for e in ev}),
            "host_scope": host_scope(avian_papers, mammal_papers),
            "host_scope_source": host_scope_src,
            "effect_hosts": {k: len(v) for k, v in claims.items()} if claims else None,
            "avian_papers": avian_papers,
            "mammalian_papers": mammal_papers,
            "aliases": sorted(mutation_aliases.get(canon, [])),
            "papers": ev_rows[:15],
            "species_studied": scoped_species(sp_counts.most_common(), cap=6),
        }
        attach_findings(wiki_mutations[canon].setdefault("key_findings", []),
                        matched_findings, cap=5)
        attach_methods(wiki_mutations[canon].setdefault("methods_findings", []),
                       matched_findings, cap=2)

    # Rank: by paper count
    wiki_mutations = dict(sorted(wiki_mutations.items(),
                                key=lambda kv: -kv[1]["paper_count"]))

    # ------------------------------------------------------------------
    # Mammalian-only mutation censorship (2026-11 data-governance rule):
    # mutations whose evidence base is exclusively mammalian stay in the
    # interior private artifact only — never shipped to the web or any
    # downloadable file (wiki_mutations/wiki_index/wiki_genes lists all
    # filtered below). Interior: data/papers/wiki_mutations_private.json.
    # ------------------------------------------------------------------
    _private_muts = {c: m for c, m in wiki_mutations.items()
                     if m["host_scope"] == "mammalian"}
    wiki_mutations = {c: m for c, m in wiki_mutations.items()
                      if m["host_scope"] != "mammalian"}
    (PROJECT_ROOT / "data" / "papers" / "wiki_mutations_private.json").write_text(
        json.dumps({
            "_doc": ("Mammalian-only mutations — censored from every shipped artifact "
                     "(web pages + downloadable JSON/parquet) by data-governance decision "
                     "2026-11. Interior database only; NEVER copy into web/public/data. "
"Full pipeline records (data/papers/records, ledgers) retain everything."),
            "generated": str(date.today()),
            "total": len(_private_muts),
            "mutations": _private_muts,
        }, indent=1))
    if _private_muts:
        print(f"[censor] mammalian-only mutations → private interior file: "
              f"{len(_private_muts)} (shipped: {len(wiki_mutations)})")
        # strip them from per-gene mutation lists (wiki_genes chips)
        _priv_ids = set(_private_muts)
        for entry in wiki_genes.values():
            if entry.get("mutations"):
                entry["mutations"] = [m for m in entry["mutations"]
                                      if m["mutation"] not in _priv_ids]
        with open(OUT_DIR / "wiki_genes.json", "w") as f:
            json.dump({"generated": str(date.today()), "total_genes": len(wiki_genes),
                       "papers_with_genes": len(papers_with_genes),
                       "genes": wiki_genes}, f, indent=1)

    with open(OUT_DIR / "wiki_mutations.json", "w") as f:
        json.dump({"generated": str(date.today()),
                   "total_mutations": len(wiki_mutations),
                   "mutations": wiki_mutations}, f, indent=1)

    # ------------------------------------------------------------------
    # wiki_species.json
    # ------------------------------------------------------------------
    # Fold canonicals that resolve to the same scientific name (synonyms and
    # common/binomial variants outside SPECIES_CANON) into one entry.
    # Target = SPECIES_CANON canonical if present, else the name with the
    # most evidence rows. (2026-10-30 paper-audit fix: duplicates made
    # per-species paper counts unusable.)
    _canon_names = {c for c, _s, _a in SPECIES_CANON.values()}
    _sci_groups = defaultdict(list)
    for _cn in list(species_evidence):
        _sci = species_meta.get(_cn, (None, None))[0]
        _sci_groups[(_sci or _cn).lower()].append(_cn)
    _merged = 0
    for _key, _names in _sci_groups.items():
        if len(_names) < 2:
            continue
        _names.sort(key=lambda n: (n in _canon_names, len(species_evidence[n])), reverse=True)
        _target, _rest = _names[0], _names[1:]
        for _src in _rest:
            species_evidence[_target].extend(species_evidence.pop(_src))
            _src_sci, _src_av = species_meta.get(_src, (None, None))
            _t_sci, _t_av = species_meta.get(_target, (None, None))
            species_meta[_target] = (_t_sci or _src_sci,
                                     _t_av if _t_av is not None else _src_av)
            _merged += 1
    if _merged:
        print(f"[wiki] folded {_merged} duplicate-species canonicals by scientific name")

    wiki_species = {}
    for cname, ev in species_evidence.items():
        paper_ids = {e["paper_id"] for e in ev}
        if len(paper_ids) < 2:
            continue
        sci, avian = species_meta.get(cname, (None, None))
        status_counts = defaultdict(int)
        for e in ev:
            status_counts[e["infection_status"]] += 1
        ev.sort(key=lambda e: -(e["year"] or 0))

        sp_papers = papers_with_species(cname)
        study_types = Counter(p["study_type"] for _, p in sp_papers if p["study_type"])
        sp_findings = [f for _, p in sp_papers for f in p["findings"]]
        sp_conclusions = [
            {**brief_paper_row(pid, pid_meta_cache.get(pid, {})), "conclusion": c}
            for pid, p in sp_papers for c in p["conclusions"][:1]
        ][:4]
        sp_claims = [
            {**brief_paper_row(pid, pid_meta_cache.get(pid, {})), "claim": claim}
            for pid, p in sp_papers for claim in p["novel_claims"][:1]
        ][:3]

        wiki_species[cname] = {
            "canonical": cname,
            "scientific_name": sci,
            "avian": avian,
            "paper_count": len(paper_ids),
            "evidence_count": len(ev),
            "status_counts": dict(status_counts),
            "evidence": ev[:15],
            "study_types": dict(study_types),
            "conclusions": sp_conclusions,
            "notable_claims": sp_claims,
        }
        attach_findings(wiki_species[cname].setdefault("key_findings", []),
                        sp_findings, cap=6)
        attach_methods(wiki_species[cname].setdefault("methods_findings", []),
                       sp_findings, cap=3)
    wiki_species = dict(sorted(wiki_species.items(),
                               key=lambda kv: -kv[1]["paper_count"]))

    # Report residual canonicals sharing a scientific name (designed generics
    # like Duck/Mallard are allowed, but the build should say so).
    by_sci = defaultdict(list)
    for cname, v in wiki_species.items():
        if v.get("scientific_name"):
            by_sci[v["scientific_name"].lower()].append((cname, v["paper_count"]))
    dups = {sci: rows for sci, rows in by_sci.items() if len(rows) > 1}
    if dups:
        print(f"[wiki] {len(dups)} scientific names carry multiple canonicals:")
        for sci, rows in sorted(dups.items(), key=lambda kv: -sum(r[1] for r in kv[1]))[:8]:
            print(f"   {sci}: {rows}")

    with open(OUT_DIR / "wiki_species.json", "w") as f:
        json.dump({"generated": str(date.today()),
                   "total_species": len(wiki_species),
                   "species": wiki_species}, f, indent=1)

    # ------------------------------------------------------------------
    # species_wiki_supplement.json — index entries for species referenced
    # by the wiki (gene/mutation "studied in" chips, wiki species pages)
    # that are NOT resolvable in species_index.json (mammals, generics).
    # The frontend merges these into the search/modal index so every
    # species link resolves to a page.
    # ------------------------------------------------------------------
    species_index_path = OUT_DIR / "species_index.json"
    try:
        with open(species_index_path) as f:
            species_index = json.load(f)
        index_com = {str(s.get("com", "")).lower() for s in species_index if s.get("com")}
        index_sci = {str(s.get("sci", "")).lower() for s in species_index if s.get("sci")}
    except (OSError, json.JSONDecodeError):
        species_index, index_com, index_sci = [], set(), set()

    referenced = {}  # canonical name → (scientific, avian)
    for cname, rec in wiki_species.items():
        referenced[cname] = (rec.get("scientific_name"), rec.get("avian"))
    for g in wiki_genes.values():
        for s in g.get("species_studied", []):
            referenced.setdefault(s["name"], (s.get("scientific"), s.get("avian")))
    for m in wiki_mutations.values():
        for s in m.get("species_studied", []):
            referenced.setdefault(s["name"], (s.get("scientific"), s.get("avian")))

    supplement = []
    seen_canon = set()  # case-insensitive dedupe ONLY (exact names must all resolve)
    for cname, (sci, avian) in sorted(referenced.items()):
        keys = {cname.lower()} | {sci.lower() for sci in [sci] if sci}
        if keys & (index_com | index_sci):
            continue  # already resolvable
        canon_key = cname.lower()
        if canon_key in seen_canon:
            continue
        seen_canon.add(canon_key)
        supplement.append({
            "id": None,
            "sci": sci or cname,
            "com": cname,
            "ord": "Mammalia" if avian is False else ("Aves" if avian else None),
            "fam": None,
            "det": 0,
            "iucn": None,
            "wiki_only": True,
            "mammal": avian is False,
        })

    # Also include species from the gene-presence pipeline (they have genomes
    # + gene panel data but may lack H5N1 detections — e.g. kākāpō).
    # Common names + assembly metadata come from the genomes manifest so
    # every searched species is searchable by name and shows its assembly
    # badge; the macron NZ spellings override the manifest's plain ASCII.
    COMMON_NAMES = {
        "strigops habroptila": "kākāpō",
        "strigops habroptilus": "kākāpō",  # legacy spelling (D101)
        "porphyrio hochstetteri": "takahē",
        "nestor notabilis": "kea",
        "nestor meridionalis": "kākā",
        "apteryx mantelli": "north island brown kiwi",
        "apteryx rowi": "rowi",
        "apteryx haastii": "great spotted kiwi",
        "apteryx owenii": "little spotted kiwi",
        "apteryx australis": "southern brown kiwi",
        "megadyptes antipodes antipodes": "yellow-eyed penguin/hoiho",
        "megadyptes antipodes": "yellow-eyed penguin/hoiho",
        "cyanoramphus novaezelandiae": "red-crowned kākāriki",
        "cyanoramphus auriceps": "yellow-crowned kākāriki",
        "gallirallus australis": "weka",
        "hymenolaimus malacorhynchos": "whio/blue duck",
        "notiomystis cincta": "hihi/stitchbird",
        "taeniopygia guttata": "zebra finch",
        "meleagris gallopavo": "wild turkey",
    }
    manifest_meta = {}
    manifest_path = PROJECT_ROOT / "data" / "genomes" / "genomes.json"
    if manifest_path.exists():
        try:
            for g in json.loads(manifest_path.read_text())["genomes"]:
                manifest_meta[g["species"].lower()] = {
                    "common": g.get("common", ""),
                    "accession": g.get("accession"),
                    "level": g.get("assembly_level"),
                    "role": g.get("role", ""),
                }
        except (OSError, json.JSONDecodeError):
            pass
    presence_path = PROJECT_ROOT / "data" / "genes" / "gene_presence_v2.jsonl"
    if presence_path.exists():
        presence_species = set()
        for line in presence_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                c = json.loads(line)
                if c.get("species"):
                    presence_species.add(c["species"])
            except json.JSONDecodeError:
                continue
        for sp in sorted(presence_species):
            sp_lower = sp.lower()
            if sp_lower in seen_canon:
                continue
            if sp_lower in index_sci or sp_lower in index_com:
                continue  # already in detection index
            seen_canon.add(sp_lower)
            meta = manifest_meta.get(sp_lower, {})
            is_mammal = str(meta.get("role", "")).startswith("mammal")
            supplement.append({
                "id": None,
                "sci": sp,
                "com": COMMON_NAMES.get(sp_lower) or meta.get("common", ""),
                "ord": "Mammalia" if is_mammal else "Aves",
                "fam": None,
                "det": 0,
                "iucn": None,
                "wiki_only": True,
                "mammal": is_mammal,
                "has_genome": True,
                "genome_species": True,
                "genome_acc": meta.get("accession"),
                "genome_level": meta.get("level"),
            })

    with open(OUT_DIR / "species_wiki_supplement.json", "w") as f:        json.dump(supplement, f, indent=1)

    # ------------------------------------------------------------------
    # wiki_index.json — compact search index
    # ------------------------------------------------------------------
    # gene evidence sidecar — raw counts for coverage reporting (D39):
    # every symbol with ANY evidence (studied / alias / text-mention),
    # independent of the >=2-paper wiki page threshold
    gene_evidence_counts = {}
    for sym, rows in gene_evidence.items():
        studied = {r["paper_id"] for r in rows if r.get("via") != "text_scan" and not r.get("via_alias")}
        aliased = {r["paper_id"] for r in rows if r.get("via_alias")}
        textonly = {r["paper_id"] for r in rows if r.get("via") == "text_scan"}
        gene_evidence_counts[sym] = {
            "papers": len(studied | aliased | textonly),
            "studied": len(studied),
            "via_alias": len(aliased),
            "text_only": len(textonly),
        }
    (PROJECT_ROOT / "data" / "papers" / "gene_evidence_counts.json").write_text(json.dumps(gene_evidence_counts, indent=1))

    # ------------------------------------------------------------------
    # Reviewed connection context (D78 item 25): published relationship
    # data flows into wiki exports + the global-search index. Counts and
    # counterpart symbols only — no new prose, so translation hashes for
    # findings/roles/conclusions stay consistent.
    # ------------------------------------------------------------------
    reviewed_conn = {}
    rel_path = OUT_DIR / "gene_relationships.json"
    if rel_path.exists():
        try:
            for e in json.loads(rel_path.read_text()).get("edges", []):
                if not e.get("evidence"):
                    continue
                for sym, other in ((e["from"], e["to"]), (e["to"], e["from"])):
                    c = reviewed_conn.setdefault(sym, {"connections": 0,
                                                       "evidence": 0,
                                                       "counterparts": []})
                    c["connections"] += 1
                    c["evidence"] += len(e["evidence"])
                    if other not in c["counterparts"]:
                        c["counterparts"].append(other)
        except Exception:
            pass
    for sym, entry in wiki_genes.items():
        if sym in reviewed_conn:
            entry["reviewed_connections"] = {
                "connections": reviewed_conn[sym]["connections"],
                "evidence": reviewed_conn[sym]["evidence"],
                "counterparts": reviewed_conn[sym]["counterparts"][:8],
            }

    wiki_index = {
        "generated": str(date.today()),
        "genes": [
            {"symbol": s, "category": g["category"], "kind": g.get("kind", "host"),
             "paper_count": g["paper_count"],
             "central_count": g["central_count"], "host_scope": g.get("host_scope"),
             "reviewed_connections": g.get("reviewed_connections", {}).get("connections", 0)}
            for s, g in sorted(wiki_genes.items(), key=lambda kv: -kv[1]["paper_count"])
        ],
        "mutations": [
            {"canonical": c, "protein": m["protein"], "paper_count": m["paper_count"],
             "host_scope": m["host_scope"]}
            for c, m in list(wiki_mutations.items())[:200]
        ],
        "species": [
            {"name": n, "scientific_name": s.get("scientific_name"),
             "paper_count": s["paper_count"], "avian": s["avian"]}
            for n, s in list(wiki_species.items())[:200]
        ],
    }
    with open(OUT_DIR / "wiki_index.json", "w") as f:
        json.dump(wiki_index, f, indent=1)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print(f"Wiki pages built from {len(analyses)} LLM analyses")
    print(f"  genes:     {len(wiki_genes)} (>=2 papers or curated)")
    print(f"  mutations: {len(wiki_mutations)}")
    print(f"  species:   {len(wiki_species)} (>=2 papers)")

    scope_counts = Counter(m["host_scope"] for m in wiki_mutations.values())
    print(f"\nMutation host scope: {dict(scope_counts)}")
    n_effect_scoped = sum(1 for m in wiki_mutations.values()
                          if m.get("host_scope_source") == "effect_claims")
    n_mammal_only = scope_counts.get("mammalian", 0)
    print(f"  effect-level host classes (mutation_host_claims ledger): "
          f"{n_effect_scoped}/{len(wiki_mutations)} mutations")
    if n_effect_scoped:
        print(f"  mammalian-only mutations CENSORED from shipped artifacts "
              f"(private interior file): {n_mammal_only}")
    gene_scopes = Counter(g.get("host_scope") for g in wiki_genes.values())
    print(f"Gene literature scope: {dict(gene_scopes)}")
    avian_species = sum(1 for s in wiki_species.values() if s["avian"] is True)
    mammal_species = sum(1 for s in wiki_species.values() if s["avian"] is False)
    print(f"Species: {avian_species} avian / {mammal_species} mammalian / "
          f"{len(wiki_species) - avian_species - mammal_species} unknown")

    top_genes = sorted(wiki_genes.items(), key=lambda kv: -kv[1]["paper_count"])[:10]
    print("\nTop genes:")
    for s, g in top_genes:
        print(f"  {s:10s} {g['paper_count']:3d} papers ({g['central_count']} central)")

    top_muts = list(wiki_mutations.items())[:10]
    print("\nTop mutations:")
    for c, m in top_muts:
        print(f"  {c:18s} {m['paper_count']:3d} papers")

    top_species = list(wiki_species.items())[:10]
    print("\nTop species:")
    for n, s in top_species:
        print(f"  {n:28s} {s['paper_count']:3d} papers, statuses={s['status_counts']}")


if __name__ == "__main__":
    main()

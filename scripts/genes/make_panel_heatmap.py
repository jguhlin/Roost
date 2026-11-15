#!/usr/bin/env python3
"""
Build static phylogeny + gene-panel heatmap figures (self-contained HTML).

Two versions are written to figures/:
  gene_panel_heatmap_observed.html — genome-searched bird species only
  gene_panel_heatmap_imputed.html  — adds HPAI-detected birds without a
      searched genome; missing values are imputed from the phylogenetically
      nearest species with an observed call for that gene. Fully imputed
      species carry a diamond at the label + hatch overlay; partially
      imputed cells get a diamond outline.

Design ("cluster by severity/literature"):
  rows  = species, ordered by a pruned BirdTree (Ericson) phylogeny
  cols  = individual genes for the literature core (critical + tier-1 +
          high-importance), aggregate % columns for tier-2 categories and
          the tier-3 immune block, plus a whole-panel summary column
  color = % of column genes FULL (FRAGMENT counts 1/2), viridis ramp
  top   = per-column prevalence across displayed species

Usage: pixi run python scripts/genes/make_panel_heatmap.py
Output: figures/*.html (static files; NOT part of the served web app)
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT_DIR = ROOT / "figures"

# Importance sets mirror scripts/genes/export_presence.py (single source of
# truth for the "severity/literature" flags shown in the portal).
CRITICAL = {"DDX58", "IFIH1", "ANP32A"}
HIGH = {
    "ANP32B", "ANP32E", "MX1", "IFIT5", "IFITM3", "OASL", "RSAD2",
    "STAT1", "STAT2", "TLR3", "TLR7", "TLR21", "MAVS", "IRF3", "IRF7",
    "TRIM25", "IFNB1", "IFNA4",
}

# Current/NCBI names -> BirdTree (Jetz et al. 2012) tip names. Anything not
# covered falls back to grafting onto the genus (or family) LCA in the tree.
SYNONYMS = {
    "Agropsar sturninus": "Sturnus_sturninus",
    "Ammospiza caudacuta": "Ammodramus_caudacutus",
    "Ammospiza nelsoni": "Ammodramus_nelsoni",
    "Anarhynchus alexandrinus": "Charadrius_alexandrinus",
    "Anarhynchus nivosus": "Charadrius_nivosus",
    "Anser caerulescens": "Chen_caerulescens",
    "Anser canagicus": "Chen_canagica",
    "Anser rossii": "Chen_rossii",
    "Anser serrirostris": "Anser_fabalis",
    "Antigone canadensis": "Grus_canadensis",
    "Antigone vipio": "Grus_vipio",
    "Anthropoides paradiseus": "Grus_paradisea",
    "Anthropoides virgo": "Grus_virgo",
    "Apteryx rowi": "Apteryx_mantelli",          # rowi split from mantelli
    "Ardea alba": "Egretta_alba",
    "Ardea intermedia": "Mesophoyx_intermedia",
    "Ardenna gravis": "Puffinus_gravis",
    "Ardenna grisea": "Puffinus_griseus",
    "Ardenna pacifica": "Puffinus_pacificus",
    "Ardenna tenuirostris": "Puffinus_tenuirostris",
    "Astur atricapillus": "Accipiter_gentilis",
    "Astur atricapillus atricapillus": "Accipiter_gentilis",
    "Astur gentilis": "Accipiter_gentilis",
    "Bubo blakistoni": "Bubo_bubo",
    "Bubo scandiacus": "Bubo_scandiacus",          # may graft if absent
    "Buteo japonicus": "Buteo_buteo",
    "Calidris pugnax": "Philomachus_pugnax",
    "Calonectris borealis": "Calonectris_diomedea",
    "Chlamydotis macqueenii": "Chlamydotis_undulata",
    "Chloris chloris": "Carduelis_chloris",
    "Chroicocephalus brunnicephalus": "Larus_brunnicephalus",
    "Chroicocephalus cirrocephalus": "Larus_cirrocephalus",
    "Chroicocephalus genei": "Larus_genei",
    "Chroicocephalus hartlaubii": "Larus_hartlaubii",
    "Chroicocephalus maculipennis": "Larus_maculipennis",
    "Chroicocephalus novaehollandiae": "Larus_novaehollandiae",
    "Chroicocephalus philadelphia": "Larus_philadelphia",
    "Chroicocephalus ridibundus": "Larus_ridibundus",
    "Chroicocephalus saundersi": "Larus_saundersi",
    "Chroicocephalus scopulinus": "Larus_scopulinus",
    "Circus hudsonius": "Circus_cyaneus",
    "Clanga clanga": "Aquila_clanga",
    "Corvus cornix": "Corvus_corone",
    "Corvus cornix cornix": "Corvus_corone",
    "Cygnus bewickii": "Cygnus_columbianus",
    "Geothlypis tolmiei": "Oporornis_tolmiei",
    "Geranoaetus polyosoma": "Buteo_polyosoma",
    "Larus smithsonianus": "Larus_argentatus",
    "Larus vegae": "Larus_argentatus",
}


# --------------------------------------------------------------------------- #
# Newick parsing / tree utilities (pure python)
# --------------------------------------------------------------------------- #
class Node:
    __slots__ = ("children", "length", "name", "depth", "y", "cnt")

    def __init__(self, name=None, length=0.0):
        self.children = []
        self.name = name
        self.length = length
        self.depth = 0
        self.y = 0.0

    @property
    def is_leaf(self):
        return not self.children


def parse_newick(text):
    """Parse a single Newick tree (branch lengths + internal labels)."""
    tokens = re.findall(r"[();,]|[^();,]+", text.strip().rstrip(";"))
    pos = 0

    def parse_node():
        nonlocal pos
        node = Node()
        if tokens[pos] == "(":
            pos += 1
            while True:
                node.children.append(parse_node())
                if tokens[pos] == ",":
                    pos += 1
                    continue
                if tokens[pos] == ")":
                    pos += 1
                    break
        if pos < len(tokens) and tokens[pos] not in "(),;":
            label = tokens[pos].strip()
            pos += 1
            if ":" in label:
                name, _, ln = label.partition(":")
                node.name = name or None
                try:
                    node.length = float(ln)
                except ValueError:
                    node.length = 0.0
            else:
                node.name = label or None
        return node

    node = parse_node()
    pos += 1  # trailing ';'
    return node


def prune_to(node, keep):
    """Drop leaves not in `keep`; suppress unary internal nodes."""
    if node.is_leaf:
        return node if node.name in keep else None
    kept = [c for c in (prune_to(ch, keep) for ch in node.children) if c]
    if not kept:
        return None
    if len(kept) == 1:
        kept[0].length += node.length
        return kept[0]
    node.children = kept
    return node


def ladderize(node):
    """Reorder children by subtree leaf count (right-heavy)."""
    if node.is_leaf:
        return 1
    pairs = [(ladderize(c), c) for c in node.children]
    node.children = [c for _, c in sorted(pairs, key=lambda p: p[0])]
    return sum(n for n, _ in pairs)


def leaf_order(node, out):
    if node.is_leaf:
        out.append(node)
    for c in node.children:
        leaf_order(c, out)


def assign_layout(node, depth=0):
    """Topological depth + y (leaf = rank, internal = mean of children)."""
    node.depth = depth
    if node.is_leaf:
        node.y = assign_layout.leaf_count
        assign_layout.leaf_count += 1
    else:
        ys = [assign_layout(c, depth + 1) for c in node.children]
        node.y = sum(ys) / len(ys)
    return node.y


def tree_edges(node, h_out, v_out):
    """Rectangular-layout segments: horizontal per child, vertical per node."""
    if not node.is_leaf:
        ys = [c.y for c in node.children]
        if len(ys) > 1:
            v_out.append((node.depth, min(ys), max(ys)))
        for c in node.children:
            h_out.append((node.depth, c.y, c.depth))
            tree_edges(c, h_out, v_out)


def lca_of_names(root, names):
    """Minimal node whose subtree contains all named tips (or None).

    Counts names anywhere in the subtree (not just leaves): a grafted-on
    species can turn a former tip into an internal node, and that node must
    still count as "found" for subsequent LCA lookups.
    """
    def dfs(n):
        cnt = 1 if n.name in names else 0
        for c in n.children:
            cnt += dfs(c)
        n.cnt = cnt
        return cnt

    total = len(names)
    if dfs(root) != total:
        return None
    n = root
    while True:
        nxt = next((c for c in n.children if c.cnt == total), None)
        if nxt is None:
            return n
        n = nxt


def compute_root_distances(node, d=0.0, out=None):
    out = out if out is not None else {}
    dd = d + node.length
    out[id(node)] = dd
    for c in node.children:
        compute_root_distances(c, dd, out)
    return out


def patristic(u, v, rdist, parent):
    anc = set()
    x = u
    while x is not None:
        anc.add(id(x))
        x = parent.get(id(x))
    y = v
    while y is not None and id(y) not in anc:
        y = parent.get(id(y))
    if y is None:
        return float("inf")
    return rdist[id(u)] + rdist[id(v)] - 2 * rdist[id(y)]


# --------------------------------------------------------------------------- #
# Main build
# --------------------------------------------------------------------------- #
# Common-name gloss for the order-level view (fallback = scientific name)
ORDER_COMMON = {
    "Anseriformes": "waterfowl", "Galliformes": "gamebirds",
    "Charadriiformes": "shorebirds & gulls", "Passeriformes": "perching birds",
    "Accipitriformes": "hawks, eagles & vultures", "Cathartiformes": "new-world vultures",
    "Piciformes": "woodpeckers & allies", "Psittaciformes": "parrots",
    "Columbiformes": "pigeons & doves", "Apodiformes": "swifts & hummingbirds",
    "Strigiformes": "owls", "Falconiformes": "falcons",
    "Pelecaniformes": "ibises & herons", "Suliformes": "frigatebirds & cormorants",
    "Procellariiformes": "albatrosses & petrels", "Sphenisciformes": "penguins",
    "Gaviiformes": "loons", "Podicipediformes": "grebes",
    "Phoenicopteriformes": "flamingos", "Ciconiiformes": "storks",
    "Gruiformes": "cranes & rails", "Otidiformes": "bustards",
    "Cuculiformes": "cuckoos", "Caprimulgiformes": "nightjars & allies",
    "Coraciiformes": "kingfishers & rollers", "Bucerotiformes": "hoopoes & hornbills",
    "Trogoniformes": "trogons", "Coliiformes": "mousebirds",
    "Cariamiformes": "seriemas", "Tinamiformes": "tinamous",
    "Rheiformes": "rheas", "Casuariiformes": "emus & cassowaries",
    "Struthioniformes": "ostrich", "Apterygiformes": "kiwis",
    "Phaethontiformes": "tropicbirds", "Pterocliformes": "sandgrouse",
    "Mesitornithiformes": "mesites", "Eurypygiformes": "kagu & sunbittern",
    "Opisthocomiformes": "hoatzin", "Musophagiformes": "turacos",
    "Aegotheliformes": "owlet-nightjars", "Nyctibiiformes": "potoos",
    "Steatornithiformes": "oilbird", "Podargiformes": "frogmouths",
}


def main():
    OUT_DIR.mkdir(exist_ok=True)
    taxinfo = {t["scientific_name"]: t for t in pl.read_csv(
        DATA / "aves_taxonomy.tsv", separator="\t"
    ).select(["scientific_name", "common_name", "order", "family"]).to_dicts()}
    genus_family = {s.split()[0]: t["family"] for s, t in taxinfo.items()}

    calls = pl.read_parquet(DATA / "genes" / "gene_presence_v2.parquet")
    panel_version = calls["panel_version"].max()
    calls = calls.filter(pl.col("panel_version") == panel_version)
    panel_gene = {g["symbol"]: g for g in json.load(
        open(DATA / "genes" / "host_panel_v2.json"))["genes"]}
    call_date = str(calls["call_date"].max())

    STATUS = {"NOT_FOUND": 0, "FRAGMENT": 1, "FULL": 2}
    observed = defaultdict(dict)
    for sp, gene, st in calls.select(
            ["species", "gene_symbol", "search_status"]).iter_rows():
        observed[sp][gene] = STATUS[st]
    searched_birds = {s for s in observed if s in taxinfo}
    genes_with_calls = sorted({g for sp in observed.values() for g in sp})

    # ---------------- column spec ------------------------------------------
    cols, shown = [], set()
    for sym in ["ANP32A", "DDX58", "IFIH1"]:           # critical, led by ANP32A
        if sym in genes_with_calls:
            cols.append(dict(id=sym, label=sym, kind="gene", group="Critical", tier=1))
            shown.add(sym)
    for cat in ["Dependency", "Sensor", "Effector", "Signaling", "Tolerance"]:
        for sym in sorted(panel_gene):
            g = panel_gene[sym]
            if g["tier"] == 1 and g["category"] == cat \
                    and sym in genes_with_calls and sym not in shown:
                cols.append(dict(id=sym, label=sym, kind="gene",
                                 group=f"Tier-1 · {cat}", tier=1))
                shown.add(sym)
    for sym in sorted(HIGH):
        if sym in genes_with_calls and sym not in shown:
            cols.append(dict(id=sym, label=sym, kind="gene", group="High importance",
                             tier=panel_gene.get(sym, {}).get("tier", 2)))
            shown.add(sym)

    rest = [g for g in genes_with_calls if g not in shown]
    buckets = defaultdict(list)
    for sym in rest:
        g = panel_gene.get(sym, {})
        if g.get("tier") == 3:
            buckets["Tier-3 · Immune (GO)"].append(sym)
        else:
            buckets[f"Tier-2 · {g.get('category', 'Host Gene')}"].append(sym)

    def bucket_key(grp):
        tier = 3 if grp.startswith("Tier-3") else 2
        return (tier, -len(buckets[grp]))

    for grp in sorted(buckets, key=bucket_key):
        cols.append(dict(
            id="agg_" + re.sub(r"[^a-z0-9]+", "_", grp.lower()).strip("_"),
            label=grp.split("· ")[1] + f" ({len(buckets[grp])})",
            kind="agg", group=grp, tier=2 if grp.startswith("Tier-2") else 3,
            genes=buckets[grp]))
    cols.append(dict(id="full_panel",
                     label=f"FULL PANEL ({len(genes_with_calls)})",
                     kind="summary", group="Summary", tier=0,
                     genes=list(genes_with_calls)))

    # ---------------- tree + name matching ---------------------------------
    with open(DATA / "birdtree_ericson.tre") as f:
        chunk = f.read(3_000_000)
    newick = chunk[: chunk.index(";") + 1]
    all_tips = set()

    def fresh_tree_with_tips():
        t = parse_newick(newick)
        lv = []
        leaf_order(t, lv)
        all_tips.clear()
        all_tips.update(n.name for n in lv)
        return t

    def match(sci):
        if " sp." in sci or " cf." in sci:
            return None, "dropped"
        n = sci.replace(" ", "_")
        if n in all_tips:
            return n, "exact"
        parts = sci.split()
        if len(parts) > 2 and "_".join(parts[:2]) in all_tips:
            return "_".join(parts[:2]), "trinomial"
        if SYNONYMS.get(sci) in all_tips:
            return SYNONYMS[sci], "synonym"
        return None, "unmatched"

    detected = pl.read_parquet(DATA / "species_profiles_detected.parquet")
    det_counts = {r["scientific_name"]: r["detection_count"]
                  for r in detected.to_dicts()}
    impute_cands = {s for s in det_counts
                    if s in taxinfo and s not in searched_birds}
    all_species = sorted(searched_birds | impute_cands)

    fresh_tree_with_tips()  # populate all_tips for matching
    name2tip, match_kind = {}, {}
    unmatched = []
    nongranular = []
    for s in all_species:
        t, kind = match(s)
        if t is None:
            if kind == "dropped":          # 'sp.'/'cf.' — not a species
                match_kind[s] = "dropped"
                nongranular.append(s)
            else:
                unmatched.append(s)
        else:
            name2tip[s] = t
            match_kind[s] = kind
    if nongranular:
        print("non-species records excluded:", nongranular)

    genus_tips = defaultdict(set)
    for t in all_tips:
        genus_tips[t.split("_")[0]].add(t)
    family_genera = defaultdict(set)
    for g, fam in genus_family.items():
        family_genera[fam].add(g)

    def graft(tree, sci, diag=False):
        """Attach an unmatched species under its genus (or family) LCA."""
        genus = sci.split()[0]
        fam = taxinfo[sci]["family"]
        anchors = genus_tips.get(genus)
        if not anchors:
            anchors = {t for g in family_genera.get(fam, ())
                       for t in genus_tips.get(g, ())}
            if not anchors:
                if diag: print(f"    graft fail {sci}: no anchors (fam={fam!r})")
                return None
        target = lca_of_names(tree, anchors)
        if target is None:
            if diag: print(f"    graft fail {sci}: LCA not found "
                           f"({len(anchors)} anchors, fam={fam!r})")
            return None
        leaf = Node(sci.replace(" ", "_"), length=1.0)
        target.children.append(leaf)
        return leaf.name

    grafted_probe = []
    for s in unmatched:
        # graft() attaches a tip named after the species itself under its
        # genus/family LCA; record the name now so set ops see it
        match_kind[s] = "grafted"
        name2tip[s] = s.replace(" ", "_")
        grafted_probe.append(s)

    # tip-name collisions (e.g. Astur gentilis + Astur atricapillus ->
    # Accipiter_gentilis): keep the best-resolved species per tip
    by_tip = defaultdict(list)
    for s, t in name2tip.items():
        by_tip[t].append(s)
    collisions = {t: ss for t, ss in by_tip.items() if len(ss) > 1}
    for t, ss in collisions.items():
        ss.sort(key=lambda s: (s in searched_birds, det_counts.get(s, 0),
                               len(observed.get(s, {}))), reverse=True)
        for s in ss[1:]:
            match_kind[s] = "dropped"
    if collisions:
        print(f"tip collisions resolved ({len(collisions)} tips): " +
              "; ".join(f"{t}: kept {ss[0]}" for t, ss in collisions.items()))

    def build_version(species_set):
        tree = fresh_tree_with_tips()
        still_dropped = []
        for s in species_set:
            if match_kind[s] == "grafted":
                if graft(tree, s, diag=True) is None:
                    still_dropped.append(s)
        for s in still_dropped:
            match_kind[s] = "dropped"
        species_set = {s for s in species_set if match_kind[s] != "dropped"}
        keep = {name2tip[s] for s in species_set}
        tree = prune_to(tree, keep)
        ladderize(tree)
        assign_layout.leaf_count = 0
        assign_layout(tree)
        leaves = []
        leaf_order(tree, leaves)
        h_edges, v_edges = [], []
        tree_edges(tree, h_edges, v_edges)
        name_of_tip = {lf.name for lf in leaves}
        tip2sp = {name2tip[s]: s for s in species_set if name2tip[s] in name_of_tip}
        ordered = [tip2sp[lf.name] for lf in leaves]
        max_depth = max((e[2] for e in h_edges), default=1)
        return dict(h=h_edges, v=v_edges, max_depth=max_depth), ordered, tree

    treeA, orderA, _ = build_version(set(searched_birds) & set(name2tip))
    treeB, orderB, treeB_nodes = build_version({s for s in all_species if s in name2tip})

    n_exact = sum(1 for v in match_kind.values() if v in ("exact", "trinomial", "synonym"))
    n_gr = sum(1 for v in match_kind.values() if v == "grafted")
    n_dr = sum(1 for v in match_kind.values() if v == "dropped")
    dropped_list = [s for s, v in match_kind.items() if v == "dropped"]
    print(f"tree matching: {n_exact} direct, {n_gr} grafted, {n_dr} dropped")
    if dropped_list:
        print("  dropped:", dropped_list)

    # ---------------- imputation machinery (on version-B tree) -------------
    treeF = fresh_tree_with_tips()
    for s in orderB:
        if match_kind[s] == "grafted":
            graft(treeF, s)
    keepB = {name2tip[s] for s in orderB}
    treeF = prune_to(treeF, keepB)
    ladderize(treeF)
    assign_layout.leaf_count = 0
    assign_layout(treeF)

    parent, node_of_tip = {}, {}
    stack = [(treeF, None)]
    while stack:
        n, p = stack.pop()
        parent[id(n)] = p
        if n.is_leaf:
            node_of_tip[n.name] = n
        for c in n.children:
            stack.append((c, n))
    rdist = compute_root_distances(treeF)

    # coverage signatures: genes share a donor set in practice
    sig_id, sigs = {}, []
    for g in genes_with_calls:
        sig = frozenset(s for s in searched_birds if g in observed[s])
        if sig not in sigs:
            sigs.append(sig)
        sig_id[g] = sigs.index(sig)
    searched_sorted = sorted(searched_birds)

    def ranked_donors(tip_name):
        u = node_of_tip[tip_name]
        out = []
        for s2 in searched_sorted:
            t2 = name2tip[s2]
            if t2 not in node_of_tip:
                continue  # donor dropped from this tree (collision/graft fail)
            d = patristic(u, node_of_tip[t2], rdist, parent)
            out.append((d, s2))
        out.sort(key=lambda x: x[0])
        return out

    def impute_row(species):
        ranked = ranked_donors(name2tip[species])
        obs_row = observed.get(species, {})
        # first ranked donor satisfying each coverage signature
        sig_donor = [None] * len(sigs)
        for d, s2 in ranked:
            for si, sig in enumerate(sigs):
                if sig_donor[si] is None and s2 in sig:
                    sig_donor[si] = s2
        row, flags = dict(obs_row), {}
        for gene in genes_with_calls:
            if gene in row:
                continue
            donor = sig_donor[sig_id[gene]]
            if donor is not None and gene in observed[donor]:
                row[gene] = observed[donor][gene]
                flags[gene] = 1
        return row, flags

    def build_rows(species_list, allow_impute):
        rows, imputed_cache = [], {}
        for s in species_list:
            if s in searched_birds:
                obs_row, flags = dict(observed[s]), {}
                if allow_impute:
                    row, flags = impute_row(s)
                else:
                    row = obs_row
            else:
                if s not in imputed_cache:
                    imputed_cache[s] = impute_row(s)
                row, flags = imputed_cache[s]
            vals, cell_imp = [], []
            for c in cols:
                if c["kind"] == "gene":
                    v = row.get(c["id"])
                    vals.append(None if v is None else 50.0 * v)
                    cell_imp.append(1 if c["id"] in flags else 0)
                else:
                    vs = [row[g] for g in c["genes"] if g in row]
                    vals.append(100.0 * sum(vs) / (2 * len(vs)) if vs else None)
                    cell_imp.append(1 if any(g in flags for g in c["genes"]) else 0)
            ti = taxinfo[s]
            rows.append(dict(sci=s, common=ti["common_name"] or s,
                             order=ti["order"], family=ti["family"],
                             searched=s in searched_birds,
                             n_obs=len(observed.get(s, {})),
                             detections=det_counts.get(s, 0),
                             vals=[None if v is None else round(v) for v in vals],
                             cell_imp=cell_imp))
        return rows

    rowsA = build_rows(orderA, allow_impute=False)
    rowsB = build_rows(orderB, allow_impute=True)

    # ---------------- clade-collapsed view (order / family) ------------------
    def build_clade(level, clade_of):
        """Aggregate phylo-ordered rowsB into clades; mini-tree from treeB."""
        groups, seen = [], {}
        for r in rowsB:
            key = clade_of(r) or "(unclassified)"
            if key not in seen:
                seen[key] = len(groups)
                groups.append(dict(name=key, rows=[], tip=name2tip[r["sci"]]))
            groups[seen[key]]["rows"].append(r)
        for g in groups:
            obs = [r for r in g["rows"] if r["searched"]]
            imp = [r for r in g["rows"] if not r["searched"]]
            vals_obs, vals_imp = [], []
            for ci in range(len(cols)):
                vo = [r["vals"][ci] for r in obs if r["vals"][ci] is not None]
                vi = [r["vals"][ci] for r in imp if r["vals"][ci] is not None]
                vals_obs.append(round(sum(vo) / len(vo)) if vo else None)
                vals_imp.append(round(sum(vi) / len(vi)) if vi else None)
            g.update(n_obs=len(obs), n_imp=len(imp),
                     vals_obs=vals_obs, vals_imp=vals_imp)
        # mini-tree: prune the species tree to one representative leaf/clade
        import copy
        tree = copy.deepcopy(treeB_nodes)
        keep = {g["tip"] for g in groups}
        tree = prune_to(tree, keep)
        tip_clade = {g["tip"]: g["name"] for g in groups}
        lv = []
        leaf_order(tree, lv)
        for lf in lv:
            lf.name = tip_clade.get(lf.name, lf.name)
        ladderize(tree)
        assign_layout.leaf_count = 0
        assign_layout(tree)
        leaves = []
        leaf_order(tree, leaves)
        h_edges, v_edges = [], []
        tree_edges(tree, h_edges, v_edges)
        by_name = {g["name"]: g for g in groups}
        ordered = [by_name[lf.name] for lf in leaves if lf.name in by_name]
        for g in groups:  # strip bulky per-species detail before emission
            g.pop("rows", None)
            g.pop("tip", None)
        means = []
        for ci in range(len(cols)):
            vs = [r["vals"][ci] for r in rowsB if r["vals"][ci] is not None]
            means.append(round(sum(vs) / len(vs), 1) if vs else None)
        return dict(rows=ordered, tree=dict(h=h_edges, v=v_edges,
                                            max_depth=max((e[2] for e in h_edges), default=1)),
                    col_means=means)

    def col_means(rows):
        out = []
        for ci in range(len(cols)):
            vs = [r["vals"][ci] for r in rows if r["vals"][ci] is not None]
            out.append(round(sum(vs) / len(vs), 1) if vs else None)
        return out

    meta = dict(
        panel_version=panel_version, call_date=call_date,
        tree="BirdTree Ericson (birdtree.org) tree #1, pruned to displayed species; "
             "taxonomy-mismatched species grafted to genus/family LCA",
        genes=len(genes_with_calls),
        imputation="per gene, nearest phylogenetic neighbor with an observed call",
    )

    clade_order = build_clade("order", lambda r: r["order"])
    for g in clade_order["rows"]:
        g["label"] = f"{g['name']} — {ORDER_COMMON.get(g['name'], '')}".strip(' —')
    clade_family = build_clade("family", lambda r: r["family"])
    for g in clade_family["rows"]:
        g["label"] = g["name"]

    clade_payload = dict(
        meta=meta, cols=cols,
        order=clade_order, family=clade_family,
        subtitle=(f"gene panel presence by clade · cell = mean panel presence "
                  f"(top ▙ observed / bottom ◟ imputed) · panel {panel_version} "
                  f"({call_date}) · {len(genes_with_calls)} genes"),
    )
    html = CLADE_TEMPLATE.replace("__PAYLOAD__",
                                  json.dumps(clade_payload, separators=(",", ":")))
    (OUT_DIR / "gene_panel_heatmap_clades.html").write_text(html)
    (OUT_DIR / "panel_data.json").write_text(
        json.dumps(clade_payload, separators=(",", ":")))  # for make_panel_figure.py
    print(f"wrote figures/gene_panel_heatmap_clades.html  "
          f"({len(clade_order['rows'])} orders / {len(clade_family['rows'])} families, "
          f"{len(html)//1024} KB)")

    for fname, rows, tree, subtitle in [
        ("gene_panel_heatmap_observed.html", rowsA, treeA,
         f"{len(rowsA)} genome-searched bird species · direct search calls only"),
        ("gene_panel_heatmap_imputed.html", rowsB, treeB,
         f"{len(rowsB)} species · detected-but-unsequenced birds imputed (diamond + hatch) "
         f"from nearest phylogenetic neighbor"),
    ]:
        payload = dict(meta=meta, subtitle=subtitle, cols=cols, rows=rows,
                       col_means=col_means(rows), tree=tree)
        html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
        (OUT_DIR / fname).write_text(html)
        print(f"wrote figures/{fname}  ({len(rows)} rows × {len(cols)} cols, {len(html)//1024} KB)")

    n_imp = sum(1 for r in rowsB if not r["searched"])
    n_part = sum(1 for r in rowsB if r["searched"] and any(r["cell_imp"]))
    print(f"imputed version: {n_imp} fully-imputed species rows; "
          f"{n_part} searched species with partially imputed cells")


# --------------------------------------------------------------------------- #
# HTML template (vanilla JS + SVG, fully self-contained)
# --------------------------------------------------------------------------- #
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roost · gene panel × phylogeny</title>
<style>
  :root { --ink:#1c2733; --mut:#5b6b7b; --line:#d8e0e8; }
  * { box-sizing:border-box; }
  body { font:14px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         color:var(--ink); margin:0; background:#f6f8fa; }
  header { padding:18px 22px 10px; }
  h1 { font-size:19px; margin:0 0 4px; }
  .sub { color:var(--mut); font-size:12.5px; }
  .legend { display:flex; gap:16px; align-items:center; flex-wrap:wrap;
            padding:6px 22px 12px; font-size:12px; color:var(--mut); }
  .legend .sw { display:inline-block; width:13px; height:13px;
                vertical-align:-2px; margin-right:5px; }
  .figwrap { margin:0 22px 30px; background:#fff; border:1px solid var(--line);
             border-radius:10px; overflow:hidden; }
  .zoombar { background:#fff; border-bottom:1px solid var(--line);
             padding:6px 10px; display:flex; gap:8px; align-items:center; font-size:12px; }
  .zoombar button { font:inherit; padding:2px 10px; border:1px solid var(--line);
                    background:#fff; border-radius:6px; cursor:pointer; }
  .zoombar button:hover { background:#eef3f7; }
  .scroller { overflow:auto; max-height:80vh; }
  .tip { position:fixed; z-index:50; background:#101820; color:#eef4fa; padding:8px 11px;
         border-radius:8px; font-size:12px; line-height:1.5; pointer-events:none;
         max-width:340px; box-shadow:0 6px 24px rgba(0,0,0,.35); display:none; }
  .tip i { color:#9fb3c8; }
  footer { color:var(--mut); font-size:11.5px; padding:0 22px 30px; }
  text { user-select:none; }
</style>
</head>
<body>
<header>
  <h1>Gene panel presence across birds — phylogeny heatmap</h1>
  <div class="sub" id="subtitle"></div>
</header>
<div class="legend" id="legend"></div>
<div class="figwrap">
  <div class="zoombar">
    <button id="zout">−</button><button id="zin">+</button>
    <button id="zfit">fit width</button><button id="z1">100%</button>
    <span id="zval"></span>
  </div>
  <div class="scroller" id="scroller"></div>
</div>
<div class="tip" id="tip"></div>
<footer id="foot"></footer>
<script>
const DATA = __PAYLOAD__;
const N = DATA.rows.length;
const ROW_H   = N > 260 ? 9.5 : 12;
const GENE_W  = N > 260 ? 7 : 12;
const AGG_W   = GENE_W * 2.6;
const TREE_W  = N > 260 ? 280 : 340;
const LABEL_W = N > 260 ? 150 : 215;
const HEAD_H  = 128, TOP_STRIP_H = 18, PAD_L = 12, PAD_T = 6;

const STOPS = [[68,1,84],[59,82,139],[33,144,140],[94,201,98],[253,231,37]];
function lerp(a,b,t){return a+(b-a)*t;}
function ramp(t){
  t = Math.max(0, Math.min(1, t));
  const x = t*(STOPS.length-1), i = Math.min(STOPS.length-2, Math.floor(x)), f = x-i;
  const c = STOPS[i].map((v,k)=>Math.round(lerp(v, STOPS[i+1][k], f)));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
function valColor(v){ return v==null ? '#e7ecf1' : ramp(v/100); }
function colW(c){ return c.kind==='gene' ? GENE_W : (c.kind==='agg' ? AGG_W : AGG_W+10); }

let x = PAD_L + TREE_W + LABEL_W;
const colX = DATA.cols.map(c => { const cx = x; x += colW(c) + 1; return cx; });
const HEAT_W = x - (PAD_L + TREE_W + LABEL_W);
const TOTAL_W = x + 6;

const groups = [];
DATA.cols.forEach((c,i)=>{
  if(!groups.length || groups[groups.length-1].name !== c.group)
    groups.push({name:c.group, from:i});
});
groups.forEach((g,gi)=>{ g.to = (gi<groups.length-1 ? groups[gi+1].from : DATA.cols.length)-1; });

const ns = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent){
  const e = document.createElementNS(ns, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]);
  if(parent) parent.appendChild(e);
  return e;
}

// ---------- header: group bar + column labels + prevalence strip ----------
function buildHeader(){
  const svg = el('svg',{width:TOTAL_W, height:HEAD_H});
  const GCOL = {'Critical':'#b30000','Summary':'#6a00a8'};
  groups.forEach(g=>{
    const last = DATA.cols[g.to];
    const gx = colX[g.from]-1;
    const gw = colX[g.to]+colW(last)+1-gx;
    const gc = GCOL[g.name] || (g.name.startsWith('Tier-1') ? '#045a8d'
             : g.name.startsWith('Tier-2') ? '#2b8cbe' : '#74a9cf');
    el('rect',{x:gx, y:6, width:gw, height:5, fill:gc, rx:2}, svg);
    const t = el('text',{x:gx+gw/2, y:22,'text-anchor':'middle','font-size':10,
      'font-weight':700, fill:gc}, svg);
    t.textContent = g.name.length>26 ? g.name.slice(0,25)+'…' : g.name;
  });
  DATA.cols.forEach((c,i)=>{
    const cx = colX[i]+colW(c)/2, base = HEAD_H-TOP_STRIP_H;
    if(c.kind==='gene'){
      const t = el('text',{x:cx+3, y:base-4, transform:`rotate(-76 ${cx+3} ${base-4})`,
        'text-anchor':'start','font-size':10,
        'font-weight':c.group==='Critical'?700:500,
        fill:c.group==='Critical'?'#b30000':'#33475a'}, svg);
      t.textContent = c.label;
    } else {
      const t = el('text',{x:cx, y:base-10,'text-anchor':'middle','font-size':9.5,
        'font-weight':700, fill:'#33475a'}, svg);
      t.textContent = c.label;
    }
  });
  const strip = DATA.col_means;
  DATA.cols.forEach((c,i)=>{
    el('rect',{x:colX[i], y:HEAD_H-TOP_STRIP_H, width:colW(c), height:TOP_STRIP_H,
      fill:valColor(strip[i]), stroke:'#fff','stroke-width':.5,
      'data-col':i, class:'hovcol'}, svg);
  });
  el('text',{x:PAD_L+TREE_W+LABEL_W-4, y:HEAD_H-TOP_STRIP_H+13,
    'text-anchor':'end','font-size':9, fill:'#8296a8'}, svg).textContent='prevalence ▸';
  return svg;
}

// ---------- body: tree + labels + heatmap ----------------------------------
function buildBody(){
  const H = PAD_T + N*ROW_H + 12;
  const svg = el('svg',{width:TOTAL_W, height:H});
  const tr = DATA.tree, xd = (TREE_W-30)/(tr.max_depth||1);
  const yOf = r => PAD_T + r*ROW_H + ROW_H/2;

  tr.h.forEach(([dp, cy, dc])=>{
    const y = yOf(cy);
    el('path',{d:`M${PAD_L+dp*xd},${y}L${PAD_L+dc*xd},${y}`,
      stroke:'#9db1c3','stroke-width':.8, fill:'none'}, svg);
  });
  tr.v.forEach(([dp, ymin, ymax])=>{
    el('path',{d:`M${PAD_L+(dp+1)*xd},${yOf(ymin)}L${PAD_L+(dp+1)*xd},${yOf(ymax)}`,
      stroke:'#9db1c3','stroke-width':.8}, svg);
  });

  const defs = el('defs',{},svg);
  const pat = el('pattern',{id:'hatch', width:7, height:7,
    patternUnits:'userSpaceOnUse', patternTransform:'rotate(45)'}, defs);
  el('line',{x1:0,y1:0,x2:0,y2:7,stroke:'#111','stroke-width':1.1,opacity:.18},pat);

  DATA.rows.forEach((row,li)=>{
    const y = PAD_T + li*ROW_H;
    if(li%2===1) el('rect',{x:0,y:y,width:PAD_L+TREE_W+LABEL_W,height:ROW_H,
      fill:'rgba(0,0,20,0.025)','pointer-events':'none'}, svg);
    // leaf tick to the label zone
    el('path',{d:`M${PAD_L+tr.max_depth*xd},${yOf(li)}L${PAD_L+TREE_W-14},${yOf(li)}`,
      stroke:row.searched?'#8fa5b8':'#c4a8e0','stroke-width':.7}, svg);
    // label: left-aligned right of the tree (anchor start — end-anchor would
    // draw text backward over the phylogeny)
    const t = el('text',{x:PAD_L+TREE_W+2, y:y+ROW_H-2,'text-anchor':'start',
      'font-size':Math.max(8, ROW_H-3.4), fill:row.searched?'#22303d':'#7a5a9e'}, svg);
    const maxc = Math.floor(LABEL_W/(ROW_H>10?6.2:5.4));
    t.textContent = row.common.length>maxc ? row.common.slice(0,maxc-1)+'…' : row.common;
    if(!row.searched){
      const dx = PAD_L+TREE_W-8, dy = y+ROW_H/2;
      el('path',{d:`M${dx},${dy-3.2}L${dx+3.2},${dy}L${dx},${dy+3.2}L${dx-3.2},${dy}Z`,
        fill:'#6a00a8'}, svg);
    }
    DATA.cols.forEach((c,ci)=>{
      el('rect',{x:colX[ci], y:y+.4, width:colW(c), height:ROW_H-.8,
        fill:valColor(row.vals[ci]), stroke:'#fff','stroke-width':.4,
        'data-row':li,'data-col':ci, class:'cell'}, svg);
      if(row.searched && row.cell_imp[ci]){
        const cx = colX[ci]+colW(c)/2, cy = y+ROW_H/2, r = Math.min(3.4, ROW_H/2-1.2);
        el('path',{d:`M${cx},${cy-r}L${cx+r},${cy}L${cx},${cy+r}L${cx-r},${cy}Z`,
          fill:'none', stroke:'#111','stroke-width':.9, opacity:.8,
          'pointer-events':'none'}, svg);
      }
    });
    if(!row.searched){
      el('rect',{x:PAD_L+TREE_W+LABEL_W, y:y+.4, width:HEAT_W, height:ROW_H-.8,
        fill:'url(#hatch)','pointer-events':'none'}, svg);
    }
  });
  return svg;
}

const scroller = document.getElementById('scroller');
const header = buildHeader(), body = buildBody();
scroller.appendChild(header);
scroller.appendChild(body);

// ---------- tooltip ----------------------------------------------------------
const tip = document.getElementById('tip');
function showTip(html, ev){
  tip.innerHTML = html; tip.style.display='block';
  tip.style.left = Math.min(window.innerWidth-tip.offsetWidth-12, ev.clientX+14)+'px';
  tip.style.top  = Math.min(window.innerHeight-tip.offsetHeight-12, ev.clientY+14)+'px';
}
document.addEventListener('mousemove', e=>{
  const t = e.target;
  if(t.classList && t.classList.contains('cell')){
    const li=+t.dataset.row, ci=+t.dataset.col, r=DATA.rows[li], c=DATA.cols[ci];
    const v = r.vals[ci];
    const vv = v==null ? 'no data' : v.toFixed(0)+'%';
    const imp = (!r.searched || r.cell_imp[ci])
      ? ' <span style="color:#c9a0ff">◆ imputed</span>' : '';
    showTip(`<b>${r.common}</b> <i>(${r.sci})</i><br>${r.order} · ${r.family}<br>` +
      (c.kind==='gene' ? `gene <b>${c.id}</b> (${c.group})` : `group <b>${c.group}</b>`) +
      `<br>panel presence: <b>${vv}</b>${imp}<br><i>${r.searched
        ? r.n_obs+' direct gene calls' : 'no genome searched'} · detections: ${r.detections}</i>`, e);
  } else if(t.classList && t.classList.contains('hovcol')){
    const ci=+t.dataset.col, c=DATA.cols[ci];
    showTip(`<b>${c.kind==='gene'?c.id:c.group}</b><br>mean across displayed species: ` +
      `<b>${DATA.col_means[ci]}%</b>`, e);
  } else tip.style.display='none';
});

// ---------- zoom -------------------------------------------------------------
let z = 1;
function applyZ(){
  [header, body].forEach(s=>{
    s.style.transformOrigin='0 0';
    s.style.transform=`scale(${z})`;
    s.style.width  = TOTAL_W*z+'px';
    s.style.height = (s===header ? HEAD_H : PAD_T+N*ROW_H+12)*z+'px';
  });
  document.getElementById('zval').textContent = Math.round(z*100)+'%';
}
function fit(){ z = Math.min(1.5, Math.max(.3, (window.innerWidth-70)/TOTAL_W)); applyZ(); }
document.getElementById('zin').onclick  = ()=>{ z=Math.min(2,z*1.15); applyZ(); };
document.getElementById('zout').onclick = ()=>{ z=Math.max(.2,z/1.15); applyZ(); };
document.getElementById('zfit').onclick = fit;
document.getElementById('z1').onclick   = ()=>{ z=1; applyZ(); };
fit();

// ---------- header/legend/footer ---------------------------------------------
document.getElementById('subtitle').textContent =
  `${DATA.subtitle} · panel ${DATA.meta.panel_version} (${DATA.meta.call_date}) · ${DATA.meta.genes} genes`;
const legend = document.getElementById('legend');
[['0%',0],['25%',.25],['50%',.5],['75%',.75],['100%',1]].forEach(([lab,t])=>{
  const s=document.createElement('span');
  s.innerHTML=`<span class="sw" style="background:${ramp(t)};border-radius:3px"></span>${lab}`;
  legend.appendChild(s);
});
const dm=document.createElement('span');
dm.innerHTML='<span class="sw" style="background:#6a00a8;clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)"></span>imputed species (no genome; whole row imputed)';
legend.appendChild(dm);
const dp=document.createElement('span');
dp.innerHTML='<span class="sw" style="background:#fff;box-shadow:inset 0 0 0 1.5px #111;clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)"></span>cell partly imputed';
legend.appendChild(dp);
const dh=document.createElement('span');
dh.innerHTML='<span class="sw" style="background:repeating-linear-gradient(45deg,#fff 0 2px,rgba(0,0,0,.25) 2px 4px)"></span>hatched = imputed row';
legend.appendChild(dh);
document.getElementById('foot').innerHTML =
  `Tree: ${DATA.meta.tree}. Imputation: ${DATA.meta.imputation}. Cell value = share of genes FULL ` +
  `(FRAGMENT counts ½). ${DATA.cols.filter(c=>c.kind==='gene').length} genes shown individually; ` +
  `tier-2 categories and the tier-3 immune block shown as aggregate columns. ` +
  `Built from data/genes/gene_presence_v2.parquet — static figure, not part of the web app.`;
</script>
</body>
</html>
"""

# --------------------------------------------------------------------------- #
# Clade-collapsed template (order/family toggle, split observed/imputed cells)
# --------------------------------------------------------------------------- #
CLADE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roost · gene panel by clade</title>
<style>
  :root { --ink:#1c2733; --mut:#5b6b7b; --line:#d8e0e8; --obs:#2b6cb0; --imp:#6a00a8; }
  * { box-sizing:border-box; }
  body { font:14px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         color:var(--ink); margin:0; background:#f6f8fa; }
  header { padding:18px 22px 8px; }
  h1 { font-size:19px; margin:0 0 4px; }
  .sub { color:var(--mut); font-size:12.5px; }
  .bar { display:flex; gap:10px; align-items:center; padding:10px 22px 12px; flex-wrap:wrap; }
  .lvl { font:inherit; padding:4px 14px; border:1px solid var(--line); background:#fff;
         border-radius:18px; cursor:pointer; font-size:13px; }
  .lvl.on { background:var(--ink); color:#fff; border-color:var(--ink); }
  .legend { display:flex; gap:14px; align-items:center; flex-wrap:wrap; font-size:12px;
            color:var(--mut); margin-left:auto; }
  .legend .sw { display:inline-block; width:13px; height:13px; vertical-align:-2px; margin-right:5px; }
  .figwrap { margin:0 22px 30px; background:#fff; border:1px solid var(--line);
             border-radius:10px; overflow-x:auto; }
  .tip { position:fixed; z-index:50; background:#101820; color:#eef4fa; padding:8px 11px;
         border-radius:8px; font-size:12px; line-height:1.5; pointer-events:none;
         max-width:360px; box-shadow:0 6px 24px rgba(0,0,0,.35); display:none; }
  .tip i { color:#9fb3c8; }
  footer { color:var(--mut); font-size:11.5px; padding:0 22px 30px; }
  text { user-select:none; }
</style>
</head>
<body>
<header>
  <h1>Gene panel presence across bird clades</h1>
  <div class="sub" id="subtitle"></div>
</header>
<div class="bar">
  <button class="lvl on" id="bOrder">Order</button>
  <button class="lvl" id="bFamily">Family</button>
  <div class="legend">
    <span><span class="sw" id="lg0"></span>0%</span>
    <span><span class="sw" id="lg5"></span>50%</span>
    <span><span class="sw" id="lg10"></span>100%</span>
    <span><span class="sw" style="background:linear-gradient(135deg,#2b6cb0 0 49%,#fff 50%,#6a00a8 52%)"></span>top ▙ observed · bottom ◟ imputed</span>
    <span><span class="sw" style="background:linear-gradient(90deg,#2b6cb0 60%,#6a00a8 60%)"></span>species: genome / imputed</span>
  </div>
</div>
<div class="figwrap" id="figwrap"></div>
<div class="tip" id="tip"></div>
<footer id="foot"></footer>
<script>
const DATA = __PAYLOAD__;
const COLS = DATA.cols;
const STOPS = [[68,1,84],[59,82,139],[33,144,140],[94,201,98],[253,231,37]];
function lerp(a,b,t){return a+(b-a)*t;}
function ramp(t){
  t = Math.max(0, Math.min(1, t));
  const x = t*(STOPS.length-1), i = Math.min(STOPS.length-2, Math.floor(x)), f = x-i;
  const c = STOPS[i].map((v,k)=>Math.round(lerp(v, STOPS[i+1][k], f)));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
function vc(v){ return v==null ? '#e7ecf1' : ramp(v/100); }

let LEVEL = 'order';
const ns = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent){
  const e = document.createElementNS(ns, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]);
  if(parent) parent.appendChild(e);
  return e;
}

const groups = [];
COLS.forEach((c,i)=>{
  if(!groups.length || groups[groups.length-1].name !== c.group) groups.push({name:c.group, from:i});
});
groups.forEach((g,gi)=>{ g.to = (gi<groups.length-1 ? groups[gi+1].from : COLS.length)-1; });

function render(){
  const D = DATA[LEVEL];
  const rows = D.rows, N = rows.length;
  const big = N <= 40;
  const GENE_W = big ? 17 : 14, AGG_W = big ? 38 : 31;
  const ROW_H   = big ? 26 : 16;
  const TREE_W  = big ? 330 : 300, LABEL_W = big ? 320 : 230, COV_W = 130;
  const HEAD_H  = 150, PAD_L = 12, PAD_T = 6;
  const colW = c => c.kind==='gene' ? GENE_W : (c.kind==='agg' ? AGG_W : AGG_W+14);

  let x = PAD_L + TREE_W + LABEL_W + COV_W;
  const colX = COLS.map(c => { const cx = x; x += colW(c) + 1; return cx; });
  const TOTAL_W = x + 6;
  const maxN = Math.max(...rows.map(r => r.n_obs + r.n_imp), 1);

  const wrap = document.getElementById('figwrap');
  wrap.innerHTML = '';
  const svg = el('svg', {width:TOTAL_W, height:PAD_T + N*ROW_H + HEAD_H + 16}, wrap);

  // ---- tree ----
  const tr = D.tree, xd = (TREE_W-24)/(tr.max_depth||1);
  const yOf = r => PAD_T + HEAD_H + r*ROW_H + ROW_H/2;
  tr.h.forEach(([dp, cy, dc])=>{
    const y = yOf(cy);
    el('path',{d:`M${PAD_L+dp*xd},${y}L${PAD_L+dc*xd},${y}`, stroke:'#9db1c3','stroke-width':1.1, fill:'none'}, svg);
  });
  tr.v.forEach(([dp, ymin, ymax])=>{
    el('path',{d:`M${PAD_L+(dp+1)*xd},${yOf(ymin)}L${PAD_L+(dp+1)*xd},${yOf(ymax)}`, stroke:'#9db1c3','stroke-width':1.1}, svg);
  });

  // ---- group header bars + column labels + prevalence strip ----
  const GCOL = {'Critical':'#b30000','Summary':'#6a00a8'};
  groups.forEach(g=>{
    const last = COLS[g.to];
    const gx = colX[g.from]-1;
    const gw = colX[g.to]+colW(last)+1-gx;
    const gc = GCOL[g.name] || (g.name.startsWith('Tier-1') ? '#045a8d'
             : g.name.startsWith('Tier-2') ? '#2b8cbe' : '#74a9cf');
    el('rect',{x:gx, y:8, width:gw, height:6, fill:gc, rx:2}, svg);
    const t = el('text',{x:gx+gw/2, y:26,'text-anchor':'middle','font-size':11,
      'font-weight':700, fill:gc}, svg);
    t.textContent = g.name.length>24 ? g.name.slice(0,23)+'…' : g.name;
  });
  const base = HEAD_H-22;
  COLS.forEach((c,i)=>{
    const cx = colX[i]+colW(c)/2;
    if(c.kind==='gene'){
      const t = el('text',{x:cx+4, y:base, transform:`rotate(-58 ${cx+4} ${base})`,
        'text-anchor':'start','font-size':10.5,'font-weight':c.group==='Critical'?700:500,
        fill:c.group==='Critical'?'#b30000':'#33475a'}, svg);
      t.textContent = c.label;
    } else {
      const t = el('text',{x:cx, y:base-8,'text-anchor':'middle','font-size':10,
        'font-weight':700, fill:'#33475a'}, svg);
      t.textContent = c.label.length>18 ? c.label.replace(/ \(\d+\)$/,'') : c.label;
    }
    el('rect',{x:colX[i], y:HEAD_H-20, width:colW(c), height:18,
      fill:vc(D.col_means[i]), stroke:'#fff','stroke-width':.5, 'data-col':i, class:'hovcol'}, svg);
  });

  // ---- rows ----
  rows.forEach((row,li)=>{
    const y = PAD_T + HEAD_H + li*ROW_H;
    if(li%2===1) el('rect',{x:0,y,width:PAD_L+TREE_W+LABEL_W+COV_W,height:ROW_H,
      fill:'rgba(0,0,20,0.025)','pointer-events':'none'}, svg);
    el('path',{d:`M${PAD_L+tr.max_depth*xd},${yOf(li)}L${PAD_L+TREE_W-2},${yOf(li)}`,
      stroke:'#8fa5b8','stroke-width':.8}, svg);
    // coverage bars, cumulative sqrt scale: obs segment then imp segment,
    // summing to sqrt(total/maxTotal)*COV_W — never overflows the track
    const sObs = Math.sqrt(row.n_obs/maxN), sTot = Math.sqrt((row.n_obs+row.n_imp)/maxN);
    const wObs = sObs*COV_W, wImp = (sTot-sObs)*COV_W;
    const by = y+ROW_H/2-5, bh = 10;
    el('rect',{x:PAD_L+TREE_W+LABEL_W, y:by, width:COV_W, height:bh, fill:'#eef2f6', rx:2}, svg);
    if(wObs>0) el('rect',{x:PAD_L+TREE_W+LABEL_W, y:by, width:wObs, height:bh,
      fill:'#2b6cb0', rx:2, 'data-row':li, class:'cov'}, svg);
    if(wImp>0) el('rect',{x:PAD_L+TREE_W+LABEL_W+wObs, y:by, width:wImp, height:bh,
      fill:'#6a00a8', rx:2, 'data-row':li, class:'cov'}, svg);
    // label: left-aligned right of the tree (anchor start — end-anchor would
    // draw text backward over the phylogeny)
    const t = el('text',{x:PAD_L+TREE_W+2, y:y+ROW_H/2+4,'text-anchor':'start',
      'font-size':big?12:10.5, 'font-weight':big?600:400, fill:'#22303d'}, svg);
    const maxc = Math.floor(LABEL_W/(big?7.4:6.2));
    t.textContent = row.label.length>maxc ? row.label.slice(0,maxc-1)+'…' : row.label;
    // cells
    COLS.forEach((c,ci)=>{
      const w = colW(c), cx = colX[ci], cy = y+1, ch = ROW_H-2;
      el('rect',{x:cx, y:cy, width:w, height:ch, fill:vc(row.vals_obs[ci]),
        stroke:'#fff','stroke-width':.5, 'data-row':li,'data-col':ci,'data-half':'obs', class:'cell'}, svg);
      if(row.n_imp>0 && row.vals_imp[ci]!=null){
        el('polygon',{points:`${cx+w},${cy} ${cx+w},${cy+ch} ${cx},${cy+ch}`,
          fill:vc(row.vals_imp[ci]), stroke:'#ffffff88','stroke-width':.5,
          'data-row':li,'data-col':ci,'data-half':'imp', class:'cell'}, svg);
      }
    });
  });
  window.__colX = colX; window.__rows = rows;
}

function rerender(){ render(); }
document.getElementById('bOrder').onclick = e=>{ LEVEL='order';
  document.getElementById('bOrder').classList.add('on');
  document.getElementById('bFamily').classList.remove('on'); rerender(); };
document.getElementById('bFamily').onclick = e=>{ LEVEL='family';
  document.getElementById('bFamily').classList.add('on');
  document.getElementById('bOrder').classList.remove('on'); rerender(); };

render();
document.getElementById('subtitle').textContent =
  `${DATA.subtitle} · order view: ${DATA.order.rows.length} clades · family view: ${DATA.family.rows.length} clades`;
['lg0','lg5','lg10'].forEach((id,i)=>{
  document.getElementById(id).style.background = ramp(i*0.5);
  document.getElementById(id).style.borderRadius = '3px';
});
document.getElementById('foot').innerHTML =
  `Cell = mean % of genes FULL (FRAGMENT ½). Top-left triangle = species with searched genomes; ` +
  `bottom-right = detected-but-unsequenced species, imputed from nearest phylogenetic neighbor. ` +
  `Coverage bars (log-ish scale) = species per clade. Tree: ${DATA.meta.tree}. ` +
  `${COLS.filter(c=>c.kind==='gene').length} genes individually; tier-2/3 as aggregates. ` +
  `Static figure from data/genes/gene_presence_v2.parquet — not part of the app.`;

const tip = document.getElementById('tip');
function showTip(html, ev){
  tip.innerHTML = html; tip.style.display='block';
  tip.style.left = Math.min(window.innerWidth-tip.offsetWidth-12, ev.clientX+14)+'px';
  tip.style.top  = Math.min(window.innerHeight-tip.offsetHeight-12, ev.clientY+14)+'px';
}
document.addEventListener('mousemove', e=>{
  const t = e.target;
  if(t.classList && t.classList.contains('cell')){
    const r = window.__rows[+t.dataset.row], c = COLS[+t.dataset.col];
    const imp = t.dataset.half==='imp';
    const v = imp ? r.vals_imp[+t.dataset.col] : r.vals_obs[+t.dataset.col];
    const n = imp ? r.n_imp : r.n_obs;
    showTip(`<b>${r.label}</b><br>${c.kind==='gene' ? `gene <b>${c.id}</b> (${c.group})` : `group <b>${c.group}</b>`}` +
      `<br>${imp?'imputed species':'observed species'} (n=${n}): <b>${v==null?'—':v+'%'}</b>` +
      `<br><i>clade totals — genome: ${r.n_obs}, imputed: ${r.n_imp}</i>`, e);
  } else if(t.classList && t.classList.contains('cov')){
    const r = window.__rows[+t.dataset.row];
    showTip(`<b>${r.label}</b><br>genome-searched species: <b>${r.n_obs}</b><br>` +
      `imputed (detected only): <b>${r.n_imp}</b>`, e);
  } else if(t.classList && t.classList.contains('hovcol')){
    const c = COLS[+t.dataset.col];
    showTip(`<b>${c.kind==='gene'?c.id:c.group}</b><br>mean across all species: ` +
      `<b>${DATA[LEVEL].col_means[+t.dataset.col]}%</b>`, e);
  } else tip.style.display='none';
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()

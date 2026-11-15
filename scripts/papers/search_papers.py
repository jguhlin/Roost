#!/usr/bin/env python3
"""
Search for new H5N1/avian influenza papers from various sources.
Run periodically to find new publications.

Usage:
    python scripts/papers/search_papers.py [--source pubmed|biorxiv|all] [--days 30]
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
NEW_PAPERS_JSON = PROJECT_ROOT / "scripts" / "papers" / "new_papers.json"
SEARCH_LOG = PROJECT_ROOT / "scripts" / "papers" / "search_log.json"

# Search terms for different aspects of H5N1 research
SEARCH_QUERIES = {
    "core": [
        "H5N1 avian influenza wild birds",
        "H5N1 clade 2.3.4.4b",
        "HPAI H5N1 host",
    ],
    "host_genomics": [
        "avian influenza ANP32 host factor",
        "avian influenza Mx gene resistance",
        "avian influenza IFITM antiviral",
        "avian influenza RIG-I MDA5 innate immunity",
        "avian influenza host genetics susceptibility",
    ],
    "species": [
        "H5N1 waterfowl duck goose",
        "H5N1 raptor eagle hawk",
        "H5N1 seabird gannet tern",
        "H5N1 corvid crow",
        "H5N1 cattle dairy bovine",
        "H5N1 seal marine mammal",
    ],
    "evolution": [
        "H5N1 reassortment genotype",
        "H5N1 PB2 mammalian adaptation",
        "avian influenza receptor binding sialic acid",
    ],
}


def search_pubmed(query: str, days: int = 30, max_results: int = 50) -> list:
    """
    Search PubMed for recent papers.
    Uses NCBI E-utilities API.
    """
    papers = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    mindate = start_date.strftime("%Y/%m/%d")
    maxdate = end_date.strftime("%Y/%m/%d")

    # Search query
    search_url = (
        f"{base_url}/esearch.fcgi?"
        f"db=pubmed&term={quote_plus(query)}"
        f"&datetype=pdat&mindate={mindate}&maxdate={maxdate}"
        f"&retmax={max_results}&retmode=json"
    )

    try:
        req = Request(search_url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())

        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return papers

        # Fetch details for each ID
        ids = ",".join(id_list)
        fetch_url = (
            f"{base_url}/esummary.fcgi?"
            f"db=pubmed&id={ids}&retmode=json"
        )

        req = Request(fetch_url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            details = json.loads(response.read())

        results = details.get("result", {})
        for pmid in id_list:
            if pmid not in results:
                continue
            article = results[pmid]

            # Extract DOI from articleids
            doi = None
            for aid in article.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                    break

            papers.append({
                "source": "pubmed",
                "pmid": pmid,
                "title": article.get("title", ""),
                "authors": article.get("sortfirstauthor", "") + " et al." if article.get("sortfirstauthor") else "",
                "journal": article.get("fulljournalname", article.get("source", "")),
                "year": int(article.get("pubdate", "2024")[:4]) if article.get("pubdate") else 2024,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "query": query,
            })

        time.sleep(0.5)  # Rate limiting

    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"  Error searching PubMed: {e}", file=sys.stderr)

    return papers


def search_biorxiv(query: str, days: int = 30, server: str = "biorxiv") -> list:
    """
    Search bioRxiv/medRxiv for recent preprints.
    Uses the bioRxiv API.
    """
    papers = []

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # bioRxiv API endpoint
    # Note: bioRxiv API doesn't support keyword search directly,
    # so we search recent papers and filter by keywords
    base_url = f"https://api.biorxiv.org/details/{server}"
    date_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    url = f"{base_url}/{date_str}/{end_str}/0/100"

    try:
        req = Request(url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())

        # Filter by query terms
        query_terms = query.lower().split()

        for article in data.get("collection", []):
            title = article.get("title", "").lower()
            abstract = article.get("abstract", "").lower()

            # Check if any query terms match
            if any(term in title or term in abstract for term in query_terms):
                papers.append({
                    "source": server,
                    "doi": article.get("doi"),
                    "title": article.get("title", ""),
                    "authors": article.get("authors", "").split(";")[0] + " et al." if article.get("authors") else "",
                    "journal": f"{server} (preprint)",
                    "year": int(article.get("date", "2024")[:4]),
                    "url": f"https://www.biorxiv.org/content/{article.get('doi')}",
                    "query": query,
                })

        time.sleep(0.5)  # Rate limiting

    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"  Error searching bioRxiv: {e}", file=sys.stderr)

    return papers


def search_europepmc(query: str, days: int = 30, max_results: int = 50) -> list:
    """
    Search EuropePMC (superset of PubMed: + Agricola, regional vet journals,
    preprint servers) for recent papers. D86 source expansion.
    """
    papers = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    # FIRST_PDATE (first publication date) is the facet EuropePMC actually
    # honours for recency; PUB_DATE returns 0 hits in practice
    date_facet = (f'FIRST_PDATE:[{start_date.strftime("%Y-%m-%d")} '
                  f'TO {end_date.strftime("%Y-%m-%d")}]')
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
           f"?query={quote_plus(query + ' AND ' + date_facet)}"
           f"&format=json&pageSize={max_results}"
           "&resultType=core&sort=" + quote_plus("P_PDATE_D desc"))
    try:
        req = Request(url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
        for r in data.get("resultList", {}).get("result", []):
            pmcid = (r.get("pmcid") or "").replace("PMC", "") or None
            papers.append({
                "source": "europepmc",
                "doi": r.get("doi"),
                "pmcid": pmcid,
                "title": r.get("title", "").rstrip("."),
                "authors": (r.get("authorString") or "Unknown").split(",")[0] + " et al.",
                "journal": r.get("journalTitle") or "Unknown",
                "year": int(r.get("pubYear") or 0) or None,
                "url": (f"https://doi.org/{r['doi']}" if r.get("doi")
                        else (f"https://europepmc.org/article/PMC/{pmcid}"
                              if pmcid else "")),
                "is_open_access": r.get("isOpenAccess") == "Y",
                "query": query,
            })
        time.sleep(0.4)
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"  Error searching EuropePMC: {e}", file=sys.stderr)
    return papers


def search_openalex(query: str, days: int = 30, max_results: int = 50) -> list:
    """
    Search OpenAlex — worldwide works index including Chinese, Korean,
    Spanish and Russian veterinary journals PubMed under-covers. D86.
    """
    papers = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    url = ("https://api.openalex.org/works"
           f"?search={quote_plus(query)}"
           f"&filter=from_publication_date:{start_date.strftime('%Y-%m-%d')}"
           f"&per-page={max_results}"
           "&mailto=roost-project@example.org")
    try:
        req = Request(url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
        for w in data.get("results", []):
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            src = (((w.get("primary_location") or {}).get("source")) or {})
            papers.append({
                "source": "openalex",
                "doi": doi or None,
                "title": (w.get("display_name") or "").rstrip("."),
                "authors": ((w.get("authorships") or [{}])[0]
                            .get("author", {}).get("display_name", "Unknown")
                            + " et al."),
                "journal": src.get("display_name") or "Unknown",
                "year": w.get("publication_year"),
                "url": (f"https://doi.org/{doi}" if doi else
                        w.get("id", "")),
                "is_open_access": (w.get("open_access") or {}
                                   .get("is_oa", False)),
                "open_access_url": (w.get("open_access") or {}).get("oa_url"),
                "query": query,
            })
        time.sleep(0.4)
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"  Error searching OpenAlex: {e}", file=sys.stderr)
    return papers


def search_pmc(query: str, days: int = 30, max_results: int = 50) -> list:
    """
    Search PubMed Central for open access papers.
    """
    papers = []
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    mindate = start_date.strftime("%Y/%m/%d")
    maxdate = end_date.strftime("%Y/%m/%d")

    search_url = (
        f"{base_url}/esearch.fcgi?"
        f"db=pmc&term={quote_plus(query)}"
        f"&datetype=pdat&mindate={mindate}&maxdate={maxdate}"
        f"&retmax={max_results}&retmode=json"
    )

    try:
        req = Request(search_url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())

        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return papers

        ids = ",".join(id_list)
        fetch_url = (
            f"{base_url}/esummary.fcgi?"
            f"db=pmc&id={ids}&retmode=json"
        )

        req = Request(fetch_url, headers={"User-Agent": "Roost/1.0"})
        with urlopen(req, timeout=30) as response:
            details = json.loads(response.read())

        results = details.get("result", {})
        for pmcid in id_list:
            if pmcid not in results:
                continue
            article = results[pmcid]

            # Get DOI
            doi = None
            for aid in article.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                    break

            papers.append({
                "source": "pmc",
                "pmcid": pmcid,
                "title": article.get("title", ""),
                "authors": article.get("sortfirstauthor", "") + " et al." if article.get("sortfirstauthor") else "",
                "journal": article.get("fulljournalname", article.get("source", "")),
                "year": int(article.get("pubdate", "2024")[:4]) if article.get("pubdate") else 2024,
                "doi": doi,
                "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
                "pdf_status": "available_pmc",
                "query": query,
            })

        time.sleep(0.5)

    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"  Error searching PMC: {e}", file=sys.stderr)

    return papers


def load_existing_papers() -> dict:
    """Load existing papers and create lookup structures."""
    if not PAPERS_JSON.exists():
        return {"papers": [], "dois": set(), "titles": set(), "urls": set()}

    with open(PAPERS_JSON) as f:
        data = json.load(f)

    papers = data.get("papers", [])

    # Create lookup sets for deduplication
    dois = {p.get("doi").lower() for p in papers if p.get("doi")}
    titles = {normalize_title(p.get("title", "")) for p in papers}
    urls = {p.get("url", "").lower() for p in papers if p.get("url")}

    return {
        "papers": papers,
        "dois": dois,
        "titles": titles,
        "urls": urls,
    }


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove punctuation, lowercase, collapse whitespace
    title = re.sub(r'[^\w\s]', '', title.lower())
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def is_duplicate(paper: dict, existing: dict) -> bool:
    """Check if a paper is a duplicate of an existing one."""
    # Check DOI
    if paper.get("doi"):
        if paper["doi"].lower() in existing["dois"]:
            return True

    # Check URL
    if paper.get("url"):
        if paper["url"].lower() in existing["urls"]:
            return True

    # Check normalized title (fuzzy match)
    norm_title = normalize_title(paper.get("title", ""))
    if norm_title and norm_title in existing["titles"]:
        return True

    return False


def categorize_paper(paper: dict) -> str:
    """Automatically categorize a paper based on title/query."""
    title = paper.get("title", "").lower()
    query = paper.get("query", "").lower()

    # Check for category keywords
    if any(kw in title for kw in ["anp32", "mx gene", "ifitm", "rig-i", "mda5", "innate", "host factor", "resistance", "susceptibility", "genetic"]):
        return "Host Genomics"
    if any(kw in title for kw in ["seabird", "gannet", "tern", "skua", "kittiwake", "puffin"]):
        return "Seabirds"
    if any(kw in title for kw in ["cattle", "dairy", "bovine", "cow", "mammal", "seal", "cat ", "fox", "mink"]):
        return "Cross-Species Transmission"
    if any(kw in title for kw in ["reassort", "evolution", "genotype", "phylogen"]):
        return "Evolution"
    if any(kw in title for kw in ["surveillance", "outbreak", "detection"]):
        return "Surveillance"
    if any(kw in title for kw in ["vaccin", "control", "cull"]):
        return "Control"
    if any(kw in title for kw in ["human", "pandemic", "zoonotic"]):
        return "Pandemic Risk"

    # Default based on query
    if "host" in query or "genomic" in query:
        return "Host Genomics"
    if "species" in query or "wild bird" in query:
        return "Wild Birds"

    return "Wild Birds"  # Default


def extract_topics(paper: dict) -> list:
    """Extract topic tags from paper title/query."""
    title = paper.get("title", "").lower()
    topics = []

    # Topic keywords
    topic_map = {
        "H5N1": ["h5n1"],
        "H5N6": ["h5n6"],
        "H5N5": ["h5n5"],
        "Clade 2.3.4.4b": ["2.3.4.4b", "clade 2.3"],
        "Host Genomics": ["anp32", "mx gene", "ifitm", "rig-i", "mda5", "host factor"],
        "Wild Birds": ["wild bird", "migratory"],
        "Waterfowl": ["waterfowl", "duck", "goose", "swan"],
        "Raptors": ["raptor", "eagle", "hawk", "falcon", "owl"],
        "Seabirds": ["seabird", "gannet", "tern", "skua"],
        "Corvids": ["crow", "corvid", "raven"],
        "Cross-Species": ["cattle", "mammal", "spillover", "cross-species"],
        "Genomics": ["genom", "phylogen", "sequenc"],
        "Surveillance": ["surveillance", "outbreak", "detection"],
        "Pathology": ["patholog", "pathogen", "lesion"],
        "Transmission": ["transmission", "spread"],
    }

    for topic, keywords in topic_map.items():
        if any(kw in title for kw in keywords):
            topics.append(topic)

    return topics[:5] if topics else ["Avian Influenza"]


def run_search(sources: list, days: int, query_categories: list = None) -> list:
    """Run search across specified sources."""
    all_papers = []

    # Determine which query categories to use
    if query_categories is None:
        query_categories = list(SEARCH_QUERIES.keys())

    for category in query_categories:
        queries = SEARCH_QUERIES.get(category, [])
        print(f"\nSearching category: {category}")

        for query in queries:
            print(f"  Query: {query[:50]}...")

            if "pubmed" in sources or "all" in sources:
                papers = search_pubmed(query, days)
                print(f"    PubMed: {len(papers)} results")
                all_papers.extend(papers)

            if "pmc" in sources or "all" in sources:
                papers = search_pmc(query, days)
                print(f"    PMC: {len(papers)} results")
                all_papers.extend(papers)

            if "biorxiv" in sources or "all" in sources:
                papers = search_biorxiv(query, days)
                print(f"    bioRxiv: {len(papers)} results")
                all_papers.extend(papers)

            if "medrxiv" in sources or "all" in sources:
                papers = search_biorxiv(query, days, server="medrxiv")
                print(f"    medRxiv: {len(papers)} results")
                all_papers.extend(papers)

            if "europepmc" in sources or "all" in sources:
                papers = search_europepmc(query, days)
                print(f"    EuropePMC: {len(papers)} results")
                all_papers.extend(papers)

            if "openalex" in sources or "all" in sources:
                papers = search_openalex(query, days)
                print(f"    OpenAlex: {len(papers)} results")
                all_papers.extend(papers)

    return all_papers


def main():
    parser = argparse.ArgumentParser(description="Search for new H5N1 papers")
    parser.add_argument(
        "--source",
        choices=["pubmed", "pmc", "biorxiv", "medrxiv",
                 "europepmc", "openalex", "all"],
        default="all",
        help="Source to search"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to search back"
    )
    parser.add_argument(
        "--category",
        choices=list(SEARCH_QUERIES.keys()) + ["all"],
        default="all",
        help="Query category to search"
    )
    args = parser.parse_args()

    sources = ([args.source] if args.source != "all" else
               ["pubmed", "pmc", "biorxiv", "medrxiv",
                "europepmc", "openalex"])
    categories = list(SEARCH_QUERIES.keys()) if args.category == "all" else [args.category]

    print(f"Searching for papers from last {args.days} days...")
    print(f"Sources: {', '.join(sources)}")
    print(f"Categories: {', '.join(categories)}")

    # Load existing papers
    existing = load_existing_papers()
    print(f"\nExisting papers in database: {len(existing['papers'])}")

    # Run search
    all_papers = run_search(sources, args.days, categories)
    print(f"\nTotal results found: {len(all_papers)}")

    # Deduplicate within results
    seen = set()
    unique_papers = []
    for paper in all_papers:
        key = paper.get("doi") or normalize_title(paper.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            unique_papers.append(paper)

    print(f"After internal dedup: {len(unique_papers)}")

    # Check against existing papers
    new_papers = []
    for paper in unique_papers:
        if not is_duplicate(paper, existing):
            # Enhance with category and topics
            paper["category"] = categorize_paper(paper)
            paper["topics"] = extract_topics(paper)
            paper["summary"] = ""  # To be filled manually
            paper["cited_for"] = ""  # To be filled manually
            new_papers.append(paper)

    print(f"New papers (not in database): {len(new_papers)}")

    if new_papers:
        # Save new papers
        NEW_PAPERS_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(NEW_PAPERS_JSON, "w") as f:
            json.dump({
                "search_date": datetime.now().isoformat(),
                "days_searched": args.days,
                "sources": sources,
                "total_found": len(all_papers),
                "new_papers": new_papers,
            }, f, indent=2)

        print(f"\nNew papers saved to: {NEW_PAPERS_JSON}")
        print("\nSample new papers:")
        for paper in new_papers[:5]:
            print(f"  - {paper['title'][:60]}...")
            print(f"    {paper['journal']} ({paper['year']}) [{paper['category']}]")
    else:
        print("\nNo new papers found.")

    # Log search
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "days": args.days,
        "sources": sources,
        "categories": categories,
        "found": len(all_papers),
        "new": len(new_papers),
    }

    log_data = []
    if SEARCH_LOG.exists():
        with open(SEARCH_LOG) as f:
            log_data = json.load(f)
    log_data.append(log_entry)

    with open(SEARCH_LOG, "w") as f:
        json.dump(log_data[-100:], f, indent=2)  # Keep last 100 entries


if __name__ == "__main__":
    main()

# agents/intake/literature_agent.py

"""
Literature Agent - Fetches academic papers from arXiv and Semantic Scholar
arXiv: no API key required
Semantic Scholar: works without key (rate limited) or with free key
"""

import arxiv
import httpx
import time
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    authors: list[str]
    published_date: str
    source: str  # "arXiv" or "SemanticScholar"
    url: str
    categories: list[str]
    citation_count: int = 0


class LiteratureAgent:
    """Fetches academic papers from arXiv and Semantic Scholar"""

    def __init__(self, max_results: int = 20):
        self.max_results = max_results
        self.s2_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        self.client = httpx.Client(timeout=30.0)
        logger.info("LiteratureAgent initialized")

    def search_arxiv(self, query: str) -> list[Paper]:
        """Search arXiv — no API key needed, very reliable"""
        logger.info(f"Searching arXiv for: {query}")
        papers = []

        try:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            client = arxiv.Client()
            for result in client.results(search):
                paper = Paper(
                    paper_id=result.entry_id,
                    title=result.title,
                    abstract=result.summary,
                    authors=[a.name for a in result.authors],
                    published_date=str(result.published.date()),
                    source="arXiv",
                    url=result.entry_id,
                    categories=result.categories,
                )
                papers.append(paper)

            logger.success(f"arXiv: {len(papers)} papers found")

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")

        return papers

    def search_semantic_scholar(self, query: str) -> list[Paper]:
        """Search Semantic Scholar — free tier or with API key"""
        logger.info(f"Searching Semantic Scholar for: {query}")
        papers = []

        headers = {}
        if self.s2_api_key:
            headers["x-api-key"] = self.s2_api_key

        try:
            time.sleep(2)  # rate limit protection
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": self.max_results,
                "fields": "title,abstract,authors,year,citationCount,externalIds,url",
            }
            response = self.client.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                for p in data.get("data", []):
                    paper = Paper(
                        paper_id=p.get("paperId", "N/A"),
                        title=p.get("title", "N/A"),
                        abstract=p.get("abstract") or "N/A",
                        authors=[a.get("name", "") for a in p.get("authors", [])],
                        published_date=str(p.get("year", "N/A")),
                        source="SemanticScholar",
                        url=p.get("url") or "N/A",
                        categories=[],
                        citation_count=p.get("citationCount", 0),
                    )
                    papers.append(paper)

                logger.success(f"SemanticScholar: {len(papers)} papers found")

            elif response.status_code == 429:
                logger.warning("SemanticScholar rate limit hit, skipping")
            else:
                logger.warning(f"SemanticScholar returned {response.status_code}")

        except Exception as e:
            logger.error(f"SemanticScholar search failed: {e}")

        return papers

    def search(self, query: str, arxiv_only: bool = False) -> list[Paper]:
        """Main entry point"""
        results = []
        results.extend(self.search_arxiv(query))

        if not arxiv_only:
            results.extend(self.search_semantic_scholar(query))

        # deduplicate by title
        seen = set()
        unique = []
        for p in results:
            if p.title not in seen:
                seen.add(p.title)
                unique.append(p)

        logger.info(f"Total unique papers found: {len(unique)}")
        return unique

    def to_dict(self, papers: list[Paper]) -> list[dict]:
        return [p.__dict__ for p in papers]

    def close(self):
        self.client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="large language models")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--arxiv-only", action="store_true")
    args = parser.parse_args()

    agent = LiteratureAgent(max_results=args.limit)
    papers = agent.search(args.query, arxiv_only=args.arxiv_only)

    print(f"\n{'='*60}")
    print(f"Results for: '{args.query}'")
    print(f"{'='*60}")
    for i, p in enumerate(papers, 1):
        print(f"\n[{i}] {p.title}")
        print(f"    Source: {p.source}")
        print(f"    Authors: {', '.join(p.authors[:3])}")
        print(f"    Date: {p.published_date}")
        print(f"    Citations: {p.citation_count}")
        print(f"    Abstract: {p.abstract[:200]}...")

    agent.close()
"""
Week 6 – Product Knowledge Graph Builder
=========================================
Constructs a graph of products, features, companies, and categories using
NetworkX, provides reasoning queries (competitors, feature gaps, similarity),
and renders interactive HTML visualisations via PyVis.
"""

import os
import uuid
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter
from pathlib import Path

import networkx as nx
from pyvis.network import Network
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

# ---------------------------------------------------------------------------
# Langfuse initialisation (graceful no-op when keys are missing)
# ---------------------------------------------------------------------------
try:
    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com"),
    )
except Exception:
    langfuse = None  # tracing disabled

SESSION_ID = str(uuid.uuid4())


def _trace(name: str, **kwargs):
    """Return a Langfuse trace or a lightweight stub."""
    if langfuse:
        return langfuse.trace(name=name, session_id=SESSION_ID, **kwargs)

    class _Stub:
        input = None
        output = None
        def span(self, *a, **kw):
            return self
        def update(self, *a, **kw):
            return self
        def end(self, *a, **kw):
            return self

    return _Stub()


# ═══════════════════════════════════════════════════════════════════════════
# Node-type constants
# ═══════════════════════════════════════════════════════════════════════════
NODE_PRODUCT = "product"
NODE_FEATURE = "feature"
NODE_COMPANY = "company"
NODE_CATEGORY = "category"

EDGE_HAS_FEATURE = "has_feature"
EDGE_COMPETES_WITH = "competes_with"
EDGE_MANUFACTURED_BY = "manufactured_by"
EDGE_IN_CATEGORY = "in_category"

# Colour palette for visualisation
_COLORS = {
    NODE_PRODUCT: "#4FC3F7",   # light blue
    NODE_FEATURE: "#AED581",   # light green
    NODE_COMPANY: "#FFB74D",   # orange
    NODE_CATEGORY: "#CE93D8",  # purple
}

_SHAPES = {
    NODE_PRODUCT: "dot",
    NODE_FEATURE: "diamond",
    NODE_COMPANY: "star",
    NODE_CATEGORY: "triangle",
}


class ProductKnowledgeGraph:
    """Graph-based representation of the e-commerce competitive landscape."""

    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        self._products: List[Dict[str, Any]] = []
        self._companies: Set[str] = set()
        self._categories: Set[str] = set()
        self._features: Set[str] = set()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def add_products(self, products: List[Dict[str, Any]]) -> None:
        """Ingest normalised products and build all nodes + edges."""
        trace = _trace("kg_add_products", tags=["week-6"])
        trace.input = {"product_count": len(products)}

        self._products = products

        for p in products:
            pid = p.get("sku") or p.get("product_id", "")
            company = p.get("company", "Unknown")
            category = p.get("category", "Unknown")
            features = p.get("features_normalized") or p.get("features", [])

            # ── product node ──
            self.graph.add_node(
                pid,
                node_type=NODE_PRODUCT,
                label=p.get("product_name", pid),
                company=company,
                category=category,
                price=p.get("effective_price", p.get("price", 0)),
                features=features,
            )

            # ── company node + edge ──
            cid = f"company:{company}"
            if cid not in self.graph:
                self.graph.add_node(
                    cid,
                    node_type=NODE_COMPANY,
                    label=company,
                )
            self._companies.add(company)
            self.graph.add_edge(pid, cid, edge_type=EDGE_MANUFACTURED_BY, weight=1.0)

            # ── category node + edge ──
            cat_id = f"category:{category}"
            if cat_id not in self.graph:
                self.graph.add_node(
                    cat_id,
                    node_type=NODE_CATEGORY,
                    label=category,
                )
            self._categories.add(category)
            self.graph.add_edge(pid, cat_id, edge_type=EDGE_IN_CATEGORY, weight=1.0)

            # ── feature nodes + edges ──
            for feat in features:
                fid = f"feature:{feat}"
                if fid not in self.graph:
                    self.graph.add_node(
                        fid,
                        node_type=NODE_FEATURE,
                        label=feat,
                    )
                self._features.add(feat)
                self.graph.add_edge(pid, fid, edge_type=EDGE_HAS_FEATURE, weight=1.0)

        # ── competition edges ──
        self._build_competition_edges()

        trace.output = self.get_graph_stats()
        print(f"[INFO] Knowledge graph built: {self.get_graph_stats()}")

    def _build_competition_edges(self) -> None:
        """Connect products that share a category but belong to different companies."""
        product_nodes = [
            (nid, d)
            for nid, d in self.graph.nodes(data=True)
            if d.get("node_type") == NODE_PRODUCT
        ]
        for i, (pid_a, data_a) in enumerate(product_nodes):
            for pid_b, data_b in product_nodes[i + 1:]:
                if (
                    data_a["category"] == data_b["category"]
                    and data_a["company"] != data_b["company"]
                ):
                    # Weight by feature overlap (Jaccard similarity)
                    feats_a = set(data_a.get("features", []))
                    feats_b = set(data_b.get("features", []))
                    union = feats_a | feats_b
                    jaccard = len(feats_a & feats_b) / len(union) if union else 0
                    self.graph.add_edge(
                        pid_a,
                        pid_b,
                        edge_type=EDGE_COMPETES_WITH,
                        weight=round(jaccard, 3),
                        category=data_a["category"],
                    )

    # ------------------------------------------------------------------
    # Reasoning / query helpers
    # ------------------------------------------------------------------

    def find_competitors(self, product_id: str) -> List[Dict[str, Any]]:
        """Return products that compete with the given product."""
        trace = _trace("kg_find_competitors")
        trace.input = {"product_id": product_id}

        if product_id not in self.graph:
            trace.output = {"found": False}
            return []

        competitors = []
        for neighbour in self.graph.neighbors(product_id):
            edge = self.graph.edges[product_id, neighbour]
            if edge.get("edge_type") == EDGE_COMPETES_WITH:
                node = self.graph.nodes[neighbour]
                competitors.append({
                    "product_id": neighbour,
                    "product_name": node.get("label", ""),
                    "company": node.get("company", ""),
                    "category": node.get("category", ""),
                    "price": node.get("price", 0),
                    "similarity": edge.get("weight", 0),
                })

        competitors.sort(key=lambda c: c["similarity"], reverse=True)
        trace.output = {"competitor_count": len(competitors)}
        return competitors

    def find_feature_gaps(self, company: str) -> List[Dict[str, Any]]:
        """
        Features that competitors have but *company* does not offer
        in any product.
        """
        trace = _trace("kg_find_feature_gaps")
        trace.input = {"company": company}

        our_features: Set[str] = set()
        competitor_features: Dict[str, Set[str]] = {}

        for nid, data in self.graph.nodes(data=True):
            if data.get("node_type") != NODE_PRODUCT:
                continue
            feats = set(data.get("features", []))
            if data.get("company") == company:
                our_features |= feats
            else:
                comp = data.get("company", "")
                competitor_features.setdefault(comp, set()).update(feats)

        all_competitor_feats: Set[str] = set()
        for fs in competitor_features.values():
            all_competitor_feats |= fs

        missing = all_competitor_feats - our_features
        gaps = []
        for feat in sorted(missing):
            owners = [
                comp
                for comp, fs in competitor_features.items()
                if feat in fs
            ]
            gaps.append({
                "feature": feat,
                "available_from": owners,
                "competitor_count": len(owners),
            })

        trace.output = {"gap_count": len(gaps)}
        return gaps

    def find_similar_products(
        self, product_id: str, min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Products sharing the most features with the given product
        (regardless of company), ranked by Jaccard similarity.
        """
        trace = _trace("kg_find_similar")
        trace.input = {"product_id": product_id}

        if product_id not in self.graph:
            trace.output = {"found": False}
            return []

        target_feats = set(self.graph.nodes[product_id].get("features", []))
        results = []

        for nid, data in self.graph.nodes(data=True):
            if data.get("node_type") != NODE_PRODUCT or nid == product_id:
                continue
            other_feats = set(data.get("features", []))
            union = target_feats | other_feats
            jaccard = len(target_feats & other_feats) / len(union) if union else 0
            if jaccard >= min_similarity:
                results.append({
                    "product_id": nid,
                    "product_name": data.get("label", ""),
                    "company": data.get("company", ""),
                    "category": data.get("category", ""),
                    "price": data.get("price", 0),
                    "shared_features": sorted(target_feats & other_feats),
                    "similarity": round(jaccard, 3),
                })

        results.sort(key=lambda r: r["similarity"], reverse=True)
        trace.output = {"similar_count": len(results)}
        return results

    def get_products_with_feature(self, feature: str) -> List[Dict[str, Any]]:
        """All products that have the specified feature."""
        fid = f"feature:{feature}"
        if fid not in self.graph:
            return []

        products = []
        for neighbour in self.graph.neighbors(fid):
            edge = self.graph.edges[fid, neighbour]
            if edge.get("edge_type") == EDGE_HAS_FEATURE:
                node = self.graph.nodes[neighbour]
                if node.get("node_type") == NODE_PRODUCT:
                    products.append({
                        "product_id": neighbour,
                        "product_name": node.get("label", ""),
                        "company": node.get("company", ""),
                        "category": node.get("category", ""),
                        "price": node.get("price", 0),
                    })
        return products

    def get_company_products(self, company: str) -> List[Dict[str, Any]]:
        """All products manufactured by *company*."""
        cid = f"company:{company}"
        if cid not in self.graph:
            return []

        products = []
        for neighbour in self.graph.neighbors(cid):
            edge = self.graph.edges[cid, neighbour]
            if edge.get("edge_type") == EDGE_MANUFACTURED_BY:
                node = self.graph.nodes[neighbour]
                if node.get("node_type") == NODE_PRODUCT:
                    products.append({
                        "product_id": neighbour,
                        "product_name": node.get("label", ""),
                        "category": node.get("category", ""),
                        "price": node.get("price", 0),
                    })
        return products

    def get_category_stats(self) -> List[Dict[str, Any]]:
        """Per-category product count and average price."""
        cat_stats: Dict[str, Dict[str, Any]] = {}
        for nid, data in self.graph.nodes(data=True):
            if data.get("node_type") != NODE_PRODUCT:
                continue
            cat = data.get("category", "")
            entry = cat_stats.setdefault(cat, {"count": 0, "prices": []})
            entry["count"] += 1
            entry["prices"].append(data.get("price", 0))

        results = []
        for cat, info in sorted(cat_stats.items()):
            prices = info["prices"]
            results.append({
                "category": cat,
                "product_count": info["count"],
                "avg_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
            })
        return results

    def get_feature_frequency(self) -> List[Tuple[str, int]]:
        """Features ranked by number of products using them."""
        counter: Counter = Counter()
        for nid, data in self.graph.nodes(data=True):
            if data.get("node_type") == NODE_PRODUCT:
                for f in data.get("features", []):
                    counter[f] += 1
        return counter.most_common()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_graph_stats(self) -> Dict[str, Any]:
        """Summary statistics of the knowledge graph."""
        type_counts: Dict[str, int] = Counter()
        for _, data in self.graph.nodes(data=True):
            type_counts[data.get("node_type", "unknown")] += 1

        edge_counts: Dict[str, int] = Counter()
        for _, _, data in self.graph.edges(data=True):
            edge_counts[data.get("edge_type", "unknown")] += 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "products": type_counts.get(NODE_PRODUCT, 0),
            "features": type_counts.get(NODE_FEATURE, 0),
            "companies": type_counts.get(NODE_COMPANY, 0),
            "categories": type_counts.get(NODE_CATEGORY, 0),
            "has_feature_edges": edge_counts.get(EDGE_HAS_FEATURE, 0),
            "competes_with_edges": edge_counts.get(EDGE_COMPETES_WITH, 0),
            "manufactured_by_edges": edge_counts.get(EDGE_MANUFACTURED_BY, 0),
            "in_category_edges": edge_counts.get(EDGE_IN_CATEGORY, 0),
        }

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def visualize(
        self,
        output_path: str = "./outputs/knowledge_graph.html",
        height: str = "800px",
        width: str = "100%",
        show_features: bool = True,
    ) -> str:
        """
        Render the knowledge graph as an interactive HTML file using PyVis.
        Returns the absolute path to the generated file.
        """
        trace = _trace("kg_visualize")
        trace.input = {"output_path": output_path, "show_features": show_features}

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        net = Network(
            height=height,
            width=width,
            bgcolor="#1a1a2e",
            font_color="white",
            directed=False,
            notebook=False,
        )
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=150,
            spring_strength=0.05,
        )

        for nid, data in self.graph.nodes(data=True):
            ntype = data.get("node_type", "")
            if ntype == NODE_FEATURE and not show_features:
                continue

            label = data.get("label", nid)
            color = _COLORS.get(ntype, "#FFFFFF")
            shape = _SHAPES.get(ntype, "dot")

            # Size by type
            if ntype == NODE_COMPANY:
                size = 40
            elif ntype == NODE_CATEGORY:
                size = 30
            elif ntype == NODE_PRODUCT:
                size = 20
            else:
                size = 12

            title_parts = [f"<b>{label}</b>", f"Type: {ntype}"]
            if ntype == NODE_PRODUCT:
                title_parts.append(f"Company: {data.get('company', '')}")
                title_parts.append(f"Category: {data.get('category', '')}")
                title_parts.append(f"Price: ${data.get('price', 0):.2f}")
                feats = data.get("features", [])
                if feats:
                    title_parts.append(f"Features: {', '.join(feats[:6])}")

            net.add_node(
                nid,
                label=label,
                color=color,
                shape=shape,
                size=size,
                title="<br>".join(title_parts),
            )

        for src, dst, data in self.graph.edges(data=True):
            etype = data.get("edge_type", "")
            # Skip feature edges if hidden
            if not show_features and etype == EDGE_HAS_FEATURE:
                continue

            edge_colors = {
                EDGE_HAS_FEATURE: "#66BB6A",
                EDGE_COMPETES_WITH: "#EF5350",
                EDGE_MANUFACTURED_BY: "#FFA726",
                EDGE_IN_CATEGORY: "#AB47BC",
            }
            color = edge_colors.get(etype, "#888888")
            width = 3 if etype == EDGE_COMPETES_WITH else 1.5
            dashes = etype == EDGE_COMPETES_WITH

            title = etype.replace("_", " ").title()
            weight = data.get("weight", 0)
            if weight and etype == EDGE_COMPETES_WITH:
                title += f" (similarity: {weight:.2f})"

            net.add_edge(
                src, dst,
                color=color,
                width=width,
                dashes=dashes,
                title=title,
            )

        net.save_graph(output_path)
        abs_path = str(Path(output_path).resolve())
        trace.output = {"saved": abs_path}
        print(f"[INFO] Knowledge graph visualisation saved → {abs_path}")
        return abs_path

    def visualize_company_view(
        self, output_path: str = "./outputs/knowledge_graph_companies.html"
    ) -> str:
        """Simplified view showing only companies, categories, and products."""
        return self.visualize(output_path=output_path, show_features=False)

    def visualize_feature_view(
        self,
        feature: str,
        output_path: str = "./outputs/knowledge_graph_feature.html",
    ) -> str:
        """Sub-graph centred on a single feature and its connected products."""
        trace = _trace("kg_visualize_feature")
        trace.input = {"feature": feature}

        fid = f"feature:{feature}"
        if fid not in self.graph:
            print(f"[WARN] Feature '{feature}' not in graph")
            trace.output = {"found": False}
            return ""

        # BFS depth-2 from feature node
        sub_nodes = {fid}
        for neighbour in self.graph.neighbors(fid):
            sub_nodes.add(neighbour)
            for nn in self.graph.neighbors(neighbour):
                nd = self.graph.nodes[nn]
                if nd.get("node_type") in (NODE_COMPANY, NODE_CATEGORY):
                    sub_nodes.add(nn)

        subgraph = self.graph.subgraph(sub_nodes)
        temp_kg = ProductKnowledgeGraph()
        temp_kg.graph = subgraph.copy()
        path = temp_kg.visualize(output_path=output_path, show_features=True)
        trace.output = {"saved": path, "nodes": len(sub_nodes)}
        return path


# ═══════════════════════════════════════════════════════════════════════════
# Standalone entry-point
# ═══════════════════════════════════════════════════════════════════════════

def _load_products() -> List[Dict[str, Any]]:
    """Load normalised products from Week 2 processor."""
    try:
        from product_catalog_processor import (
            COMPANY_X_CATALOG,
            COMPANY_Y_CATALOG,
            TracedProductCatalogProcessor,
        )
        processor = TracedProductCatalogProcessor()
        products_x = processor.process_catalog_with_tracing(COMPANY_X_CATALOG)
        products_y = processor.process_catalog_with_tracing(COMPANY_Y_CATALOG)
        return products_x + products_y
    except ImportError:
        print("[WARN] product_catalog_processor unavailable")
        return []


def main() -> None:
    print("\n" + "=" * 60)
    print("WEEK 6 – PRODUCT KNOWLEDGE GRAPH")
    print("=" * 60)

    products = _load_products()
    if not products:
        print("[ERROR] No products loaded – aborting")
        return
    print(f"[INFO] Loaded {len(products)} normalised products")

    kg = ProductKnowledgeGraph()
    kg.add_products(products)

    stats = kg.get_graph_stats()
    print("\n── Graph Statistics ─────────────────────────────")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Competitor queries
    print("\n── Competitor Queries ───────────────────────────")
    sample_sku = products[0].get("sku", "")
    competitors = kg.find_competitors(sample_sku)
    print(f"  Competitors of {sample_sku}:")
    for c in competitors:
        print(
            f"    → {c['product_name']} ({c['company']}) "
            f"similarity={c['similarity']:.2f}"
        )

    # Feature gaps
    print("\n── Feature Gaps ─────────────────────────────────")
    for company in sorted(kg._companies):
        gaps = kg.find_feature_gaps(company)
        print(f"  {company} is missing {len(gaps)} features:")
        for g in gaps[:5]:
            print(f"    → {g['feature']}  (from: {', '.join(g['available_from'])})")

    # Feature frequency
    print("\n── Feature Frequency ────────────────────────────")
    for feat, count in kg.get_feature_frequency()[:10]:
        print(f"  {feat}: {count} products")

    # Category stats
    print("\n── Category Stats ──────────────────────────────")
    for cs in kg.get_category_stats():
        print(
            f"  {cs['category']}: {cs['product_count']} products, "
            f"avg ${cs['avg_price']:.2f}"
        )

    # Visualisations
    print("\n── Generating Visualisations ────────────────────")
    kg.visualize("./outputs/knowledge_graph.html")
    kg.visualize_company_view("./outputs/knowledge_graph_companies.html")

    # Feature sub-graph for the most common feature
    top_feature = kg.get_feature_frequency()[0][0] if kg.get_feature_frequency() else None
    if top_feature:
        kg.visualize_feature_view(
            top_feature,
            f"./outputs/knowledge_graph_feature_{top_feature.replace(' ', '_')}.html",
        )

    print("\n✅ Week 6 complete – knowledge graph built and visualised")
    print("=" * 60)


if __name__ == "__main__":
    main()

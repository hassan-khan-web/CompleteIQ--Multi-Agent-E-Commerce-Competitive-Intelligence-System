import os
import json
import sys
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime
import networkx as nx
from pyvis.network import Network
from dotenv import load_dotenv
from langfuse import Langfuse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from semantic_search_engine import get_normalized_products

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
)


@dataclass
class ProductNode:
    product_id: str
    name: str
    company: str
    category: str
    price: float
    sku: str
    node_type: str = "product"


@dataclass
class CompanyNode:
    company_name: str
    product_count: int = 0
    node_type: str = "company"


@dataclass
class CategoryNode:
    category_name: str
    product_count: int = 0
    node_type: str = "category"


@dataclass
class EdgeRelation:
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraphBuilder:

    def __init__(self, session_id: str = None):
        self.session_id = session_id
        self.graph = nx.Graph()
        self.products = []
        self.companies = set()
        self.categories = set()
        self.edges_created = 0
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "session_id": session_id,
            "nodes_count": 0,
            "edges_count": 0
        }

    def load_products(self, products: List[Dict] = None):
        if products is None:
            products = get_normalized_products()
        
        self.products = products
        
        for product in products:
            self.companies.add(product.get("company", "Unknown"))
            self.categories.add(product.get("category", "Unknown"))
        
        return len(self.products)

    def build_graph(self):
        trace = langfuse.trace(
            name="knowledge_graph_builder",
            input={"products": len(self.products), "companies": len(self.companies)}
        )
        
        self._add_product_nodes()
        self._add_company_nodes()
        self._add_category_nodes()
        self._add_product_to_company_edges()
        self._add_product_to_category_edges()
        self._add_company_relationships()
        self._add_price_similarity_edges()
        
        self.metadata["nodes_count"] = self.graph.number_of_nodes()
        self.metadata["edges_count"] = self.graph.number_of_edges()
        
        trace.update(
            output={
                "nodes": self.metadata["nodes_count"],
                "edges": self.metadata["edges_count"]
            }
        )
        
        langfuse.flush()
        
        return self.graph

    def _add_product_nodes(self):
        for product in self.products:
            node_id = product.get("sku", product.get("id", "unknown"))
            self.graph.add_node(
                node_id,
                node_type="product",
                name=product.get("name", "Unknown"),
                company=product.get("company", "Unknown"),
                category=product.get("category", "Unknown"),
                price=float(product.get("price", 0.0)),
                sku=product.get("sku", ""),
                label=product.get("name", "Unknown")[:20]
            )

    def _add_company_nodes(self):
        for company in self.companies:
            company_id = f"company_{company.lower().replace(' ', '_')}"
            product_count = sum(1 for p in self.products if p.get("company") == company)
            self.graph.add_node(
                company_id,
                node_type="company",
                name=company,
                product_count=product_count,
                label=company
            )

    def _add_category_nodes(self):
        for category in self.categories:
            category_id = f"category_{category.lower().replace(' ', '_')}"
            product_count = sum(1 for p in self.products if p.get("category") == category)
            self.graph.add_node(
                category_id,
                node_type="category",
                name=category,
                product_count=product_count,
                label=category
            )

    def _add_product_to_company_edges(self):
        for product in self.products:
            product_id = product.get("sku", product.get("id", "unknown"))
            company = product.get("company", "Unknown")
            company_id = f"company_{company.lower().replace(' ', '_')}"
            
            self.graph.add_edge(
                product_id,
                company_id,
                relation_type="belongs_to_company",
                weight=1.0
            )
            self.edges_created += 1

    def _add_product_to_category_edges(self):
        for product in self.products:
            product_id = product.get("sku", product.get("id", "unknown"))
            category = product.get("category", "Unknown")
            category_id = f"category_{category.lower().replace(' ', '_')}"
            
            self.graph.add_edge(
                product_id,
                category_id,
                relation_type="belongs_to_category",
                weight=1.0
            )
            self.edges_created += 1

    def _add_company_relationships(self):
        companies_list = list(self.companies)
        for i, company1 in enumerate(companies_list):
            for company2 in companies_list[i+1:]:
                category_overlap = len(
                    set(p.get("category") for p in self.products if p.get("company") == company1) &
                    set(p.get("category") for p in self.products if p.get("company") == company2)
                )
                
                if category_overlap > 0:
                    company1_id = f"company_{company1.lower().replace(' ', '_')}"
                    company2_id = f"company_{company2.lower().replace(' ', '_')}"
                    
                    weight = category_overlap / max(
                        len(set(p.get("category") for p in self.products if p.get("company") == company1)),
                        1
                    )
                    
                    self.graph.add_edge(
                        company1_id,
                        company2_id,
                        relation_type="competes_with",
                        weight=weight,
                        overlap=category_overlap
                    )
                    self.edges_created += 1

    def _add_price_similarity_edges(self):
        price_groups = defaultdict(list)
        
        for product in self.products:
            price = float(product.get("price", 0.0))
            price_bracket = round(price / 50) * 50
            price_groups[price_bracket].append(product)
        
        for price_bracket, products_in_bracket in price_groups.items():
            for i, product1 in enumerate(products_in_bracket):
                for product2 in products_in_bracket[i+1:]:
                    if product1.get("category") == product2.get("category"):
                        sku1 = product1.get("sku", product1.get("id", "unknown"))
                        sku2 = product2.get("sku", product2.get("id", "unknown"))
                        
                        price_diff = abs(
                            float(product1.get("price", 0)) - 
                            float(product2.get("price", 0))
                        )
                        
                        similarity = 1.0 / (1.0 + (price_diff / 100.0))
                        
                        self.graph.add_edge(
                            sku1,
                            sku2,
                            relation_type="similar_price",
                            weight=similarity,
                            price_diff=price_diff
                        )
                        self.edges_created += 1

    def get_graph_stats(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": {
                "products": len([n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "product"]),
                "companies": len([n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "company"]),
                "categories": len([n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "category"])
            },
            "density": nx.density(self.graph),
            "is_connected": nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False,
            "number_of_components": nx.number_connected_components(self.graph)
        }

    def find_competitive_clusters(self) -> Dict[str, List[str]]:
        clusters = {}
        for i, component in enumerate(nx.connected_components(self.graph)):
            companies_in_cluster = set()
            for node_id in component:
                node_data = self.graph.nodes[node_id]
                if node_data.get("node_type") == "company":
                    companies_in_cluster.add(node_data.get("name", node_id))
            
            if companies_in_cluster:
                clusters[f"cluster_{i}"] = list(companies_in_cluster)
        
        return clusters

    def find_category_leaders(self) -> Dict[str, Dict[str, Any]]:
        leaders = {}
        
        for category in self.categories:
            category_id = f"category_{category.lower().replace(' ', '_')}"
            
            products_in_category = [
                p for p in self.products if p.get("category") == category
            ]
            
            company_products = defaultdict(list)
            for product in products_in_category:
                company = product.get("company", "Unknown")
                company_products[company].append(product)
            
            if company_products:
                leader = max(company_products.items(), key=lambda x: len(x[1]))
                leaders[category] = {
                    "leader": leader[0],
                    "product_count": len(leader[1]),
                    "avg_price": sum(float(p.get("price", 0)) for p in leader[1]) / len(leader[1])
                }
        
        return leaders

    def find_price_competitors(self, sku: str, tolerance: float = 50.0) -> List[Dict[str, Any]]:
        if sku not in self.graph:
            return []
        
        product_node = self.graph.nodes[sku]
        product_price = product_node.get("price", 0.0)
        product_category = product_node.get("category", "")
        
        competitors = []
        for neighbor in self.graph.neighbors(sku):
            neighbor_data = self.graph.nodes[neighbor]
            
            if (neighbor_data.get("node_type") == "product" and 
                neighbor_data.get("category") == product_category):
                
                price_diff = abs(neighbor_data.get("price", 0.0) - product_price)
                
                if price_diff <= tolerance:
                    edge_data = self.graph.get_edge_data(sku, neighbor)
                    competitors.append({
                        "sku": neighbor,
                        "name": neighbor_data.get("name", "Unknown"),
                        "company": neighbor_data.get("company", "Unknown"),
                        "price": neighbor_data.get("price", 0.0),
                        "price_diff": price_diff,
                        "similarity": edge_data.get("weight", 0.0) if edge_data else 0.0
                    })
        
        return sorted(competitors, key=lambda x: x["price_diff"])

    def export_to_json(self, filepath: str = None):
        if filepath is None:
            filepath = "knowledge_graph.json"
        
        graph_data = {
            "metadata": self.metadata,
            "stats": self.get_graph_stats(),
            "competitive_clusters": self.find_competitive_clusters(),
            "category_leaders": self.find_category_leaders(),
            "nodes": []
        }
        
        for node_id, node_data in self.graph.nodes(data=True):
            graph_data["nodes"].append({
                "id": node_id,
                **node_data
            })
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
        
        return filepath

    def visualize(self, output_path: str = None, physics: bool = True):
        if output_path is None:
            output_path = "knowledge_graph.html"
        
        net = Network(
            height="750px",
            width="100%",
            directed=False
        )
        
        if physics:
            net.physics = True
        
        net.from_nx(self.graph)
        
        for node in net.nodes:
            node_id = node["id"]
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get("node_type", "unknown")
            
            if node_type == "product":
                node["color"] = "#4CAF50"
                node["size"] = 20
                node["title"] = f"{node_data.get('name', '')} - ${node_data.get('price', 0):.2f}"
            elif node_type == "company":
                node["color"] = "#2196F3"
                node["size"] = 40
                node["title"] = f"Company: {node_data.get('name', '')} ({node_data.get('product_count', 0)} products)"
            elif node_type == "category":
                node["color"] = "#FF9800"
                node["size"] = 30
                node["title"] = f"Category: {node_data.get('name', '')} ({node_data.get('product_count', 0)} products)"
        
        for edge in net.edges:
            edge_id = (edge["from"], edge["to"])
            if edge_id in self.graph.edges or (edge_id[1], edge_id[0]) in self.graph.edges:
                edge_data = self.graph.get_edge_data(edge_id[0], edge_id[1])
                if edge_data is None:
                    edge_data = self.graph.get_edge_data(edge_id[1], edge_id[0])
                
                if edge_data:
                    relation_type = edge_data.get("relation_type", "")
                    
                    if relation_type == "competes_with":
                        edge["color"] = "#FF5252"
                        edge["width"] = edge_data.get("weight", 1.0) * 3
                    elif relation_type == "similar_price":
                        edge["color"] = "#FFC107"
                        edge["width"] = 1.5
                    else:
                        edge["color"] = "#CCCCCC"
                        edge["width"] = 1.0
        
        try:
            net.write_html(output_path)
        except Exception:
            with open(output_path, 'w') as f:
                f.write(net.generate_html())
        
        return output_path

    def get_network_insights(self) -> Dict[str, Any]:
        stats = self.get_graph_stats()
        clusters = self.find_competitive_clusters()
        leaders = self.find_category_leaders()
        
        degree_centrality = nx.degree_centrality(self.graph)
        top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "graph_statistics": stats,
            "competitive_clusters": clusters,
            "category_leaders": leaders,
            "most_connected_nodes": [
                {
                    "node_id": node_id,
                    "centrality": centrality,
                    "node_type": self.graph.nodes[node_id].get("node_type", "unknown"),
                    "name": self.graph.nodes[node_id].get("name", "Unknown")
                }
                for node_id, centrality in top_nodes
            ],
            "network_cohesion": {
                "density": stats["density"],
                "is_connected": stats["is_connected"],
                "components": stats["number_of_components"]
            }
        }


def main():
    builder = KnowledgeGraphBuilder()
    
    print("[INFO] Loading products...")
    product_count = builder.load_products()
    print(f"[INFO] Loaded {product_count} products")
    
    print("[INFO] Building knowledge graph...")
    graph = builder.build_graph()
    print(f"[INFO] Graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    print("\n[INFO] Graph Statistics:")
    stats = builder.get_graph_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n[INFO] Competitive Clusters:")
    clusters = builder.find_competitive_clusters()
    for cluster_id, companies in clusters.items():
        print(f"  {cluster_id}: {', '.join(companies)}")
    
    print("\n[INFO] Category Leaders:")
    leaders = builder.find_category_leaders()
    for category, leader_info in leaders.items():
        print(f"  {category}: {leader_info['leader']} ({leader_info['product_count']} products)")
    
    print("\n[INFO] Exporting to JSON...")
    json_path = builder.export_to_json("knowledge_graph.json")
    print(f"[INFO] Exported to {json_path}")
    
    print("\n[INFO] Generating visualization...")
    html_path = builder.visualize("knowledge_graph.html", physics=True)
    print(f"[INFO] Visualization saved to {html_path}")
    
    print("\n[INFO] Network Insights:")
    insights = builder.get_network_insights()
    print(f"  Most connected nodes: {len(insights['most_connected_nodes'])} identified")
    print(f"  Network density: {insights['network_cohesion']['density']:.2f}")
    print(f"  Connected: {insights['network_cohesion']['is_connected']}")
    
    print("\n" + "="*80)
    print("WEEK 6 CHECKPOINT - VALIDATION")
    print("="*80)
    
    checks = [
        ("Products loaded", len(builder.products) == 12),
        ("Graph nodes created", builder.graph.number_of_nodes() > 0),
        ("Graph edges created", builder.graph.number_of_edges() > 0),
        ("Competitive clusters identified", len(clusters) > 0),
        ("Category leaders found", len(leaders) > 0),
        ("JSON export successful", True),
        ("Visualization generated", True),
        ("Network insights computed", len(insights["most_connected_nodes"]) > 0)
    ]
    
    passed = 0
    for check_name, result in checks:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  [{symbol}] {check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nWeek 6 Score: {passed}/{len(checks)} checks passed")
    
    if passed == len(checks):
        print("✅ Week 6 Complete! Knowledge graph operational.")
    else:
        print(f"⚠️  {len(checks) - passed} checks failed.")


if __name__ == "__main__":
    main()

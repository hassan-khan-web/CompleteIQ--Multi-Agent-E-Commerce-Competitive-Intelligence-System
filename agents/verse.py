from typing import List, Dict, Any
from langfuse import Langfuse

from .base_models import MarketingContent


class Verse:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = "Verse"

    def generate_product_content(self, product: Dict[str, Any]) -> MarketingContent:
        trace = self.langfuse.trace(
            name="verse_generate_product",
            session_id=self.session_id,
        )
        trace.input = {"product_id": product.get("sku")}
        
        product_id = product.get("sku", "")
        product_name = product.get("product_name", "")
        category = product.get("category", "")
        price = product.get("effective_price", 0)
        features = product.get("features", [])
        
        tone = "professional"
        if price < 100:
            tone = "casual_accessible"
        elif price > 200:
            tone = "premium_sophisticated"
        
        if "headphones" in product_name.lower() or "earbuds" in product_name.lower():
            headline = f"{product_name}: Premium Audio Experience"
            key_points = [
                "Crystal clear sound quality",
                "Long battery life",
                "Comfortable fit",
                "Wireless connectivity"
            ]
        elif "watch" in product_name.lower():
            headline = f"{product_name}: Your Fitness & Health Companion"
            key_points = [
                "Advanced health monitoring",
                "All-day battery life",
                "Water resistant design",
                "Smart notifications"
            ]
        elif "speaker" in product_name.lower():
            headline = f"{product_name}: Portable Sound System"
            key_points = [
                "Powerful sound output",
                "Waterproof design",
                "Long battery duration",
                "Bluetooth connectivity"
            ]
        else:
            headline = f"{product_name}: Innovation in {category}"
            key_points = [f"Feature: {f}" for f in features[:3]]
        
        description = f"{product_name} delivers exceptional value in the {category} market. "
        description += f"Designed for those who demand quality and reliability. "
        description += f"Available at ${price:.2f}, offering competitive pricing and premium features."
        
        content = MarketingContent(
            product_id=product_id,
            product_name=product_name,
            category=category,
            headline=headline,
            description=description,
            key_selling_points=key_points,
            tone=tone,
            confidence_score=0.88,
            reasoning=f"Content generated based on product category and pricing tier"
        )
        
        trace.output = {
            "headline": headline,
            "tone": tone,
            "key_points_count": len(key_points)
        }
        
        return content

    def generate_catalog_content(self, products: List[Dict[str, Any]]) -> List[MarketingContent]:
        trace = self.langfuse.trace(
            name="verse_generate_catalog",
            session_id=self.session_id,
        )
        trace.input = {"product_count": len(products)}
        
        contents = []
        for product in products:
            content = self.generate_product_content(product)
            contents.append(content)
        
        trace.output = {"generated_count": len(contents)}
        return contents

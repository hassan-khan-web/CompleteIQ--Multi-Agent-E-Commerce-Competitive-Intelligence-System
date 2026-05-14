from pydantic import BaseModel
from typing import List, Dict, Optional


class PriceAnalysis(BaseModel):
    product_id: str
    product_name: str
    current_price: float
    competitor_price: Optional[float]
    price_difference: float
    recommendation: str
    confidence_score: float
    reasoning: str


class CatalogAnalysis(BaseModel):
    company: str
    total_products: int
    categories: List[str]
    avg_price: float
    price_range: Dict[str, float]
    competitive_strength: str
    market_position: str
    confidence_score: float
    reasoning: str


class MarketingContent(BaseModel):
    product_id: str
    product_name: str
    category: str
    headline: str
    description: str
    key_selling_points: List[str]
    tone: str
    confidence_score: float
    reasoning: str

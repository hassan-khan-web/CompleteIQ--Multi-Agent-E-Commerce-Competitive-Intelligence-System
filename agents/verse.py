from typing import List, Dict, Any
from langfuse import Langfuse
from .base_models import MarketingContent
from .llm_utils import create_content_chain, _rate_limited_invoke

class Verse:

    def __init__(self, search_engine, langfuse: Langfuse, session_id: str, openrouter_api_key: str, model: str):
        self.search_engine = search_engine
        self.langfuse = langfuse
        self.session_id = session_id
        self.name = 'Verse'
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.chain = create_content_chain(openrouter_api_key, model)

    def generate_product_content(self, product: Dict[str, Any]) -> MarketingContent:
        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name='verse_generate_product', session_id=self.session_id)
            trace.input = {'product_id': product.get('sku'), 'model': self.model}
        try:
            product_id = product.get('sku', '')
            product_name = product.get('product_name', '')
            category = product.get('category', '')
            price = product.get('effective_price', 0)
            features = product.get('features', [])
            company = product.get('company', '')
            similar_products = self.search_engine.search_with_filters(product_name, category=category, k=5)
            competitor_name = 'N/A'
            competitor_price = 0
            advantages = []
            if similar_products:
                for p in similar_products:
                    if p['company'] != company:
                        competitor_name = p['company']
                        competitor_price = p.get('effective_price', 0)
                        our_features = set(features)
                        competitor_features = set(p.get('features', []))
                        advantages = list(our_features - competitor_features)
                        break
            if price < 100:
                tone = 'casual_accessible'
                target_audience = 'budget-conscious consumers'
            elif price > 200:
                tone = 'premium_sophisticated'
                target_audience = 'premium buyers seeking excellence'
            else:
                tone = 'professional'
                target_audience = 'value-focused consumers'
            llm_input = {'product_name': product_name, 'category': category, 'price': price, 'features': ', '.join(features[:5]) if features else 'quality product', 'company': company, 'competitor_name': competitor_name, 'competitor_price': competitor_price, 'advantages': ', '.join(advantages[:3]) if advantages else 'premium features', 'target_audience': target_audience}
            llm_output = _rate_limited_invoke(self.chain, llm_input)
            headline = llm_output.get('headline', f'{product_name}: Premium Choice')
            description = llm_output.get('description', f'Discover {product_name} - innovation meets quality.')
            key_points = llm_output.get('key_selling_points', features[:4])
            call_to_action = llm_output.get('call_to_action', 'Order Now')
            confidence = llm_output.get('confidence_score', 0.88)
            content = MarketingContent(product_id=product_id, product_name=product_name, category=category, headline=headline, description=description, key_selling_points=key_points, tone=tone, confidence_score=confidence, reasoning=f'LLM-generated content for {category} targeting {target_audience}')
            if trace:
                trace.output = {'headline': headline, 'tone': tone, 'key_points_count': len(key_points), 'model': self.model}
            return content
        except Exception as e:
            print(f'[WARN] Verse LLM failed: {str(e)}, using fallback logic')
            if trace:
                trace.output = {'error': str(e), 'fallback': True}
            return self._fallback_product_content(product)

    def _fallback_product_content(self, product: Dict[str, Any]) -> MarketingContent:
        product_id = product.get('sku', '')
        product_name = product.get('product_name', '')
        category = product.get('category', '')
        price = product.get('effective_price', 0)
        features = product.get('features', [])
        company = product.get('company', 'Our Company')

        if price < 100:
            tone = 'casual_accessible'
        elif price > 200:
            tone = 'premium_sophisticated'
        else:
            tone = 'professional'

        # Extract top features for natural sentence weaving
        feat_1 = features[0] if len(features) > 0 else "premium build quality"
        feat_2 = features[1] if len(features) > 1 else "advanced ergonomic design"
        feat_str = f"{feat_1.lower()} and {feat_2.lower()}"

        # Dynamic Headline Rotation based on hash of product name
        style_idx = abs(hash(product_name)) % 4
        if style_idx == 0:
            headline = f"{product_name}: Experience {feat_1}"
        elif style_idx == 1:
            headline = f"Elevate Your {category} with {product_name}"
        elif style_idx == 2:
            headline = f"{product_name} — Engineered for Excellence"
        else:
            headline = f"Uncompromising Quality: The {product_name}"

        # Dynamic Description Framework Rotation
        if style_idx == 0:  # Feature Showcase
            description = f"Immerse yourself in superior performance with the {product_name}. Featuring {feat_str}, it sets a new standard for {category.lower()} at an accessible ${price:.2f} price point."
        elif style_idx == 1:  # Benefit-First
            description = f"Transform your daily routine with {product_name}. Designed specifically for demanding users, this premium {category.lower()} combines {feat_str} into a sleek, highly durable build."
        elif style_idx == 2:  # Value Proposition
            description = f"Why compromise on quality? The {product_name} by {company} delivers top-tier engineering—highlighted by {feat_str}—all while maintaining an ultra-competitive ${price:.2f} tag."
        else:  # Premium Exclusivity
            description = f"Discover the ultimate {category.lower()} experience. The {product_name} integrates state-of-the-art {feat_str} to provide unmatched reliability and aesthetic elegance."

        # Dynamic Selling Points using actual product features
        key_points = []
        for f in features[:4]:
            key_points.append(f)
        
        # Ensure we always have 4 strong selling points
        fallback_points = ["Optimized power efficiency", "Premium durable construction", "Seamless universal compatibility", "1-Year manufacturer warranty"]
        while len(key_points) < 4:
            key_points.append(fallback_points[len(key_points)])

        return MarketingContent(
            product_id=product_id, 
            product_name=product_name, 
            category=category, 
            headline=headline, 
            description=description, 
            key_selling_points=key_points, 
            tone=tone, 
            confidence_score=0.88, 
            reasoning=f'Dynamic heuristic generation targeting {tone} audience'
        )

    def generate_catalog_content(self, products: List[Dict[str, Any]]) -> List[MarketingContent]:
        trace = None
        if self.langfuse:
            trace = self.langfuse.trace(name='verse_generate_catalog', session_id=self.session_id)
            trace.input = {'product_count': len(products), 'model': self.model}
        contents = []
        for product in products:
            content = self.generate_product_content(product)
            contents.append(content)
        if trace:
            trace.output = {'generated_count': len(contents), 'model': self.model}
        return contents
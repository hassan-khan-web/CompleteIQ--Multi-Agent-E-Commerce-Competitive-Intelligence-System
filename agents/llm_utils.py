from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class PricingRecommendation(BaseModel):
    product_id: str = Field(description='Product SKU')
    product_name: str = Field(description='Product name')
    current_price: float = Field(description='Current product price')
    competitor_price: float | None = Field(description='Competitor price')
    recommendation: str = Field(description='REDUCE_PRICE, INCREASE_PRICE, or MAINTAIN_PRICE')
    confidence_score: float = Field(description='Confidence 0-1')
    reasoning: str = Field(description='Reasoning for recommendation')

class MarketPositioningAnalysis(BaseModel):
    company: str = Field(description='Company name')
    competitive_strength: str = Field(description='PREMIUM, VALUE, or BALANCED')
    market_position: str = Field(description='Overall market position')
    key_insights: list[str] = Field(description='Key competitive insights')
    confidence_score: float = Field(description='Confidence 0-1')
    reasoning: str = Field(description='Analysis reasoning')

class MarketingContentOutput(BaseModel):
    product_id: str = Field(description='Product SKU')
    headline: str = Field(description='Marketing headline')
    description: str = Field(description='Product description')
    key_selling_points: list[str] = Field(description='Top 4 selling points')
    tone: str = Field(description='Tone of content')
    call_to_action: str = Field(description='Call to action')
    confidence_score: float = Field(description='Confidence 0-1')

def create_llm_beacon(openrouter_api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(api_key=openrouter_api_key, base_url='https://openrouter.ai/api/v1', model=model, temperature=0.3, max_tokens=400, model_kwargs={"max_tokens": 400})

def create_llm_nexus(openrouter_api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(api_key=openrouter_api_key, base_url='https://openrouter.ai/api/v1', model=model, temperature=0.5, max_tokens=400, model_kwargs={"max_tokens": 400})

def create_llm_verse(openrouter_api_key: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(api_key=openrouter_api_key, base_url='https://openrouter.ai/api/v1', model=model, temperature=0.7, max_tokens=400, model_kwargs={"max_tokens": 400})

def get_beacon_prompt() -> PromptTemplate:
    return PromptTemplate.from_template('\nYou are a pricing analyst AI. Analyze the following product pricing data and recommend a pricing strategy.\n\nProduct Information:\n- Name: {product_name}\n- Current Price: ${current_price:.2f}\n- Category: {category}\n- Company: {company}\n- Features: {features}\n\nCompetitor Information:\n- Competitor Name: {competitor_name}\n- Competitor Price: ${competitor_price}\n- Price Difference: ${price_difference:.2f}\n\nBased on this data, provide a pricing recommendation. Return a JSON with:\n- recommendation: One of "REDUCE_PRICE", "INCREASE_PRICE", or "MAINTAIN_PRICE"\n- confidence_score: 0.0 to 1.0\n- reasoning: Explanation for the recommendation\n\nConsider:\n1. Price competitiveness\n2. Market positioning\n3. Value proposition\n4. Profit margins\n5. Market demand signals\n\nRespond ONLY with valid JSON.\n')

def get_nexus_prompt() -> PromptTemplate:
    return PromptTemplate.from_template('\nYou are a market analyst AI specializing in competitive intelligence. Analyze the given product catalogs and market positioning.\n\nCompany Data:\n- Name: {company}\n- Products: {total_products}\n- Categories: {categories}\n- Price Range: ${min_price} - ${max_price}\n- Average Price: ${avg_price:.2f}\n\nCompetitor Data:\n- {competitor_name}: {competitor_products} products, avg price ${competitor_avg_price:.2f}\n\nMarket Context:\n- Top Features in Market: {top_features}\n- Market Trends: {market_trends}\n\nAnalyze and provide:\n1. Competitive Positioning: PREMIUM, VALUE, or BALANCED\n2. Market Position: Strategic positioning vs competitors\n3. Key Competitive Insights: 3-4 actionable insights\n4. Confidence Score: 0.0 to 1.0\n\nReturn ONLY valid JSON with structure:\n{{\n  "competitive_strength": "string",\n  "market_position": "string",\n  "key_insights": ["string"],\n  "confidence_score": number,\n  "reasoning": "string"\n}}\n')

def get_verse_prompt() -> PromptTemplate:
    return PromptTemplate.from_template('\nYou are a creative marketing copywriter AI. Generate compelling marketing content for the product below.\n\nProduct Information:\n- Name: {product_name}\n- Category: {category}\n- Price: ${price:.2f}\n- Features: {features}\n- Company: {company}\n\nCompetitive Context:\n- Top Competitor: {competitor_name}\n- Competitor Price: ${competitor_price:.2f}\n- Competitive Advantages: {advantages}\n- Target Audience: {target_audience}\n\nCreate engaging marketing content:\n1. Headline: Catchy, benefit-focused (max 10 words)\n2. Description: Compelling product description (2-3 sentences)\n3. Key Selling Points: Top 4 unique benefits\n4. Call to Action: Persuasive CTA\n5. Tone: Match the price tier - "casual_accessible" for budget, "professional" for mid-range, "premium_sophisticated" for premium\n\nReturn ONLY valid JSON with:\n{{\n  "headline": "string",\n  "description": "string",\n  "key_selling_points": ["string"],\n  "call_to_action": "string",\n  "tone": "string",\n  "confidence_score": number\n}}\n')

def create_pricing_chain(openrouter_api_key: str, model: str):
    llm = create_llm_beacon(openrouter_api_key, model)
    prompt = get_beacon_prompt()
    parser = JsonOutputParser(pydantic_object=PricingRecommendation)
    return prompt | llm | parser

def create_market_chain(openrouter_api_key: str, model: str):
    llm = create_llm_nexus(openrouter_api_key, model)
    prompt = get_nexus_prompt()
    parser = JsonOutputParser(pydantic_object=MarketPositioningAnalysis)
    return prompt | llm | parser

def create_content_chain(openrouter_api_key: str, model: str):
    llm = create_llm_verse(openrouter_api_key, model)
    prompt = get_verse_prompt()
    parser = JsonOutputParser(pydantic_object=MarketingContentOutput)
    return prompt | llm | parser
import asyncio
import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import gradio as gr
from config import load_config, validate_config
from system_integration import CompetitiveIntelligenceSystem
_config = load_config()
_config.enable_tracing = False
_config.timeout = 60
_system: Optional[CompetitiveIntelligenceSystem] = None
_init_error: Optional[str] = None

def _boot_system() -> CompetitiveIntelligenceSystem:
    global _system, _init_error
    if _system is not None:
        return _system
    try:
        system = CompetitiveIntelligenceSystem(_config)
        ok, errs = system.initialize()
        if not ok:
            _init_error = '; '.join(errs)
            raise RuntimeError(_init_error)
        _system = system
        return _system
    except Exception as exc:
        _init_error = str(exc)
        raise

def _fmt_product_table(products: list[dict]) -> str:
    if not products:
        return '*No results found.*'
    rows = ['| # | Product | Company | Category | Price |', '|---|---------|---------|----------|-------|']
    for i, p in enumerate(products, 1):
        name = p.get('product_name', p.get('label', '—'))
        company = p.get('company', '—')
        category = p.get('category', '—')
        price = p.get('effective_price', p.get('price', 0))
        rows.append(f'| {i} | {name} | {company} | {category} | ${price:.2f} |')
    return '\n'.join(rows)

def _fmt_competitor_table(competitors: list[dict]) -> str:
    if not competitors:
        return '*No competitors found for this product.*'
    rows = ['| Product | Company | Category | Price | Similarity |', '|---------|---------|----------|-------|------------|']
    for c in competitors:
        rows.append(f"| {c['product_name']} | {c['company']} | {c['category']} | ${c['price']:.2f} | {c['similarity']:.2f} |")
    return '\n'.join(rows)

def _fmt_feature_gaps(gaps: list[dict]) -> str:
    if not gaps:
        return '*No feature gaps found — full parity!*'
    rows = ['| Feature | Available From | # Competitors |', '|---------|---------------|---------------|']
    for g in gaps:
        owners = ', '.join(g['available_from'])
        rows.append(f"| {g['feature']} | {owners} | {g['competitor_count']} |")
    return '\n'.join(rows)

def get_dashboard():
    try:
        system = _boot_system()
        health = system.health_check()
        lines = ['## 🩺 System Health\n']
        status_icon = '🟢' if health.overall_healthy else '🔴'
        lines.append(f"**Overall**: {status_icon} {('Healthy' if health.overall_healthy else 'Unhealthy')}\n")
        lines.append('| Component | Status |')
        lines.append('|-----------|--------|')
        for comp, ok in health.components.items():
            icon = '✅' if ok else '❌'
            lines.append(f'| {comp} | {icon} |')
        if health.details:
            lines.append('\n### 📊 Details\n')
            for k, v in health.details.items():
                lines.append(f'- **{k}**: {v}')
        if health.errors:
            lines.append('\n### ⚠️ Errors\n')
            for e in health.errors:
                lines.append(f'- {e}')
        kg = system.knowledge_graph
        if kg:
            stats = kg.get_graph_stats()
            lines.append('\n## 🕸️ Knowledge Graph\n')
            lines.append(f"- **Nodes**: {stats['total_nodes']}  (Products: {stats['products']}, Features: {stats['features']}, Companies: {stats['companies']}, Categories: {stats['categories']})")
            lines.append(f"- **Edges**: {stats['total_edges']}  (Competition: {stats['competes_with_edges']}, Features: {stats['has_feature_edges']})")
        if kg:
            lines.append('\n## 📦 Category Overview\n')
            lines.append('| Category | Products | Avg Price | Min | Max |')
            lines.append('|----------|----------|-----------|-----|-----|')
            for cs in kg.get_category_stats():
                lines.append(f"| {cs['category']} | {cs['product_count']} | ${cs['avg_price']:.2f} | ${cs['min_price']:.2f} | ${cs['max_price']:.2f} |")
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ System Error**: {exc}'

def run_search(query: str, company: str, category: str, top_k: int):
    if not query.strip():
        return '⚠️ Please enter a search query.'
    try:
        system = _boot_system()
        comp = company if company != 'All' else None
        cat = category if category != 'All' else None
        if comp or cat:
            results = system.search_engine.search_with_filters(query, company=comp, category=cat, k=int(top_k))
        else:
            results = system.search_engine.semantic_search(query, k=int(top_k))
        if not results:
            return 'No results found.'
        lines = [f'### 🔍 Results for *"{query}"*\n']
        lines.append('| # | Product | Company | Category | Price | Similarity |')
        lines.append('|---|---------|---------|----------|-------|------------|')
        for i, r in enumerate(results, 1):
            sim = r.get('similarity_score', 0)
            lines.append(f"| {i} | {r['product_name']} | {r['company']} | {r['category']} | ${r['effective_price']:.2f} | {sim:.3f} |")
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def run_analysis(selected_product="All Products", progress=gr.Progress()):
    try:
        system = _boot_system()
        progress(0.1, desc='Initialising agents…')

        target_products = None
        if selected_product and selected_product != "All Products":
            sku = selected_product.split(' — ')[0].strip()
            target_products = [p for p in system.normalized_products if p.get('sku') == sku]
            if not target_products:
                return f"⚠️ Product `{sku}` not found in catalog."

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            progress(0.3, desc='Running Nexus → Beacon → Verse sequentially (rate-limited)…')
            report = loop.run_until_complete(system.analyze_competitors(products=target_products))
        finally:
            loop.close()
        progress(0.9, desc='Formatting report…')
        lines = [f'## 📊 Competitive Analysis Report\n']
        lines.append(f'- **Analysis ID**: `{report.analysis_id}`')
        lines.append(f'- **Timestamp**: {report.timestamp}')
        lines.append(f'- **Products Analyzed**: {report.products_analyzed}')
        lines.append(f'- **Confidence**: {report.confidence_score:.0%}')
        lines.append(f'- **Execution Time**: {report.execution_time_ms}ms')
        lines.append(f'- **Recommendation**: {report.overall_recommendation}\n')

        # ── Beacon: Pricing Recommendations ──
        ba = report.price_analysis
        lines.append('---')
        lines.append('### 💰 Beacon — Pricing Recommendations')
        lines.append(f"- **Status**: {ba.get('status', 'N/A')}  ·  **Execution**: {ba.get('execution_time', 0):.1f}s\n")
        beacon_data = ba.get('data')
        if beacon_data:
            lines.append('| Product | Current Price | Competitor Price | Diff | Recommendation | Confidence | Reasoning |')
            lines.append('|---------|:------------:|:---------------:|:----:|:--------------:|:----------:|-----------|')
            for a in beacon_data:
                comp_p = f'${a.competitor_price:.2f}' if a.competitor_price else '—'
                diff = f'${a.price_difference:+.2f}' if a.price_difference else '—'
                rec_icon = {'REDUCE_PRICE': '🔻 Reduce', 'INCREASE_PRICE': '🔺 Increase', 'MAINTAIN_PRICE': '⏸️ Maintain'}.get(a.recommendation, a.recommendation)
                lines.append(f'| {a.product_name} | ${a.current_price:.2f} | {comp_p} | {diff} | {rec_icon} | {a.confidence_score:.0%} | {a.reasoning} |')
        else:
            lines.append('*No pricing data available.*')

        # ── Nexus: Market Positioning ──
        fa = report.feature_analysis
        lines.append('\n---')
        lines.append('### 🔬 Nexus — Market Positioning')
        lines.append(f"- **Status**: {fa.get('status', 'N/A')}  ·  **Execution**: {fa.get('execution_time', 0):.1f}s\n")
        nexus_data = fa.get('data')
        if nexus_data:
            for company_name, analysis in nexus_data.items():
                strength = analysis.competitive_strength
                strength_icon = {'PREMIUM': '👑', 'VALUE': '💎', 'BALANCED': '⚖️'}.get(strength, '📊')
                lines.append(f'#### {strength_icon} {company_name}')
                lines.append(f'- **Products**: {analysis.total_products}  ·  **Categories**: {", ".join(analysis.categories)}')
                lines.append(f'- **Avg Price**: ${analysis.avg_price:.2f}  ·  **Range**: ${analysis.price_range.get("min", 0):.2f} – ${analysis.price_range.get("max", 0):.2f}')
                lines.append(f'- **Positioning**: {strength_icon} **{strength}**  ·  **Market Position**: {analysis.market_position}')
                lines.append(f'- **Confidence**: {analysis.confidence_score:.0%}')
                lines.append(f'- **Analysis**: {analysis.reasoning}\n')
        else:
            lines.append('*No market positioning data available.*')

        # ── Verse: Marketing Content ──
        mi = report.marketing_insights
        lines.append('---')
        lines.append('### ✍️ Verse — Marketing Content')
        lines.append(f"- **Status**: {mi.get('status', 'N/A')}  ·  **Execution**: {mi.get('execution_time', 0):.1f}s\n")
        verse_data = mi.get('data')
        if verse_data:
            for content in verse_data:
                tone_icon = {'casual_accessible': '😊', 'professional': '💼', 'premium_sophisticated': '✨'}.get(content.tone, '📝')
                lines.append(f'#### {tone_icon} {content.product_name} ({content.category})')
                lines.append(f'> **{content.headline}**\n')
                lines.append(f'{content.description}\n')
                lines.append(f'**Key Selling Points:**')
                for point in content.key_selling_points:
                    lines.append(f'- ✅ {point}')
                lines.append(f'\n*Tone: {content.tone} · Confidence: {content.confidence_score:.0%}*\n')
        else:
            lines.append('*No marketing content available.*')

        if report.errors:
            lines.append('\n---')
            lines.append('### ⚠️ Errors')
            for e in report.errors:
                lines.append(f'- {e}')
        out_dir = Path('outputs')
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f'analysis_{report.analysis_id}.json'
        report.save(str(path))
        lines.append(f'\n> 💾 Report saved to `{path}`')
        progress(1.0, desc='Done')
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Analysis Failed**: {exc}\n\n```\n{traceback.format_exc()}\n```'

def get_product_choices():
    try:
        system = _boot_system()
        return [f"{p.get('sku', '')} — {p.get('product_name', '')}" for p in system.normalized_products]
    except Exception:
        return []

def get_company_choices():
    try:
        system = _boot_system()
        return sorted(set((p.get('company', '') for p in system.normalized_products)))
    except Exception:
        return ['Company X', 'Company Y']

def get_category_choices():
    try:
        system = _boot_system()
        return sorted(set((p.get('category', '') for p in system.normalized_products)))
    except Exception:
        return []

def find_competitors_ui(product_choice: str):
    if not product_choice:
        return '⚠️ Select a product.'
    sku = product_choice.split(' — ')[0].strip()
    try:
        system = _boot_system()
        competitors = system.knowledge_graph.find_competitors(sku)
        lines = [f'### 🏁 Competitors for **{product_choice}**\n']
        lines.append(_fmt_competitor_table(competitors))
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def find_feature_gaps_ui(company: str):
    if not company:
        return '⚠️ Select a company.'
    try:
        system = _boot_system()
        gaps = system.knowledge_graph.find_feature_gaps(company)
        lines = [f'### 🔍 Feature Gaps for **{company}**\n']
        lines.append(f'*Features competitors have that {company} does not.*\n')
        lines.append(_fmt_feature_gaps(gaps))
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def find_similar_ui(product_choice: str):
    if not product_choice:
        return '⚠️ Select a product.'
    sku = product_choice.split(' — ')[0].strip()
    try:
        system = _boot_system()
        similar = system.knowledge_graph.find_similar_products(sku)
        lines = [f'### 🔗 Products Similar to **{product_choice}**\n']
        if not similar:
            lines.append('*No similar products found.*')
        else:
            lines.append('| Product | Company | Category | Price | Shared Features | Similarity |')
            lines.append('|---------|---------|----------|-------|-----------------|------------|')
            for s in similar[:10]:
                shared = ', '.join(s['shared_features'][:4])
                lines.append(f"| {s['product_name']} | {s['company']} | {s['category']} | ${s['price']:.2f} | {shared} | {s['similarity']:.2f} |")
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def feature_frequency_ui():
    try:
        system = _boot_system()
        freq = system.knowledge_graph.get_feature_frequency()
        lines = ['### 📈 Feature Frequency\n', '| Feature | Products Using |', '|---------|--------------|']
        for feat, count in freq:
            bar = '█' * count
            lines.append(f'| {feat} | {bar} {count} |')
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def visualize_graph_ui():
    try:
        system = _boot_system()
        path = system.knowledge_graph.visualize('./outputs/knowledge_graph_ui.html')
        return path
    except Exception as exc:
        return None

def explore_products():
    try:
        system = _boot_system()
        return _fmt_product_table(system.normalized_products)
    except Exception as exc:
        return f'**❌ Error**: {exc}'

def product_detail(product_choice: str):
    if not product_choice:
        return '⚠️ Select a product.'
    sku = product_choice.split(' — ')[0].strip()
    try:
        system = _boot_system()
        prod = None
        for p in system.normalized_products:
            if p.get('sku') == sku:
                prod = p
                break
        if not prod:
            return f'Product `{sku}` not found.'
        lines = [f"## {prod.get('product_name', sku)}\n"]
        lines.append(f"- **Company**: {prod.get('company', '—')}")
        lines.append(f"- **Category**: {prod.get('category', '—')}")
        lines.append(f"- **SKU**: `{prod.get('sku', '—')}`")
        lines.append(f"- **Base Price**: ${prod.get('base_price', 0):.2f}")
        lines.append(f"- **Discount**: {prod.get('discount_pct', 0)}% ({prod.get('discount_type', 'none')})")
        lines.append(f"- **Effective Price**: ${prod.get('effective_price', 0):.2f}")
        lines.append(f"- **Price/Feature**: ${prod.get('price_per_feature', 0):.2f}")
        lines.append(f"- **Availability**: {prod.get('availability', '—')}")
        features = prod.get('features', [])
        if features:
            lines.append(f'\n### Features ({len(features)})\n')
            for f in features:
                lines.append(f'- {f}')
        return '\n'.join(lines)
    except Exception as exc:
        return f'**❌ Error**: {exc}'
CSS = '\n/* ── Global ── */\n.gradio-container {\n    max-width: 1280px !important;\n    margin: auto !important;\n}\n#app-title {\n    text-align: center;\n    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n    -webkit-background-clip: text;\n    -webkit-text-fill-color: transparent;\n    font-size: 2.4rem !important;\n    font-weight: 800 !important;\n    letter-spacing: -0.5px;\n    margin-bottom: 0 !important;\n}\n#app-subtitle {\n    text-align: center;\n    opacity: 0.7;\n    font-size: 1rem !important;\n    margin-top: 0 !important;\n}\n/* ── Buttons ── */\n.primary-btn {\n    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;\n    border: none !important;\n    color: white !important;\n    font-weight: 600 !important;\n    transition: transform 0.15s, box-shadow 0.15s !important;\n}\n.primary-btn:hover {\n    transform: translateY(-1px) !important;\n    box-shadow: 0 4px 15px rgba(102,126,234,0.4) !important;\n}\n/* ── Cards ── */\n.stat-card {\n    border-radius: 12px !important;\n    padding: 16px !important;\n}\n'

def build_app() -> gr.Blocks:
    theme = gr.themes.Soft(primary_hue='indigo', secondary_hue='purple', neutral_hue='slate', font=gr.themes.GoogleFont('Inter'))
    with gr.Blocks(theme=theme, css=CSS, title='CompleteIQ — Competitive Intelligence') as app:
        gr.Markdown('# CompleteIQ', elem_id='app-title')
        gr.Markdown('Multi-Agent E-Commerce Competitive Intelligence System', elem_id='app-subtitle')
        with gr.Tabs():
            with gr.Tab('📊 Dashboard', id='dashboard'):
                refresh_btn = gr.Button('🔄  Refresh Dashboard', elem_classes=['primary-btn'])
                dashboard_out = gr.Markdown()
                refresh_btn.click(fn=get_dashboard, outputs=dashboard_out)
                app.load(fn=get_dashboard, outputs=dashboard_out)
            with gr.Tab('🔍 Semantic Search', id='search'):
                gr.Markdown('### Search products by natural language query')
                with gr.Row():
                    search_query = gr.Textbox(label='Search Query', placeholder='e.g. noise cancelling headphones with long battery', scale=3)
                    search_company = gr.Dropdown(choices=['All', 'Company X', 'Company Y'], value='All', label='Company', scale=1)
                    search_category = gr.Dropdown(choices=['All', 'Wireless Headphones', 'Smart Watches', 'Portable Speakers'], value='All', label='Category', scale=1)
                    search_k = gr.Slider(1, 12, value=5, step=1, label='Top K', scale=1)
                search_btn = gr.Button('🔍  Search', elem_classes=['primary-btn'])
                search_out = gr.Markdown()
                search_btn.click(fn=run_search, inputs=[search_query, search_company, search_category, search_k], outputs=search_out)
            with gr.Tab('⚔️ Competitive Analysis', id='analysis'):
                gr.Markdown('### Run multi-agent competitive analysis\nSelect an individual product to analyze (fast, uses 3 API calls) or analyze the entire catalog (uses 26 API calls).')
                analysis_product = gr.Dropdown(choices=['All Products'] + get_product_choices(), value='All Products', label='Select Product to Analyze')
                analysis_btn = gr.Button('🚀  Run Analysis', elem_classes=['primary-btn'])
                analysis_out = gr.Markdown()
                analysis_btn.click(fn=run_analysis, inputs=analysis_product, outputs=analysis_out)
            with gr.Tab('🕸️ Knowledge Graph', id='kg'):
                with gr.Tabs():
                    with gr.Tab('Competitors'):
                        gr.Markdown('### Find direct competitors for a product')
                        comp_product = gr.Dropdown(choices=get_product_choices(), label='Select Product')
                        comp_btn = gr.Button('🏁  Find Competitors', elem_classes=['primary-btn'])
                        comp_out = gr.Markdown()
                        comp_btn.click(fn=find_competitors_ui, inputs=comp_product, outputs=comp_out)
                    with gr.Tab('Feature Gaps'):
                        gr.Markdown("### Discover features your competitors have that you don't")
                        gap_company = gr.Dropdown(choices=get_company_choices(), label='Select Company')
                        gap_btn = gr.Button('🔍  Find Gaps', elem_classes=['primary-btn'])
                        gap_out = gr.Markdown()
                        gap_btn.click(fn=find_feature_gaps_ui, inputs=gap_company, outputs=gap_out)
                    with gr.Tab('Similar Products'):
                        gr.Markdown('### Products with the highest feature overlap')
                        sim_product = gr.Dropdown(choices=get_product_choices(), label='Select Product')
                        sim_btn = gr.Button('🔗  Find Similar', elem_classes=['primary-btn'])
                        sim_out = gr.Markdown()
                        sim_btn.click(fn=find_similar_ui, inputs=sim_product, outputs=sim_out)
                    with gr.Tab('Feature Frequency'):
                        gr.Markdown('### Most common features across all products')
                        freq_btn = gr.Button('📈  Show Frequency', elem_classes=['primary-btn'])
                        freq_out = gr.Markdown()
                        freq_btn.click(fn=feature_frequency_ui, outputs=freq_out)
                    with gr.Tab('Interactive Graph'):
                        gr.Markdown('### Interactive Knowledge Graph Visualization')
                        gr.Markdown('*Click **Generate Graph** to build an interactive network visualization of all products, features, companies, and competitive relationships.*')
                        viz_btn = gr.Button('🗺️  Generate Graph', elem_classes=['primary-btn'])
                        viz_html = gr.HTML()

                        def _render_graph():
                            try:
                                path = visualize_graph_ui()
                                if path and os.path.exists(path):
                                    import html
                                    with open(path, 'r', encoding='utf-8') as f:
                                        raw_html = f.read()
                                    escaped_html = html.escape(raw_html)
                                    return f'<iframe srcdoc="{escaped_html}" width="100%" height="750" style="border:1px solid #444;border-radius:12px;" sandbox="allow-scripts allow-same-origin"></iframe>'
                                return "<p style='color:#f66;'>⚠️ Graph generation failed.</p>"
                            except Exception as e:
                                return f"<p style='color:#f66;'>❌ Error: {e}</p>"
                        viz_btn.click(fn=_render_graph, outputs=viz_html)
            with gr.Tab('📦 Products', id='products'):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown('### Product Catalog')
                        explore_btn = gr.Button('📋  Load All Products', elem_classes=['primary-btn'])
                        catalog_out = gr.Markdown()
                        explore_btn.click(fn=explore_products, outputs=catalog_out)
                    with gr.Column(scale=1):
                        gr.Markdown('### Product Details')
                        detail_product = gr.Dropdown(choices=get_product_choices(), label='Select Product')
                        detail_btn = gr.Button('🔎  View Details', elem_classes=['primary-btn'])
                        detail_out = gr.Markdown()
                        detail_btn.click(fn=product_detail, inputs=detail_product, outputs=detail_out)
        gr.Markdown(f"<center style='opacity:0.5; margin-top:20px;'>CompleteIQ v1.0 · Multi-Agent Competitive Intelligence · Built with Gradio {gr.__version__}</center>")
    return app
if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('COMPLETEIQ — STARTING UI')
    print('=' * 60)
    print('[INFO] Pre-loading system…')
    try:
        _boot_system()
        print('[INFO] System ready')
    except Exception as e:
        print(f'[WARN] System pre-load failed: {e}')
        print('[INFO] System will retry on first request')
    app = build_app()
    app.launch(server_name='0.0.0.0', server_port=7860, share=False, show_error=True)
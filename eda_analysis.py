import os
import sys
import json
import re
import uuid
import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
import base64
from langfuse import Langfuse
from openai import OpenAI
DATASET_REPO = "https://github.com/AI-Project-Lab/IK-pwc-agenticai-datasets.git"
DATASET_PROJECT = "ecommerce"
def load_environment() -> Path:
    load_dotenv()
    datasets_dir = Path("./datasets")
    if not (datasets_dir / DATASET_PROJECT).exists():
        print(f"Cloning dataset from {DATASET_REPO}...")
        try:
            datasets_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", DATASET_REPO, str(datasets_dir / DATASET_PROJECT)],
                           check=True, capture_output=True)
            print("Dataset cloned successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone dataset: {e.stderr.decode()}")
            create_mock_data(datasets_dir / DATASET_PROJECT)
    else:
        print("Dataset already available locally.")
    required_vars = [
        "OPENAI_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"[WARN] Missing API keys: {missing}. OpenAI/Langfuse tracing will fail.")
    if not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = "https://jp.cloud.langfuse.com"
    data_dir = datasets_dir / DATASET_PROJECT
    return data_dir
def create_mock_data(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    company_x = [
        {"company_name": "Company X", "category": "Wireless Headphones", "product_name": "Headphones X1", "base_price": 99.99, "discount": "10% off"},
        {"company_name": "Company X", "category": "Smart Watches", "product_name": "Watch X1", "base_price": 199.99, "discount": "15% off"}
    ]
    company_y = [
        {"company_name": "Company Y", "category": "Wireless Headphones", "product_name": "Headphones Z1", "base_price": 105.00, "discount": "5% off"},
        {"company_name": "Company Y", "category": "Smart Watches", "product_name": "Watch Z1", "base_price": 189.99, "discount": "20% off"}
    ]
    with open(path / "company_x.json", "w") as f: json.dump(company_x, f)
    with open(path / "company_y.json", "w") as f: json.dump(company_y, f)
    print("Mock data created as fallback.")
def init_observability() -> tuple[Langfuse, OpenAI, str]:
    lf = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST"),
    )
    session_id = f"ecommerce-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return lf, client, session_id
def traced_completion(
    prompt: str,
    system: str,
    lf: Langfuse,
    client: OpenAI,
    session_id: str
) -> str:
    trace = lf.trace(name="completion", session_id=session_id)
    generation = trace.generation(
        name="gpt-4o-mini",
        model="gpt-4o-mini",
        input=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        output = response.choices[0].message.content
        generation.end(
            output=output,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )
    except Exception as e:
        generation.end(status_message=str(e))
        raise
    finally:
        trace.end()
    return output
def traced_embedding(
    text: str,
    lf: Langfuse,
    client: OpenAI,
    session_id: str
) -> List[float]:
    trace = lf.trace(name="embedding", session_id=session_id)
    span = trace.span(name="text-embedding-3-small", input=text)
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        vector = response.data[0].embedding
        span.end(output="Vector generated", metadata={"usage": response.usage.total_tokens})
    except Exception as e:
        span.end(status_message=str(e))
        raise
    finally:
        trace.end()
    return vector
def parse_discount(discount_str: Optional[str]) -> float:
    if not discount_str or not isinstance(discount_str, str):
        return 0.0
    match = re.search(r'(\d+)%', discount_str)
    return float(match.group(1)) if match else 0.0
def load_and_normalize(data_dir: Path) -> pd.DataFrame:
    eda_data = []
    for filename in ["company_x.json", "company_y.json"]:
        file_path = data_dir / filename
        if not file_path.exists():
            continue
        with open(file_path, 'r') as f:
            catalog = json.load(f)
        products = catalog if isinstance(catalog, list) else catalog.get('products', [])
        company_name_from_catalog = catalog.get('company', "Company X" if "company_x" in filename else "Company Y")
        for p in products:
            try:
                base_price = float(p.get('base_price', p.get('price', 0)))
                discount_raw = p.get('discount', '0%')
                discount_pct = parse_discount(str(discount_raw))
                effective_price = base_price * (1 - discount_pct / 100)
                eda_data.append({
                    "company_name": company_name_from_catalog,
                    "category": p.get('category', 'Unknown'),
                    "product_name": p.get('product_name', 'Unknown'),
                    "base_price": base_price,
                    "discount_percentage": discount_pct,
                    "effective_price": effective_price,
                    "feature_count": len(p.get('features', []))
                })
            except Exception:
                continue
    return pd.DataFrame(eda_data)
def create_dashboard(df: pd.DataFrame):
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = {'Company X': '#3498db', 'Company Y': '#e74c3c'}
    sns.kdeplot(data=df, x="effective_price", hue="company_name", palette=colors, fill=True, ax=axes[0, 0])
    axes[0, 0].set_title("Price Distributions (Effective Price)")
    sns.boxplot(data=df, x="company_name", y="discount_percentage", palette=colors, ax=axes[0, 1])
    axes[0, 1].set_title("Discount Strategies (% Off)")
    avg_features = df.groupby('company_name')['feature_count'].mean().reset_index()
    sns.barplot(data=avg_features, x="company_name", y="feature_count", palette=colors, ax=axes[1, 0])
    axes[1, 0].set_title("Average Feature Counts")
    sns.scatterplot(data=df, x="effective_price", y="feature_count", hue="company_name", palette=colors, ax=axes[1, 1])
    axes[1, 1].set_title("Feature Count vs. Price")
    plt.tight_layout()
    plt.savefig('ecommerce_eda.png', dpi=150, bbox_inches='tight')
    return fig
def log_image_to_langfuse(image_path: Path, lf: Langfuse, trace: Any) -> None:
    try:
        with image_path.open("rb") as f:
            image_bytes = f.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_image}"
        trace.span(
            name="eda_results",
            output={"dashboard": data_uri},
            metadata={"product_count": 12}
        )
        print("Logged dashboard to Langfuse.")
    except Exception as exc:
        print(f"[WARN] Failed to upload dashboard image to Langfuse: {exc}")
def main():
    print("Starting CompeteIQ Week 1 Pipeline...")
    data_dir = load_environment()
    try:
        lf, client, session_id = init_observability()
        print(f"Session ID: {session_id}")
    except Exception as e:
        print(f"[WARN] Observability initialization failed: {e}")
        lf, client, session_id = None, None, "local-session"
    df = load_and_normalize(data_dir)
    print(f"Loaded {len(df)} products.")
    create_dashboard(df)
    if lf:
        trace = lf.trace(name="week_1_eda_summary", session_id=session_id)
        log_image_to_langfuse(Path("ecommerce_eda.png"), lf, trace)
        lf.flush()
    else:
        print("[INFO] Skipping Langfuse logging (no client initialized).")
if __name__ == "__main__":
    main()
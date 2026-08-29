

import sys
import os
import pandas as pd
from sentence_transformers import SentenceTransformer

# Add project root to path so app.* imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal  # ✅ sync session
from app.db.models import KnowledgeChunk
from sqlalchemy import text

print("Loading embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Model loaded.\n")


def get_embedding(text_input: str) -> list:
    return model.encode(text_input).tolist()


def ingest_data():
    # Find the Excel file in project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    possible_names = [
        "MoinSystems_AI_Public_Chatbot_RAG_Dataset_v2__1_.xlsx",
        "MoinSystems_AI_Public_Chatbot_RAG_Dataset_v2 (1).xlsx",
        "MoinSystems_AI_Public_Chatbot_RAG_Dataset_v2.xlsx",
    ]

    file_path = None
    for name in possible_names:
        candidate = os.path.join(project_root, name)
        if os.path.exists(candidate):
            file_path = candidate
            break

    if not file_path:
        print("❌ ERROR: Excel file not found in project root.")
        print("   Place the RAG dataset Excel file in your project root folder.")
        sys.exit(1)

    print(f"📖 Reading dataset from: {file_path}")
    df = pd.read_excel(file_path, sheet_name="RAG_Knowledge")
    df = df.fillna("")

    validated = df[df["Data Status"] == "cleaned_validated"].copy()
    print(f"✅ Found {len(validated)} validated chunks.\n")

    db = SessionLocal()
    try:
        # Clear existing chunks
        existing = db.execute(text("SELECT COUNT(*) FROM knowledge_chunk")).scalar()
        if existing > 0:
            print(f"⚠️  Clearing {existing} existing chunks...")
            db.execute(text("DELETE FROM knowledge_chunk"))
            db.commit()
            print("✅ Table cleared.\n")

        success = 0
        failed = 0
        total = len(validated)

        for _, row in validated.iterrows():
            chunk_id = str(row["ID"]).strip()
            content = str(row["Content"]).strip()
            embedding_text = str(row["Embedding Text"]).strip() or content
            category = str(row["Category"]).strip()
            tags = str(row["Tags"]).strip()

            if not content:
                print(f"  ⚠️  Skipping {chunk_id} — empty content")
                continue

            try:
                print(f"  🔄 [{success + failed + 1}/{total}] Embedding {chunk_id}...")
                embedding = get_embedding(embedding_text)

                chunk = KnowledgeChunk(
                    id=chunk_id,
                    category=category,
                    content=content,
                    tags=tags,
                    embedding=embedding,
                )
                db.merge(chunk)
                db.commit()
                success += 1

            except Exception as e:
                db.rollback()
                failed += 1
                print(f"  ❌ FAILED {chunk_id}: {e}")

        print(f"\n{'='*50}")
        print(f"✅ Ingestion complete!")
        print(f"   Inserted/Updated : {success}")
        print(f"   Failed           : {failed}")
        print(f"{'='*50}")

        total_in_db = db.execute(text("SELECT COUNT(*) FROM knowledge_chunk")).scalar()
        print(f"\n📊 Total chunks in DB: {total_in_db}")

    finally:
        db.close()


if __name__ == "__main__":
    ingest_data()
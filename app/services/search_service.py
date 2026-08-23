import os
import logging
from sqlalchemy import select
from sentence_transformers import SentenceTransformer

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from app.db.session import SessionLocal
from app.db.models import KnowledgeChunk

logger = logging.getLogger(__name__)

print("Loading local embedding model for search engine...")
model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)

class SearchService:
    @staticmethod
    def get_embedding(text: str) -> list[float]:
        return model.encode(text).tolist()

    @staticmethod
    def search(query: str, limit: int = 4) -> list[dict]:
        query_embedding = SearchService.get_embedding(query)

        # Synchronous database connection
        with SessionLocal() as db:
            stmt = (
                select(KnowledgeChunk)
                .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
            )

            result = db.execute(stmt)
            chunks = result.scalars().all()

            formatted_results = []
            for chunk in chunks:
                formatted_results.append({
                    "id": chunk.id,
                    "category": chunk.category,
                    "content": chunk.content,
                    "tags": chunk.tags
                })

            return formatted_results
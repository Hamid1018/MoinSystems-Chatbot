import sys
import os
import asyncio
import pandas as pd
from sentence_transformers import SentenceTransformer

# Add the root directory to the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.models import KnowledgeDocument, KnowledgeChunk

# Load the local open-source embedding model
print("Loading local embedding model (this may take a moment to download the first time)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list[float]:
    """Uses the local model to vectorize text."""
    # encode() returns a numpy array, we convert it to a standard python list
    return model.encode(text).tolist()

async def ingest_data(file_path: str, dataset_version: str = "v2"):
    print(f"Loading knowledge dataset from {file_path}...")
    
    df = pd.read_excel(file_path, sheet_name="RAG_Knowledge")
    df = df.fillna("") 
    
    async with AsyncSessionLocal() as db:
        doc = KnowledgeDocument(
            id=f"moin_dataset_{dataset_version}",
            source_name="MoinSystems RAG Excel",
            version=dataset_version,
        )
        await db.merge(doc)
        
        for index, row in df.iterrows():
            content = row["Content"]
            if not content:
                continue
            
            chunk_id = str(row["ID"])
            print(f"Generating embedding for {chunk_id}: {row['Title']}")
            
            # Generate local vector
            embedding = get_embedding(content)
            
            tags = [t.strip() for t in str(row["Tags"]).split(",")] if row["Tags"] else []
            intents = [i.strip() for i in str(row["Intents"]).split(",")] if row["Intents"] else []
            
            chunk = KnowledgeChunk(
                id=chunk_id,
                document_id=doc.id,
                content=content,
                embedding=embedding,
                category=str(row["Category"]),
                tags=tags,
                intents=intents
            )
            
            await db.merge(chunk)
            
        await db.commit()
        print("\n✅ Successfully indexed all knowledge chunks into pgvector using the local model!")

if __name__ == "__main__":
    excel_file = "MoinSystems_AI_Public_Chatbot_RAG_Dataset_v2 (1).xlsx"
    
    if not os.path.exists(excel_file):
        print(f"Error: Could not find '{excel_file}'.")
    else:
        asyncio.run(ingest_data(excel_file))
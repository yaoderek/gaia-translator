import chromadb


def get_chroma_client(persist_dir: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=persist_dir)


def get_or_create_collection(
    client: chromadb.PersistentClient,
    name: str = "gaia_papers",
) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

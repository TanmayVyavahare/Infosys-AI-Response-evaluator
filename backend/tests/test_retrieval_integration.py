"""Exercise real MiniLM embeddings, FAISS search, and the disk-cache path.

These tests intentionally require the actual model, not a mocked embedding.
They run in the Linux CI job as well as any supported local ML environment.
"""
from app.config.settings import Settings
from app.retrieval.retriever import FAISSRetriever
from app.retrieval.embedder import Embedder


def test_real_retrieval_and_disk_cache(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, data_dir=tmp_path, retrieval_score_threshold=0)
    monkeypatch.setattr('app.retrieval.retriever.get_settings', lambda: settings)
    text = 'The Willow Museum opens at nine in the morning and closes at five in the afternoon. Admission costs twelve credits.'
    first = FAISSRetriever()
    results = first.retrieve_from_text('What time does the museum open?', text)
    assert results and 'nine' in results[0]['text']
    assert -1 <= results[0]['score'] <= 1.00001
    assert list(settings.faiss_cache_dir.glob('*.index'))

    cached = FAISSRetriever()
    # A cache hit must not re-embed the document (query embeddings still run).
    monkeypatch.setattr(cached.embedder, 'embed_batch', lambda _: (_ for _ in ()).throw(AssertionError('Cache was not used')))
    assert cached.retrieve_from_text('When does it close?', text)[0]['text'] == results[0]['text']


def test_semantic_paraphrase_beats_unrelated_text():
    embedder = Embedder()
    original = 'Customers can contact support by email.'
    paraphrase = 'Users can send an email to get help.'
    unrelated = 'Volcanoes erupt when molten rock reaches the surface.'
    assert embedder.semantic_similarity(original, paraphrase) > embedder.semantic_similarity(original, unrelated)

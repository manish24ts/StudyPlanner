from app.agents.learning_resources import search_learning_articles
from app.agents.resource_quiz import fallback_resources_for_subtopic


def test_fallback_resources_return_links_when_external_search_fails():
    youtube, blogs = fallback_resources_for_subtopic("DSA", "Core concepts")

    assert youtube is not None
    assert youtube.startswith("https://")
    assert blogs
    assert all(link["url"].startswith("https://") for link in blogs)


def test_search_learning_articles_returns_empty_when_ddgs_unavailable(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ddgs":
            raise ImportError("ddgs unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert search_learning_articles("DSA", "Core concepts", max_results=3) == []

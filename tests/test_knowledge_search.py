import os
import pytest

from models.knowledge_search import Chunk, tokenize, chunk_file, score_query, read_files, knowledge_search

def test_tokenize():
    q = "Hi!! Return-policy, ID=123? ok."
    assert tokenize(q) == ["return", "policy", "123"]


def test_chunk_files_no_main_heading():
    content = """
    ## Section One
    Hello there
    """
    chunks = chunk_file("shipping_and_orders.md", content)

    assert len(chunks) == 1
    assert chunks[0].title == "shipping_and_orders"   
    assert chunks[0].section == "Section One"
    assert "Hello there" in chunks[0].content

def test_chunk_files_with_main_heading():
    content = """
    # Oster Return Policy

    ## Standard Return Policy
    Returns within 30 days.

    ## Refund Method
    Refunds go to original payment method.
    """
    chunks = chunk_file("return_policy.md", content)

    assert len(chunks) == 2
    assert chunks[0].title == "Oster Return Policy"
    assert chunks[0].section == "Standard Return Policy"
    assert "30 days" in chunks[0].content

    assert chunks[1].section == "Refund Method"
    assert "original payment method" in chunks[1].content

def test_chunk_files_ignore_before_first_section():
    # Anything before the first ## should not become a chunk
    content = """
    # Title
    Intro line that is outside a section.

    ## Section A
    Inside A
    """
    chunks = chunk_file("x.md", content)

    assert len(chunks) == 1
    assert chunks[0].section == "Section A"
    assert "Inside A" in chunks[0].content
    assert "Intro line" not in chunks[0].content


def test_score_query():
    c = Chunk(
        filename="a.md",
        title="A",
        section="Return Policy",
        content="Return within 30 days. Return items must be unused.",
    )

    terms = ["return", "policy", "days"]
    # "return" appears 3 times total? Let's count:
    # section: "Return Policy" -> return(1) policy(1)
    # content: "Return within 30 days. Return items must be unused."
    # return(2) days(1)
    # Total: return(3), policy(1), days(1) => 5
    assert score_query(terms, c) == 5


def test_read_files(tmp_path):
    folder = tmp_path / "knowledge"
    folder.mkdir()

    (folder / "a.md").write_text("# A\n\n## S\nhello", encoding="utf-8")
    (folder / "b.MD").write_text("# B\n\n## S\nworld", encoding="utf-8")
    (folder / "not_md.txt").write_text("ignore me", encoding="utf-8")

    files = read_files(str(folder))
    names = sorted([name for name, _ in files])

    assert names == ["a.md", "b.MD"]


def test_knowledge_search_returns_ranked_matches_and_respects_top_k(tmp_path):
    folder = tmp_path / "knowledge"
    folder.mkdir()

    # This one should rank higher for "return"
    (folder / "return_policy.md").write_text(
        "# Return Policy\n\n## Standard\nReturn return return.\n",
        encoding="utf-8",
    )

    (folder / "shipping.md").write_text(
        "# Shipping\n\n## Speed\nFast shipping.\n",
        encoding="utf-8",
    )

    res = knowledge_search("return policy", top_k=1, folder=str(folder))

    assert res["query"] == "return policy"
    assert res["top_k"] == 1
    assert len(res["matches"]) == 1
    assert res["matches"][0]["source"] == "return_policy.md"


def test_knowledge_search_truncates_long_content_to_700_chars(tmp_path):
    folder = tmp_path / "knowledge"
    folder.mkdir()

    long_text = "A" * 800
    (folder / "long.md").write_text(
        "# Long\n\n## Section\n" + long_text,
        encoding="utf-8",
    )

    res = knowledge_search("Section", top_k=3, folder=str(folder))
    assert len(res["matches"]) == 1

    content = res["matches"][0]["content"]
    assert len(content) <= 703  # 700 + "..."
    assert content.endswith("...")


def test_knowledge_search_returns_empty_matches_when_no_hits(tmp_path):
    folder = tmp_path / "knowledge"
    folder.mkdir()

    (folder / "a.md").write_text("# A\n\n## S\nhello world", encoding="utf-8")

    res = knowledge_search("nonexistentterm", folder=str(folder))
    assert res["matches"] == []
"""Tests for PatchEngine, Search/Replace blocks, fuzzy replacement, and syntax safety."""

from src.editor.patch_engine import PatchBlock, PatchEngine


def test_parse_search_replace_blocks() -> None:
    """Verifies parsing of standard Search/Replace blocks."""
    llm_output = """Here is the suggested modification:
<<<<<<< SEARCH
def old_function():
    return 1
=======
def old_function():
    return 2
>>>>>>> REPLACE
Done!"""

    blocks = PatchEngine.parse_search_replace_blocks(llm_output)
    assert len(blocks) == 1
    assert "return 1" in blocks[0].search_block
    assert "return 2" in blocks[0].replace_block


def test_apply_patch_exact_match() -> None:
    """Verifies clean application of an exact match."""
    original = "x = 10\ny = 20\n"
    block = PatchBlock(search_block="x = 10", replace_block="x = 100")
    res = PatchEngine.apply_search_replace_blocks(original, [block], "test.py")

    assert res.success
    assert "-x = 10" in res.diff
    assert "+x = 100" in res.diff


def test_apply_patch_fuzzy_whitespace() -> None:
    """Verifies fuzzy matching handles whitespace variations."""
    original = "    def test():\n        return True\n"
    # Search block has different leading whitespace
    block = PatchBlock(search_block="def test():\nreturn True", replace_block="def test():\n        return False")
    res = PatchEngine.apply_search_replace_blocks(original, [block], "test.py")

    assert res.success


def test_syntax_validation_rejects_bad_code() -> None:
    """Verifies that syntax errors are trapped before writing to disk."""
    original = "def foo():\n    return 42\n"
    bad_block = PatchBlock(search_block="return 42", replace_block="return (42")
    res = PatchEngine.apply_search_replace_blocks(original, [bad_block], "foo.py")

    assert not res.success
    assert "SyntaxError" in (res.error_message or "")

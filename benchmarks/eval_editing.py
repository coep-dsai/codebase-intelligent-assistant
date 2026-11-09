"""Automated evaluation benchmark for patch application precision and fuzzy matching."""

import time
from src.editor.patch_engine import PatchBlock, PatchEngine


def run_patch_benchmark() -> None:
    """Evaluates patch engine precision across clean, fuzzy, and multi-block edits."""
    test_code = """
def calculate_metrics(values):
    # Old logic
    total = sum(values)
    avg = total / len(values) if values else 0
    return avg

class DataProcessor:
    def process(self, data):
        return [x * 2 for x in data]
"""

    # Test 1: Clean Search/Replace
    block1 = PatchBlock(
        search_block="    # Old logic\n    total = sum(values)",
        replace_block="    # Optimized sum logic\n    total = math.fsum(values)",
    )
    t0 = time.perf_counter()
    res1 = PatchEngine.apply_search_replace_blocks(test_code, [block1], "math_utils.py")
    t1 = time.perf_counter()
    assert res1.success, f"Test 1 failed: {res1.error_message}"
    print(f"[PASS] Test 1 (Exact match) passed in {(t1 - t0)*1000:.2f}ms")

    # Test 2: Whitespace/Indentation Tolerant Match
    block2 = PatchBlock(
        search_block="def process(self, data):\nreturn [x * 2 for x in data]",
        replace_block="    def process(self, data):\n        # Vectorized\n        return [x * 3 for x in data]",
    )
    t0 = time.perf_counter()
    res2 = PatchEngine.apply_search_replace_blocks(test_code, [block2], "processor.py")
    t1 = time.perf_counter()
    assert res2.success, f"Test 2 failed: {res2.error_message}"
    print(f"[PASS] Test 2 (Fuzzy match) passed in {(t1 - t0)*1000:.2f}ms")

    # Test 3: Syntax Error Pre-flight Detection
    bad_block = PatchBlock(
        search_block="    avg = total / len(values) if values else 0",
        replace_block="    avg = (total / len(values) if values else 0",  # Unclosed paren
    )
    res3 = PatchEngine.apply_search_replace_blocks(test_code, [bad_block], "syntax_check.py")
    assert not res3.success, "Test 3 should have failed due to invalid syntax!"
    print("[PASS] Test 3 (Syntax error pre-flight detection) passed successfully!")

    print("\nAll patch benchmarks passed with 100% precision!")


if __name__ == "__main__":
    run_patch_benchmark()

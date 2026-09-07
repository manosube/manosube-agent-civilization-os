"""The one bounded-block replacement primitive every generated-block writer in this
repository shares (Issue #57, ``GENERATED_BLOCK_AUTOWRITE`` boundary).

Extracted from ``generate_readme_status_block.py`` (Issue #54) rather than duplicated: that
script's own ``apply()`` now delegates here, and ``merge_source_reflow.py``'s ``HANDOFF.md``
writer uses the identical primitive for a different marker pair. One algorithm, one proof
(``test_a_malformed_marker_pair_is_refused`` and friends), reused everywhere a file carries
exactly one machine-owned block inside otherwise Human-authored text.

Refuses (``SystemExit``) rather than silently appending or guessing when the two markers are
missing, duplicated, or out of order -- an unbounded write is not a smaller version of a
bounded one.
"""

from __future__ import annotations


def apply_bounded_block(original_text: str, block: str, begin_marker: str, end_marker: str) -> str:
    """Return *original_text* with the byte range from *begin_marker* through *end_marker*
    (inclusive) replaced by *block*. Every other byte is preserved exactly.

    *block* is expected to itself start with *begin_marker* and end with *end_marker* --
    this function does not add them.
    """

    begin_count = original_text.count(begin_marker)
    end_count = original_text.count(end_marker)
    if begin_count != 1 or end_count != 1:
        raise SystemExit(
            f"text must contain exactly one {begin_marker!r} and one {end_marker!r} "
            f"marker; found {begin_count} and {end_count}"
        )
    begin_index = original_text.index(begin_marker)
    end_index = original_text.index(end_marker) + len(end_marker)
    if end_index <= begin_index:
        raise SystemExit("the END marker must appear after the BEGIN marker")
    return original_text[:begin_index] + block + original_text[end_index:]


def human_text_outside_block(text: str, begin_marker: str, end_marker: str) -> str:
    """Return every byte of *text* outside the bounded block -- the exact substring a
    caller must prove is unchanged before and after a regeneration (Issue #57's
    ``HUMAN_TEXT_HASH_BEFORE=HUMAN_TEXT_HASH_AFTER`` requirement).

    Raises the same way :func:`apply_bounded_block` does when the markers are not exactly
    one well-ordered pair -- there is no "outside the block" to name otherwise.
    """

    begin_count = text.count(begin_marker)
    end_count = text.count(end_marker)
    if begin_count != 1 or end_count != 1:
        raise SystemExit(
            f"text must contain exactly one {begin_marker!r} and one {end_marker!r} "
            f"marker; found {begin_count} and {end_count}"
        )
    begin_index = text.index(begin_marker)
    end_index = text.index(end_marker) + len(end_marker)
    if end_index <= begin_index:
        raise SystemExit("the END marker must appear after the BEGIN marker")
    return text[:begin_index] + text[end_index:]

"""Vietnamese PII scrubbing for livestream comments.

HARD RULE (plan §1.4, description §11.3): this filter runs inside the ingest
process, BEFORE any write. The raw comment text never touches disk. Only the
scrubbed text is persisted.
"""

from livelift.ingest.pii.filter import PIIMatch, ScrubResult, scrub

__all__ = ["PIIMatch", "ScrubResult", "scrub"]

# Round-Trip Results

The deterministic diff and checkpoint machinery is implemented and covered by
synthetic tests. No real Unity round-trip result is claimed yet. Required cases
are no-op, controlled identity/value mutations, cleanup, reimport, and
save/reopen, with mismatch states preserved instead of hidden.

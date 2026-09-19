# Worker State Machine

```text
BOOT -> VALIDATE_TEMPLATE -> LOAD_REQUEST -> VALIDATE_REQUEST
-> IMPORT_PACKAGE -> WAIT_FOR_IMPORT -> WAIT_FOR_STABLE
-> PROBE -> WRITE_IMMUTABLE_RESULT -> FINAL_VERIFY -> COMPLETE
```

Domain reload recovery uses the external request/checkpoint as authority and
re-registers public callbacks. If import ownership, callback completeness,
template identity, or quiescence is uncertain, the worker writes `CRASHED` or
`FAILED` evidence and stops. It does not issue a second import in that
workspace.

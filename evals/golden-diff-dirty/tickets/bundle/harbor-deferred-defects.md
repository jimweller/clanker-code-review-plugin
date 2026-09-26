# Low-severity defects in harbor

Paths and line numbers refer to commit `7a9f10e84d875d9fa1433eb401e8efe6f077f5e4`.

The file lists 1 defects, sorted by the first file each one touches.

## 1. No tests for encrypt/decrypt round trip and tamper detection in crypto.ts

Categories are testing.

- `src/crypto.ts:10` `decrypt` No tests cover `encrypt` and `decrypt`, including the round trip and tamper detection.

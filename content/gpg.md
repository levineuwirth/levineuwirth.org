---
title: GPG Key
description: >-
  Public key, key ID, fingerprint, and verification steps for
  ln@levineuwirth.org.
history:
  - date: "2026-03-25"
  - date: "2026-03-17"

---

Public key for [ln@levineuwirth.org](mailto:ln@levineuwirth.org).

**Key ID:** `B01A01AD1B5C9663`

**Fingerprint:**
```
CD90 AE96 383B BAF4 15A1  D740 B01A 01AD 1B5C 9663
```

Download: [pubkey.asc](/gpg/pubkey.asc)

## Verification

```bash
curl -s https://levineuwirth.org/gpg/pubkey.asc | gpg --import
gpg --fingerprint ln@levineuwirth.org
```

# Contribution statement — G14

Signed by every member of the group. Contributions below are the substantive
ones: each maps to commits (short hash), to files in the repository, to a
recorded checkpoint, or, for the final review, to review notes held by the
member, so a reader can verify it with git log or by asking for the notes
rather than taking it on trust.

| Member | Student ID | Contribution | Evidence |
|---|---|---|---|
| Jiale Zhang | 2023304368 | Session 2: L1 forward model, correction factor and mobility, reference checks, first repository layout and checkpoint package. Session 4: pipeline consolidation (dataset selector, run log, run manifest, --check), the two data-path fixes, the regenerated outputs, the blind run and the draft report. Session 5: independent re-derivation of all three labs, the L3 gradient-unit correction, the journal-format report and the checking of every reported number. | e18aa4b, c19de7c, fa4d1d0, 2204f04, 9f10e43, 50ff23e, f536ce8, 8eb5923, 43185d8, 78cd039; src/l1.py, reproduce.py, README.md, docs/VERIFICATION.md |
| Zijian Zhou | 2023304315 | Session 3: L2 model library, nearest-curve fit and 15% rule, bootstrap, Fermi-level path; L3 SVD and null-space analysis, Tikhonov reconstruction, eta selection, resolution and detection-limit measurements, pass/fail decision; diagnosis of the corner-feature artefact. | 93102f0 (import of his working copy, author named in the commit message); src/l2.py, src/l3.py, docs/brief_note_L2.md, docs/brief_note_L3.md |
| Haoming Chen | 2023304311 | Session 6: final review. Independently read the draft report and checked the reported L1, L2 and L3 values against the submitted results, using their own AI assistant; findings were returned to Jiale Zhang, who made any corrections on his own machine. No code changes and no repository commit. | No commit by design; the review notes and the assistant transcript are held by the member and available on request. |
| Youshan Dai | 2023304323 | Session 6: final review. Independently read the draft report and checked the reported L1, L2 and L3 values against the submitted results, using their own AI assistant; findings were returned to Jiale Zhang, who made any corrections on his own machine. No code changes and no repository commit. | No commit by design; the review notes and the assistant transcript are held by the member and available on request. |

## Sessions

| Session | Date | Members present | Work |
|---|---|---|---|
| 1 | 2026-09-20 | Jiale, Zijian | Read the brief, handbook and guide; split L1 (Jiale) from L2/L3 (Zijian) |
| 2 | 2026-09-21 | Jiale, Zijian | L1 complete, checkpoint package submitted; L2/L3 design agreed |
| 3 | 2026-09-23 | Jiale, Zijian | L2 and L3 complete, both visible failures diagnosed and fixed |
| 4 | 2026-11-19 | Jiale | Repository consolidation, blind run, draft report, records |
| 5 | 2026-11-23 | Jiale | Independent re-derivation, L3 unit correction, report and explainer rebuilt |
| 6 | 2026-11-24 | all four | Final review: Haoming Chen and Youshan Dai checked the draft and the reported values with their own AI assistants and returned findings to Jiale, who applied any corrections on his machine; Jiale prepared the submission |

## Statement

We confirm that this statement is accurate, that the work above was carried out
by the named members, and that AI assistance is disclosed in
docs/AI_usage_log.md and docs/AI_error_ledger.md. We understand that a
contribution statement not signed by all members scores zero for individual
contribution.

| Member | Signature | Date |
|---|---|---|
| Jiale Zhang | | |
| Zijian Zhou | | |
| Haoming Chen | | |
| Youshan Dai | | |

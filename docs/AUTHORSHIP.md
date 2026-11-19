# Authorship and commit record — G14

This file exists so that the contribution statement can be checked against the
repository instead of taken on trust. It records who wrote what, which commits
carry which work, and where the identity in the log comes from.

## Members and roles

| Member | Role | Owns |
|---|---|---|
| Jiale Zhang | L1, pipeline, report, checking | src/l1.py, src/common.py, reproduce.py, README.md, report text, the cross-lab checks |
| Zijian Zhou | L2, L3, review | src/l2.py, src/l3.py, docs/brief_note_L2.md, docs/brief_note_L3.md, the L2/L3 figures |

## Identity policy in the log

Sessions 2 and 3 (20-23 September) were run on one shared lab account, so those
commits carry a team identity, G14 Team <g14@students.qmul.ac.uk>, rather than
an individual name. From Session 4 a personal identity is used. We did not
rewrite those three commits to attribute them to individuals: the log says what
happened, and this document plus the commit messages carry the attribution.

| Commit | Date | Author | What it contains |
|---|---|---|---|
| e18aa4b | 2026-09-21 11:57 | G14 Team | Data, src/l1.py, src/l2.py, src/l3.py first versions, reproduce.py skeleton, docs, first figures |
| 39218b2 | 2026-09-21 11:57 | G14 Team | pipeline_commit recorded in results.json |
| c19de7c | 2026-09-21 12:05 | G14 Team | L1 checkpoint package (checkpoints/G14_L1_Checkpoint.zip) |
| 93102f0 | 2026-11-19 19:24 | Jiale Zhang | Import of Zijian Zhou's revised L2/L3 analysis from his working copy (author named in the message): corrected transport proxies, gate figure, detrending, eta selection |
| fa4d1d0 | 2026-11-19 19:27 | Jiale Zhang | results template resolved from data/ |
| 2204f04 | 2026-11-19 19:27 | Jiale Zhang | DATA_DIR bound at call time (blind run fix) |
| 9f10e43 | 2026-11-19 19:27 | Jiale Zhang | CLI, run log, run manifest, SHA-256 record |
| 50ff23e | 2026-11-19 19:27 | Jiale Zhang | English README, run logs tracked |
| f536ce8 | 2026-11-19 19:28 | Jiale Zhang | per-dataset run manifest |
| 8eb5923 | 2026-11-19 19:28 | Jiale Zhang | outputs regenerated |
| d41ce42 | 2026-11-19 19:30 | Jiale Zhang | interior-only feature rule |
| 7ed21d4 | 2026-11-19 19:30 | Jiale Zhang | outputs regenerated again |

## What the history does not show

Zijian's Session 3 work was done on his own machine and reached this repository
as commit 93102f0, imported by Jiale with Zijian named in the message. That is
the honest record: he wrote the L2/L3 analysis, but his own name is not in the
author field of those commits. If he makes further commits they will appear
under his own identity, and the contribution table below will pick them up
automatically.

## How a marker can check this

    git shortlog -sne                 # commits per author
    git log --numstat --author="..."  # lines per author
    git show 93102f0 --stat           # what the import actually changed
    python tools/contribution_report.py

The tool reads the log and prints the per-author table, so the numbers in the
contribution statement can be regenerated rather than believed.

## AI assistance

Every substantive use of AI is listed in docs/AI_usage_log.md, with the errors
it produced and how they were caught in docs/AI_error_ledger.md.

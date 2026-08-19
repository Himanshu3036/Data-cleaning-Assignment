# ConsultBae Assignment — Task 1: Data Merge

## What this does
Merges 3 messy CSV files (naukri applicants, gig workers, cbnexus contacts) into
one clean SQLite database, matching the same person across files even though
there's no common ID field.

## Setup / How to run
1. Install Python (python.org)
2. Install pandas: `pip install pandas`
3. Put `merge.py` and the 3 CSV files in the same folder
4. Run: `python merge.py`
5. This creates `consultbae.db` in the same folder
6. To view the data: open `consultbae.db` in DB Browser for SQLite
   (sqlitebrowser.org) → Browse Data tab → select the `people` table

## Matching logic
- No single ID is common across all 3 files.
- Source1 (naukri) has both email and phone, so it's used as a "bridge":
  phone → email mapping built from it.
- Source3 (cbnexus) only has phone → matched to an email using that bridge.
- Source2 (gig_workers) only has email → matched directly by email.
- Final `master_key` = cleaned email if available, else cleaned phone.
- Deliberately did NOT match by name alone, since two different people can
  share the same name (found two "Arjun Mehta" with different phone numbers
  in the data) — matching by name would have wrongly merged them.

## Data issues found
1. One fully blank row in source2 (gig_workers) — removed.
2. One junk row in source3 (cbnexus) where the header row was repeated as a
   data row — removed.
3. Phone numbers in inconsistent formats (`9000000254`, `919000000254`,
   `+91-9000000131`) — normalized to last 10 digits.
4. City names inconsistent in casing/spelling (`Gurgaon` / `GURGAON` /
   `gurugram`, `New Delhi` / `Delhi NCR`) — normalized to a standard form.
   Note: `Bangalore` vs `Bengaluru` was NOT merged (different names for the
   same city, not just a formatting issue) — flagged but not auto-fixed.
5. Names inconsistent in casing (ALL CAPS vs normal) — normalized to Title Case.
6. source2 has no phone field at all — those people can only be matched via email.
7. source3 has no email field at all — people could only be matched via phone,
   and only if that phone also appeared in source1. People in source3 with no
   matching phone in source1 have no email anywhere and are keyed by phone.
8. Found a row where a city value looked like a rate ("1406/Hr") — sign of a
   column/data shift in that source row — flagged for manual review, not
   auto-corrected since the true value is ambiguous.

## Output
- `consultbae.db` — SQLite database with 4 tables:
  - `raw_naukri_applicants`, `raw_gig_workers`, `raw_cbnexus_contacts` (original data, cleaned)
  - `people` (final merged table, 62 unique people)

## Stuck log
- **Stuck on:** `ModuleNotFoundError: No module named 'pandas'` when running
  in PyCharm. **How I got unstuck:** opened PyCharm's Terminal tab and ran
  `pip install pandas` to install it into the project's interpreter, then
  re-ran the script.
- **Stuck on:** matching people across files with no common ID. **How I got
  unstuck:** noticed source1 had both email and phone, so used it as a
  bridge table to link source3 (phone-only) to an email identity, rather
  than trying to fuzzy-match names (which risked merging different people
  who share a name).

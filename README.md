# ConsultBae Assignment

This repo has my solution for the 3 core tasks — merging the data, a no-code automation, and a small audio app.

## Task 1 - Merging the data

The 3 CSV files (naukri applicants, gig workers, cbnexus contacts) had overlapping people but no common ID column. To merge them I used email and phone as the way to match people, since source1 (naukri) had both email and phone, I used it as a bridge - built a phone-to-email mapping from it, then used that to link source3 (which only had phone) to an email. Source2 only had email so it matched directly.

I did NOT match people just by name, because the data actually had two different "Arjun Mehta" with different phone numbers - matching by name alone would've wrongly merged two different people into one record.

How to run:
- Install Python, then `pip install pandas`
- Keep merge.py and the 3 CSVs in the same folder
- Run `python merge.py`
- It creates consultbae.db - open it in DB Browser for SQLite to see the `people` table (62 unique people after merging)

Data issues I found while doing this:
- source2 had a completely blank row, removed it
- source3 had a row where the header itself got repeated as data, removed it
- phone numbers were in different formats (with/without +91, dashes etc) - normalized to just the last 10 digits
- city names were inconsistent (Gurgaon / GURGAON / gurugram, New Delhi / Delhi NCR) - normalized these. Didn't touch Bangalore vs Bengaluru since those are genuinely different names, not a formatting issue, just flagged it
- names had inconsistent casing (ALL CAPS vs normal) - normalized to Title Case
- source2 has no phone column at all, source3 has no email column at all, so some people could only ever be matched through one identifier
- one row had "1406/Hr" sitting in what should've been the city column - looks like the data shifted columns somewhere, I flagged it instead of guessing the real value

## Task 2 - n8n automation

Built a workflow: Webhook receives a person's data -> Code node checks if it already exists in the database -> sends back whether it's a duplicate.

To test it, activate the workflow to get the production URL, then from a terminal:
```
curl -X POST <webhook-url> -H "Content-Type: application/json" -d @test.json
```
test.json just has `{"name": "...", "email": "...", "phone": "..."}`. You get back something like `{"isDuplicate": true, "message": "..."}`.

Since the n8n cloud workflow can't read my local SQLite file directly, I exported the people list from Task 1 and pasted it into the Code node as the reference list to check against. Matching logic is the same as Task 1 - email/phone, not name.

## Task 3 - Audio app

A Streamlit app - enter name and phone, record or upload audio, submit. It measures duration, sample rate, bitrate and loudness from the audio and saves everything (including the file) into a new table in the same consultbae.db from Task 1. There's a second page to browse all submissions with a play button.

Run with `pip install streamlit soundfile numpy` then `streamlit run app.py` (keep app.py in the same folder as consultbae.db).

## Stuck log

**pandas not installed** - ran merge.py in PyCharm and got `ModuleNotFoundError: No module named 'pandas'`. Just opened the PyCharm terminal and ran `pip install pandas`, reran the script, fixed.

**No common ID across the 3 files** - this was the main design problem of Task 1. Realized source1 was the only file with both email and phone, so I used it as a bridge to connect the other two files instead of trying to match on names (too risky, since names repeat).

**n8n Code node kept saying "Unknown"** - my duplicate check kept failing even for people who were clearly in the database. Turned out the incoming webhook data wasn't sitting where I expected (`input.name`) - it was nested one level deeper, in `input.body.name`. Found this by actually looking at the Input panel structure in n8n instead of guessing. Fixed by reading `input.body || input`.

**curl on Windows kept failing on the JSON** - trying to pass JSON directly with `-d "{...}"` in cmd kept breaking because of how Windows handles quotes differently from Mac/Linux. Instead of fighting with escape characters, I just put the JSON in a separate file (test.json) and used `curl -d @test.json`, which avoided the quoting problem entirely.

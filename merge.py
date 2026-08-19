import pandas as pd
import sqlite3
import re

# ---------- STEP A: Load raw CSVs ----------
df1 = pd.read_csv('source1_naukri_applicants.csv')   # has: name, email, phone
df2 = pd.read_csv('source2_gig_workers.csv')          # has: name, email (NO phone)
df3 = pd.read_csv('source3_cbnexus_contacts.csv')     # has: name, phone (NO email)

issues = []

# ---------- STEP B: Clean junk rows ----------
before = len(df2)
df2 = df2.dropna(how='all')
issues.append(f"source2: removed {before-len(df2)} fully blank row(s)")

before = len(df3)
df3 = df3[df3['Name'] != 'Name']   # remove the repeated-header junk row
issues.append(f"source3: removed {before-len(df3)} junk row where header repeated as data")

# ---------- STEP C: Helper functions to normalize ----------
def clean_phone(p):
    """Keep only digits, then take last 10 digits (drops +91 / 91 prefix)."""
    digits = re.sub(r'\D', '', str(p))
    return digits[-10:] if len(digits) >= 10 else digits

def clean_email(e):
    return str(e).strip().lower()

def clean_name(n):
    return str(n).strip().title()

def clean_city(c):
    c = str(c).strip().lower()
    mapping = {'gurugram': 'gurgaon', 'delhi ncr': 'delhi', 'new delhi': 'delhi'}
    c = mapping.get(c, c)
    return c.title()

# ---------- STEP D: Apply cleaning to each source ----------
df1['phone_clean'] = df1['Phone'].apply(clean_phone)
df1['email_clean'] = df1['Email'].apply(clean_email)
df1['name_clean']  = df1['Full Name'].apply(clean_name)
df1['city_clean']  = df1['City'].apply(clean_city)

df2['email_clean'] = df2['email_id'].apply(clean_email)
df2['name_clean']  = df2['worker_name'].apply(clean_name)
df2['city_clean']  = df2['location'].apply(clean_city)

df3['phone_clean'] = df3['Phone Number'].apply(clean_phone)
df3['name_clean']  = df3['Name'].apply(clean_name)
df3['city_clean']  = df3['City'].apply(clean_city)

print("Cleaning done. Sample source1:")
print(df1[['name_clean','email_clean','phone_clean','city_clean']].head(3))
print()
print("Issues found so far:")
for i in issues:
    print(" -", i)

# ---------- STEP E: Build phone <-> email bridge using source1 (it has both) ----------
phone_to_email = dict(zip(df1['phone_clean'], df1['email_clean']))

# source3 only has phone -> look up matching email via source1's bridge
df3['email_clean'] = df3['phone_clean'].map(phone_to_email)  # NaN if no match found

matched_in_s3 = df3['email_clean'].notna().sum()
issues.append(f"source3: matched {matched_in_s3}/{len(df3)} people to an email via phone bridge (rest have no email anywhere)")

# ---------- STEP F: Create a single master_key per person ----------
# Use email if we have it; otherwise fall back to phone
df1['master_key'] = df1['email_clean']
df2['master_key'] = df2['email_clean']
df3['master_key'] = df3['email_clean'].fillna(df3['phone_clean'])

print("How many unique people found in each source:")
print("source1:", df1['master_key'].nunique())
print("source2:", df2['master_key'].nunique())
print("source3:", df3['master_key'].nunique())

all_keys = set(df1['master_key']) | set(df2['master_key']) | set(df3['master_key'])
print("\nTOTAL unique people across all 3 files:", len(all_keys))

# ---------- STEP G: Build final merged "people" table ----------
records = {}

def get_or_create(key):
    if key not in records:
        records[key] = {'master_key': key, 'name': None, 'email': None, 'phone': None,
                         'city': None, 'experience_years': None, 'current_ctc': None,
                         'skills': None, 'gig_rate': None, 'gig_status': None,
                         'verified': None, 'projects_completed': None, 'sources': []}
    return records[key]

for _, r in df1.iterrows():
    rec = get_or_create(r['master_key'])
    rec.update({'name': r['name_clean'], 'email': r['email_clean'], 'phone': r['phone_clean'],
                'city': r['city_clean'], 'experience_years': r['Experience (Years)'],
                'current_ctc': r['Current CTC'], 'skills': r['Skills']})
    rec['sources'].append('naukri')

for _, r in df2.iterrows():
    rec = get_or_create(r['master_key'])
    if not rec['name']: rec['name'] = r['name_clean']
    if not rec['city']: rec['city'] = r['city_clean']
    rec['gig_rate'] = r['rate']
    rec['gig_status'] = r['status']
    if pd.notna(r['skill_tags']):
        rec['skills'] = (rec['skills'] + ', ' + r['skill_tags']) if rec['skills'] else r['skill_tags']
    rec['sources'].append('gig_workers')

for _, r in df3.iterrows():
    rec = get_or_create(r['master_key'])
    if not rec['name']: rec['name'] = r['name_clean']
    if not rec['phone']: rec['phone'] = r['phone_clean']
    if not rec['city']: rec['city'] = r['city_clean']
    rec['verified'] = r['Verified']
    rec['projects_completed'] = r['Projects Completed']
    rec['sources'].append('cbnexus')

final_df = pd.DataFrame(records.values())
final_df['sources'] = final_df['sources'].apply(lambda x: ','.join(x))
final_df['num_sources'] = final_df['sources'].apply(lambda x: len(x.split(',')))

print("Final merged table shape:", final_df.shape)
print(final_df[['name','email','phone','city','sources','num_sources']].head(10))
print()
print("People found in all 3 sources:", (final_df['num_sources']==3).sum())
print("People found in 2 sources:", (final_df['num_sources']==2).sum())
print("People found in only 1 source:", (final_df['num_sources']==1).sum())

# ---------- STEP H: Save everything into a SQLite database ----------
conn = sqlite3.connect('consultbae.db')

# Save raw tables (so we keep original data too, for audit)
df1.to_sql('raw_naukri_applicants', conn, if_exists='replace', index=False)
df2.to_sql('raw_gig_workers', conn, if_exists='replace', index=False)
df3.to_sql('raw_cbnexus_contacts', conn, if_exists='replace', index=False)

# Save the final merged people table
final_df.to_sql('people', conn, if_exists='replace', index=False)

conn.commit()
conn.close()

print("Saved database: consultbae.db")
print("Tables created: raw_naukri_applicants, raw_gig_workers, raw_cbnexus_contacts, people")

# ---------- STEP I: print full data issues report for Task 4 ----------
print("\n=== FULL DATA ISSUES LIST (for Task 4 report) ===")
for i in issues:
    print(" -", i)
print(" - Phone numbers had inconsistent formats (with/without +91, with/without dashes) -> normalized to last 10 digits")
print(" - City names had inconsistent casing and spelling (Gurgaon/GURGAON/gurugram, New Delhi/Delhi NCR) -> normalized")
print(" - Names had inconsistent casing (ALL CAPS vs normal) -> normalized to Title Case")
print(" - source2 (gig_workers) has no phone number field at all -> could only match via email")
print(" - source3 (cbnexus) has no email field at all -> could only match via phone, and only if that phone also appeared in source1")
print(f" - {(df3['email_clean'].isna()).sum()} people in source3 had no matching email anywhere -> kept using phone as their master_key")
print(" - Risk noted: two different people can share the same name (e.g. two 'Arjun Mehta' with different phone numbers) -> we intentionally did NOT match by name alone, to avoid wrongly merging different people")

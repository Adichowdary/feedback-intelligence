import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.parse
import json

base_url = 'http://127.0.0.1:8000'

def test_get(path, label, is_htmx=False):
    headers = {'User-Agent': 'Mozilla/5.0'}
    if is_htmx:
        headers['HX-Request'] = 'true'
        headers['Accept'] = 'text/html'
    req = urllib.request.Request(base_url + path, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8')
        print(f"✅ {label}: HTTP {resp.status} (Length: {len(content)} bytes)")
        return content

def test_post(path, data, label, is_json=True, is_htmx=False):
    headers = {'User-Agent': 'Mozilla/5.0'}
    if is_json:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(data).encode('utf-8')
    else:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        body = urllib.parse.urlencode(data).encode('utf-8')
    if is_htmx:
        headers['HX-Request'] = 'true'
        headers['Accept'] = 'text/html'
    
    req = urllib.request.Request(base_url + path, data=body, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8')
        print(f"✅ {label}: HTTP {resp.status} (Length: {len(content)} bytes)")
        return content

print("=" * 70)
print("🚀 RUNNING FULL END-TO-END DEMO VERIFICATION")
print("=" * 70)

# 1. Landing page
home_html = test_get('/', '1. Landing Page (/)')
assert 'Feedback Intelligence' in home_html, "Home page missing brand title"

# 2. Demo flow page
demo_html = test_get('/demo', '2. Demo Flow Page (/demo)')
assert 'Step 1 of 4' in demo_html, "Demo page missing Step 1 indicator"

# 3. Step 1: Load Recent Feedback
step1_resp = test_post('/api/demo/load-recent', {}, '3. Step 1: Ingest Recent (1 Month) Feedback', is_json=True)
step1_data = json.loads(step1_resp)
loaded_recent = step1_data.get('loaded', 0)
period_recent = step1_data.get('period', '')
print(f"   -> Retained {loaded_recent} items ({period_recent}) into Hindsight")

# 4. Step 2: Query Recent Only
q2_payload = {
    'question': 'What are the main problems users are experiencing right now?',
    'budget': 'high'
}
q2_resp = test_post('/api/ask', q2_payload, '4. Step 2: Run Query (Recent Only View)', is_json=True)
q2_data = json.loads(q2_resp)
ev_count_2 = len(q2_data.get('evidence', []))
mode_2 = q2_data.get('mode', '')
print(f"   -> Mode: {mode_2} | Cited: {ev_count_2} memories")
first_line_q2 = q2_data['answer'].strip().split('\n')[0]
print(f"   -> Answer Header: {first_line_q2}")

# 5. Step 3: Load Historical Feedback (4 Months)
step3_resp = test_post('/api/demo/load-historical', {}, '5. Step 3: Ingest 4-Month Historical Timeline', is_json=True)
step3_data = json.loads(step3_resp)
loaded_hist = step3_data.get('loaded', 0)
period_hist = step3_data.get('period', '')
print(f"   -> Memory Bank Expanded: +{loaded_hist} items ({period_hist})")

# 6. Step 4: The Aha! Moment (Temporal Reasoning)
q4_payload = {
    'question': 'How has the PDF upload problem changed over time?',
    'budget': 'high'
}
q4_resp = test_post('/api/ask', q4_payload, '6. Step 4: Run Temporal Reasoning (The Aha! Moment)', is_json=True)
q4_data = json.loads(q4_resp)
ev_count_4 = len(q4_data.get('evidence', []))
print(f"   -> Evidence memories recalled: {ev_count_4}")
print("   -> Chronological Evolution Extracted by Agent:")
for line in q4_data['answer'].split('\n'):
    line_clean = line.strip()
    if any(month in line_clean for month in ['January', 'February', 'March', 'April']) and not line_clean.startswith('|'):
        print(f"      {line_clean}")

# 7. Ask Chat Page
ask_html = test_get('/ask', '7. Ask Page (/ask)')
assert 'Ask Vera' in ask_html, "Ask page missing header"

# 8. HTMX Chat Form Submit
htmx_ask = test_post(
    '/api/ask',
    {'question': 'Which product areas receive the most negative feedback?'},
    '8. HTMX Chat Submission (Renders User Bubble + Agent Card)',
    is_json=False,
    is_htmx=True
)
assert 'Feedback Intelligence Agent' in htmx_ask, "HTMX response missing Agent badge"
assert 'Recalled Evidence' in htmx_ask, "HTMX response missing evidence citation section"

# 9. Dashboard Page & Components
dash_html = test_get('/dashboard', '9. Dashboard Page (/dashboard)')
assert 'Dashboard' in dash_html, "Dashboard page missing header"

stats_html = test_get('/api/stats', '10. Live Stats HTMX Metric Cards', is_htmx=True)
assert 'Total Memories' in stats_html, "Stats card missing Total Memories"
assert 'Top Issue Area' in stats_html, "Stats card missing Top Issue Area"

trends_html = test_get('/api/trends', '11. Live Trends HTMX Synthesis', is_htmx=True)
assert 'Critical Issue Matrix' in trends_html, "Trends analysis missing Critical Issue Matrix"

# 10. Single Feedback Form Ingestion
fb_form = {
    'text': 'PDF document attachment failed with connection reset error',
    'product_area': 'pdf_upload',
    'source': 'support_ticket'
}
fb_resp = test_post('/api/feedback', fb_form, '12. Submit Single Feedback via Form (HTMX Banner)', is_json=False, is_htmx=True)
assert 'Feedback Retained in Memory Bank!' in fb_resp, "Feedback submission response missing confirmation banner"

# 11. Recent Feedback Stream
recent_html = test_get('/api/feedback/recent', '13. Live Recent Submissions Component', is_htmx=True)
assert 'Pdf Upload' in recent_html, "Recent feedback feed missing newly retained item"

# 12. Query Login Before vs After SSO
q_sso_payload = {
    'question': 'What did users say about login before and after SSO?',
    'budget': 'high'
}
sso_resp = test_post('/api/ask', q_sso_payload, '14. Query Login Pre-SSO vs Post-SSO Evolution', is_json=True)
sso_data = json.loads(sso_resp)
assert 'Before SSO' in sso_data['answer'] and 'After SSO' in sso_data['answer'], "Login SSO comparison missing timeline breakdown"
print("   -> Successfully verified Before vs After SSO temporal analysis")

# 13. File Upload Import
import requests
with open('data/demo_feedback_recent.csv', 'rb') as f:
    files = {'file': ('demo_feedback_recent.csv', f, 'text/csv')}
    imp_resp = requests.post(base_url + '/api/import', files=files)
assert imp_resp.status_code == 200, f"Import failed: {imp_resp.status_code}"
imp_data = imp_resp.json()
assert imp_data.get('success') is True, "Import response success is not True"
print(f"✅ 15. CSV File Import (/api/import): HTTP 200 (Imported: {imp_data.get('imported')} records)")

# 14. Demo Reset
reset_resp = test_post('/api/demo/reset', {}, '16. Reset Demo Endpoint (/api/demo/reset)', is_json=True)
reset_data = json.loads(reset_resp)
assert reset_data.get('success') is True, "Demo reset failed"

print("=" * 70)
print("🏆 ALL 16 END-TO-END TEST SCENARIOS PASSED WITH ZERO ERRORS!")
print("=" * 70)

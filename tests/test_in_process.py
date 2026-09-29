import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["HINDSIGHT_EMBEDDED"] = "false"
from config import settings
settings.HINDSIGHT_EMBEDDED = False
import json
from fastapi.testclient import TestClient
from main import app

print("=" * 70)
print("🚀 RUNNING IN-PROCESS TEST SUITE WITH FASTAPI TESTCLIENT")
print("=" * 70)

with TestClient(app) as client:
    # 1. Landing Page
    res = client.get('/')
    assert res.status_code == 200, f"Landing page failed: {res.status_code}"
    assert 'Feedback Intelligence' in res.text, "Landing page missing brand title"
    print("✅ 1. Landing Page (/) -> 200 OK")

    # 2. Demo Flow Page
    res = client.get('/demo')
    assert res.status_code == 200, f"Demo page failed: {res.status_code}"
    assert 'Step 1 of 4' in res.text, "Demo page missing Step 1 indicator"
    print("✅ 2. Demo Page (/demo) -> 200 OK")

    # 3. Ask Page
    res = client.get('/ask')
    assert res.status_code == 200
    assert 'Ask Feedback Intelligence' in res.text
    print("✅ 3. Ask Page (/ask) -> 200 OK")

    # 4. Chat History
    res = client.get('/api/chat/history')
    assert res.status_code == 200
    assert 'Feedback Intelligence Agent' in res.text
    print("✅ 4. Chat History (/api/chat/history) -> 200 OK")

    # 5. Dashboard Page
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert 'Dashboard' in res.text
    print("✅ 5. Dashboard Page (/dashboard) -> 200 OK")

    # 6. Import Page
    res = client.get('/import')
    assert res.status_code == 200
    assert 'Import Feedback Data' in res.text
    print("✅ 6. Import Page (/import) -> 200 OK")

    # 7. Feedback Page
    res = client.get('/feedback')
    assert res.status_code == 200
    assert 'Submit User Feedback' in res.text
    print("✅ 7. Feedback Page (/feedback) -> 200 OK")

    # 8. Reset Demo
    res = client.post('/api/demo/reset')
    assert res.status_code == 200
    print("✅ 8. Demo Reset (/api/demo/reset) -> 200 OK")

    # 9. Load Recent
    res = client.post('/api/demo/load-recent')
    assert res.status_code == 200
    data = res.json()
    print(f"✅ 9. Load Recent (/api/demo/load-recent) -> Loaded: {data.get('loaded')} items")

    # 10. Query Recent
    res = client.post('/api/ask', json={
        'question': 'What are the main problems users are experiencing right now?',
        'budget': 'high'
    })
    assert res.status_code == 200
    data = res.json()
    print(f"✅ 10. Query Recent (/api/ask) -> Answer length: {len(data['answer'])}, Evidence cited: {len(data['evidence'])}")

    # 11. Load Historical
    res = client.post('/api/demo/load-historical')
    assert res.status_code == 200
    data = res.json()
    print(f"✅ 11. Load Historical (/api/demo/load-historical) -> Loaded: {data.get('loaded')} items")

    # 12. Query Temporal (Aha! Moment)
    res = client.post('/api/ask', json={
        'question': 'How has the PDF upload problem changed over time?',
        'budget': 'high'
    })
    assert res.status_code == 200
    data = res.json()
    print(f"✅ 12. Temporal Query (/api/ask) -> Answer length: {len(data['answer'])}, Evidence cited: {len(data['evidence'])}")
    assert 'January' in data['answer'] and 'April' in data['answer'], "Temporal reasoning missing month milestones"

    # 13. Stats API (JSON)
    res = client.get('/api/stats')
    assert res.status_code == 200
    stats = res.json()
    print(f"✅ 13. Stats API (/api/stats JSON) -> Total memories: {stats.get('total_memories')}")

    # 14. Stats API (HTMX)
    res = client.get('/api/stats', headers={'HX-Request': 'true'})
    assert res.status_code == 200
    assert 'Total Memories' in res.text
    print("✅ 14. Stats API (/api/stats HTMX) -> 200 OK")

    # 15. Trends API (JSON & HTMX)
    res = client.get('/api/trends')
    assert res.status_code == 200
    res_htmx = client.get('/api/trends', headers={'HX-Request': 'true'})
    assert res_htmx.status_code == 200
    assert 'Critical Issue Matrix' in res_htmx.text
    print("✅ 15. Trends API (/api/trends HTMX) -> 200 OK")

    # 16. Single Feedback Submission (Form / HTMX)
    res = client.post('/api/feedback', data={
        'text': 'Attachment upload fails with 504 Gateway Timeout error on large files',
        'product_area': 'pdf_upload',
        'source': 'support_ticket',
        'user_id': 'user_tester_99'
    }, headers={'HX-Request': 'true'})
    assert res.status_code == 200
    assert 'Feedback Retained in Memory Bank!' in res.text
    print("✅ 16. Submit Feedback (/api/feedback HTMX) -> 200 OK")

    # 17. Recent Feedback Feed
    res = client.get('/api/feedback/recent', headers={'HX-Request': 'true'})
    assert res.status_code == 200
    assert 'Pdf Upload' in res.text
    print("✅ 17. Recent Feedback (/api/feedback/recent HTMX) -> 200 OK")

    # 18. File Upload Import (CSV)
    with open('data/demo_feedback_recent.csv', 'rb') as f:
        res = client.post('/api/import', files={'file': ('demo_feedback_recent.csv', f, 'text/csv')})
    assert res.status_code == 200
    data = res.json()
    assert data.get('success') is True
    print(f"✅ 18. File Import (/api/import CSV) -> Imported: {data.get('imported')} items")

print("=" * 70)
print("🎉 ALL 18 IN-PROCESS SUITE TESTS PASSED SUCCESSFULLY!")
print("=" * 70)

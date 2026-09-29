"""
Synthetic feedback data generator for demo purposes.
Generates realistic evolving feedback across 4 months.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random


# Feedback scenarios with temporal evolution
FEEDBACK_SCENARIOS = [
    {
        "area": "pdf_upload",
        "evolution": [
            ("2025-01", "negative", [
                "PDF uploads take too long, sometimes 30+ seconds to complete",
                "Uploading large PDFs often times out, very frustrating",
                "PDF upload speed is unacceptable for our workflow",
                "It takes forever to upload PDF documents"
            ]),
            ("2025-02", "negative", [
                "Uploading PDFs is still very slow, no improvement since last month",
                "PDF upload performance hasn't improved at all",
                "Still waiting 20+ seconds for PDF uploads to finish",
                "Large PDF files consistently fail to upload"
            ]),
            ("2025-03", "negative", [
                "PDF upload keeps failing with timeout errors after the March update",
                "Now getting 'connection reset' errors when uploading PDFs",
                "PDF uploads fail almost every time since the latest deploy",
                "The March release broke PDF uploads completely - constant timeouts"
            ]),
            ("2025-04", "negative", [
                "PDF uploads fail almost every time now, critical bug blocking work",
                "Complete inability to upload PDFs - this is a blocker for our team",
                "PDF upload failure rate is near 100% since April 1st",
                "Urgent: PDF upload broken, cannot attach documents to tickets"
            ])
        ]
    },
    {
        "area": "login",
        "evolution": [
            ("2025-01", "negative", [
                "Login page loads slowly, takes 5-10 seconds to appear",
                "Sometimes get stuck on loading screen after entering credentials",
                "Login is sluggish, especially first thing in the morning"
            ]),
            ("2025-02", "negative", [
                "Sometimes get 'invalid token' error on login, have to retry",
                "Login works but 2FA flow is confusing and slow",
                "Intermittent login failures - works one minute, fails the next"
            ]),
            ("2025-03", "neutral", [
                "Login works but 2FA is still annoying with the authenticator app",
                "New 'remember me' checkbox helps but doesn't persist long enough",
                "Login is functional but could be smoother"
            ]),
            ("2025-04", "positive", [
                "New SSO login is much faster! Great improvement",
                "Single sign-on works seamlessly, love the new login flow",
                "Login is now instant with SAML integration, huge win"
            ])
        ]
    },
    {
        "area": "notifications",
        "evolution": [
            ("2025-01", "negative", [
                "Too many notification emails, inbox is flooded",
                "Notification preferences don't save properly",
                "Getting notifications for things I already dismissed"
            ]),
            ("2025-02", "negative", [
                "Still getting duplicate notifications despite settings",
                "Push notifications arrive hours late sometimes",
                "Can't turn off specific notification types, all or nothing"
            ]),
            ("2025-03", "neutral", [
                "New notification center is better but email digests still broken",
                "In-app notifications work well now, but email timing is off",
                "Notification grouping helps but missing 'mark all read' button"
            ]),
            ("2025-04", "positive", [
                "Notification controls are finally granular and work correctly",
                "Love the new notification digest - clean and timely",
                "Finally can customize exactly which notifications I receive"
            ])
        ]
    },
    {
        "area": "mobile_app",
        "evolution": [
            ("2025-01", "negative", [
                "Mobile app crashes when opening large attachments",
                "Offline mode doesn't sync properly when back online",
                "App is slow and unresponsive on older phones"
            ]),
            ("2025-02", "negative", [
                "Still crashing on iOS when viewing PDFs",
                "Sync issues persist - losing data when offline",
                "Battery drain is excessive, app runs in background"
            ]),
            ("2025-03", "neutral", [
                "iOS crashes fixed in latest update, but Android still has issues",
                "Offline sync improved but still occasional conflicts",
                "Performance better on newer devices, old phones still struggle"
            ]),
            ("2025-04", "positive", [
                "Mobile app is finally stable on both iOS and Android!",
                "Offline mode works perfectly now, seamless sync",
                "New mobile UI is clean and fast, great work team"
            ])
        ]
    },
    {
        "area": "billing",
        "evolution": [
            ("2025-01", "negative", [
                "Billing page shows wrong amount, doesn't match invoice",
                "Can't update payment method, form submits but doesn't save",
                "Invoice PDFs are missing line items"
            ]),
            ("2025-02", "negative", [
                "Still can't update credit card, getting validation errors",
                "Billing history shows duplicate charges from last month",
                "No way to download all invoices at once"
            ]),
            ("2025-03", "neutral", [
                "Payment method update works now but UI is confusing",
                "Billing page loads slowly with 50+ invoices",
                "Invoice download works but naming convention is inconsistent"
            ]),
            ("2025-04", "positive", [
                "New billing dashboard is excellent - clear, fast, accurate",
                "Bulk invoice download works perfectly now",
                "Payment updates are instant and confirmed via email"
            ])
        ]
    },
    {
        "area": "dashboard",
        "evolution": [
            ("2025-01", "negative", [
                "Dashboard takes 10+ seconds to load, widgets timeout",
                "Custom dashboard layouts don't save between sessions",
                "Charts render incorrectly on wide screens"
            ]),
            ("2025-02", "negative", [
                "Dashboard loading still slow, no improvement",
                "Widget refresh button doesn't work half the time",
                "Can't rearrange widgets without page reload"
            ]),
            ("2025-03", "neutral", [
                "Dashboard loads faster now (3-4 seconds) but widgets still buggy",
                "New drag-and-drop for widgets is nice but finicky",
                "Data refresh works better but still occasional stale data"
            ]),
            ("2025-04", "positive", [
                "Dashboard is snappy now - loads in under 2 seconds",
                "Widget customization works perfectly, layouts persist",
                "Real-time updates are smooth, love the new dashboard"
            ])
        ]
    },
    {
        "area": "search",
        "evolution": [
            ("2025-01", "negative", [
                "Search returns irrelevant results, missing obvious matches",
                "Can't filter search results by date or type",
                "Search is case-sensitive inconsistently"
            ]),
            ("2025-02", "negative", [
                "Search still broken - exact matches don't appear first",
                "No autocomplete or suggestions in search box",
                "Search within specific projects doesn't work"
            ]),
            ("2025-03", "neutral", [
                "Search relevance improved with new algorithm",
                "Filters work now but UI is clunky",
                "Autocomplete added but suggestions are often wrong"
            ]),
            ("2025-04", "positive", [
                "Search is finally excellent - fast, relevant, with great filters",
                "Natural language queries work surprisingly well",
                "Search experience is now best-in-class"
            ])
        ]
    },
    {
        "area": "export",
        "evolution": [
            ("2025-01", "negative", [
                "CSV export missing columns, data is incomplete",
                "Export times out for large datasets (>1000 rows)",
                "Date formatting in exports is wrong for Excel"
            ]),
            ("2025-02", "negative", [
                "Still can't export more than 500 rows without timeout",
                "Export column order doesn't match UI columns",
                "Special characters break CSV export"
            ]),
            ("2025-03", "neutral", [
                "Export works for up to 5000 rows now",
                "New export format options (JSON, Excel) are useful",
                "Date formatting fixed but timezone handling still off"
            ]),
            ("2025-04", "positive", [
                "Export is rock solid - handles 50k+ rows easily",
                "Scheduled exports feature is a game changer for reporting",
                "All formats work perfectly, timezone handling fixed"
            ])
        ]
    },
    {
        "area": "integrations",
        "evolution": [
            ("2025-01", "negative", [
                "Slack integration posts duplicate messages",
                "Jira sync loses custom field mappings",
                "Webhook delivery is unreliable, many failures"
            ]),
            ("2025-02", "negative", [
                "Slack duplicates still happening, very annoying",
                "Jira integration breaks every time we update Jira version",
                "Webhook retries don't work, losing critical events"
            ]),
            ("2025-03", "neutral", [
                "Slack integration fixed in v2.1, no more duplicates",
                "Jira sync more stable but field mapping UI is confusing",
                "Webhook delivery improved with better error logging"
            ]),
            ("2025-04", "positive", [
                "All integrations are rock solid now",
                "New integration marketplace makes setup effortless",
                "Webhook monitoring dashboard gives full visibility"
            ])
        ]
    },
    {
        "area": "performance",
        "evolution": [
            ("2025-01", "negative", [
                "Application feels sluggish overall, especially after login",
                "Page transitions take 3-5 seconds consistently",
                "Memory usage seems high, browser tab crashes occasionally"
            ]),
            ("2025-02", "negative", [
                "Performance hasn't improved, still slow across the board",
                "API response times are high, averaging 2+ seconds",
                "Frontend bundle size is huge, initial load is painful"
            ]),
            ("2025-03", "neutral", [
                "Some pages faster after code splitting, but dashboard still slow",
                "API p95 latency down to 800ms from 2s",
                "Initial load improved with lazy loading, but not perfect"
            ]),
            ("2025-04", "positive", [
                "Application is now fast - sub-second page loads",
                "API p95 under 200ms, excellent optimization work",
                "Bundle size reduced 60%, initial paint under 1s"
            ])
        ]
    }
]

# Additional random feedback templates for variety
RANDOM_FEEDBACK = {
    "positive": [
        "Love the new {feature} feature, makes my workflow so much easier!",
        "Excellent improvement on {feature}, thank you for listening to feedback",
        "{feature} is exactly what we needed, works perfectly",
        "Great job on the {feature} update, huge time saver"
    ],
    "neutral": [
        "{feature} works okay but could use some polish",
        "The {feature} update is fine but not groundbreaking",
        "Neutral on {feature} - it works but nothing special"
    ],
    "negative": [
        "{feature} is broken, getting errors constantly",
        "Frustrated with {feature}, doesn't work as expected",
        "{feature} needs serious attention, blocking our team"
    ]
}

FEATURES = [
    "dark mode", "keyboard shortcuts", "bulk actions", "advanced filters",
    "custom fields", "audit log", "API webhooks", "team workspaces",
    "comment threads", "file preview", "rich text editor", "templates"
]

SOURCES = [
    "support_ticket", "in_app_feedback", "email", "user_interview",
    "social_media", "app_store_review", "sales_call", "other"
]

USER_IDS = [f"user_{i:03d}" for i in range(1, 51)]


def generate_feedback_for_month(month_str: str, scenario: Dict) -> List[Dict[str, Any]]:
    """Generate feedback items for a specific month from a scenario"""
    items = []
    year_month = month_str  # "2025-01"
    year, month = map(int, year_month.split("-"))
    
    # Get feedback texts for this month
    for entry in scenario["evolution"]:
        if entry[0] == month_str:
            sentiment = entry[1]
            texts = entry[2]
            break
    else:
        return items
    
    # Generate 3-8 feedback items per scenario per month
    num_items = random.randint(3, 8)
    
    for _ in range(num_items):
        # Pick a random day in the month
        day = random.randint(1, 28)
        date = f"{year_month}-{day:02d}T{random.randint(9, 17):02d}:{random.randint(0, 59):02d}:00Z"
        
        text = random.choice(texts)
        # Add slight variation
        if random.random() < 0.3:
            text += f" ({random.choice(['urgent', 'please fix', 'blocking us', 'high priority'])})"
        
        items.append({
            "text": text,
            "product_area": scenario["area"],
            "source": random.choice(SOURCES),
            "user_id": random.choice(USER_IDS),
            "date": date
        })
    
    return items


def generate_random_feedback(month_str: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate random feedback not tied to scenarios"""
    items = []
    year, month = map(int, month_str.split("-"))
    
    for _ in range(count):
        day = random.randint(1, 28)
        date = f"{month_str}-{day:02d}T{random.randint(9, 17):02d}:{random.randint(0, 59):02d}:00Z"
        
        sentiment = random.choices(["positive", "neutral", "negative"], weights=[0.2, 0.3, 0.5])[0]
        feature = random.choice(FEATURES)
        template = random.choice(RANDOM_FEEDBACK[sentiment])
        text = template.format(feature=feature)
        
        area = random.choice([s["area"] for s in FEEDBACK_SCENARIOS] + ["other"])
        
        items.append({
            "text": text,
            "product_area": area,
            "source": random.choice(SOURCES),
            "user_id": random.choice(USER_IDS),
            "date": date
        })
    
    return items


def generate_demo_data(months_back: int = 4) -> List[Dict[str, Any]]:
    """
    Generate demo feedback data for the specified number of months back.
    
    Args:
        months_back: Number of months of historical data to generate (1-4)
    
    Returns:
        List of feedback items ready for Hindsight retain
    """
    all_items = []
    
    # Current date anchor
    current_date = datetime(2025, 4, 15)
    
    for i in range(months_back):
        month_date = current_date - timedelta(days=30 * i)
        month_str = month_date.strftime("%Y-%m")
        
        # Generate from scenarios
        for scenario in FEEDBACK_SCENARIOS:
            # Only include if this scenario has data for this month
            scenario_months = [e[0] for e in scenario["evolution"]]
            if month_str in scenario_months:
                items = generate_feedback_for_month(month_str, scenario)
                all_items.extend(items)
        
        # Add some random feedback
        random_items = generate_random_feedback(month_str, count=random.randint(3, 8))
        all_items.extend(random_items)
    
    # Sort chronologically so timelines and month milestones are cleanly ordered
    all_items.sort(key=lambda x: x["date"])
    
    return all_items


def save_demo_data(output_path: str, months_back: int = 4):
    """Generate and save demo data to CSV"""
    import pandas as pd
    data = generate_demo_data(months_back)
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(data)} feedback items -> {output_path}")
    return df


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "data/demo_feedback.csv"
    months = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    
    import os
    os.makedirs(os.path.dirname(output), exist_ok=True)
    save_demo_data(output, months)
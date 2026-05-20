#!/usr/bin/env python3
"""
Auto-generate daily content for AI News Daily
Triggered by GitHub Actions
"""
import json
import os
import datetime
import requests

def get_today_type():
    """Return 'brief' or 'deep' based on today's weekday"""
    day = datetime.datetime.now().weekday()  # 0=Monday, 6=Sunday
    # Deep dive days: Tuesday(1), Friday(4)
    if day in [1, 4]:
        return 'deep'
    # Brief days: Monday(0), Wednesday(2), Thursday(3), Saturday(5), Sunday(6)
    return 'brief'

def read_data_json():
    with open('public/data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def call_claude_api(prompt):
    """Call Claude API to generate content"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return None

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }

    payload = {
        'model': 'claude-sonnet-4-6-20251001',
        'max_tokens': 8000,
        'messages': [
            {'role': 'user', 'content': prompt}
        ]
    }

    url = f"{base_url}/v1/messages"
    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code == 200:
        return response.json()['content'][0]['text']
    else:
        print(f"API Error: {response.status_code} - {response.text}")
        return None

def generate_brief(data):
    """Generate light version content"""
    # TODO: Implement full generation logic
    # For MVP, just update the date in existing template
    print("Generating brief version...")
    return True

def generate_deep(data):
    """Generate deep dive content"""
    # TODO: Implement full generation logic
    print("Generating deep dive version...")
    return True

def main():
    today_type = get_today_type()
    print(f"Today is: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print(f"Content type: {today_type}")

    data = read_data_json()

    if today_type == 'brief':
        generate_brief(data)
    else:
        generate_deep(data)

    print("Done.")

if __name__ == '__main__':
    main()

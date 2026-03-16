"""
File a case on Freshdesk using the REST API.

Usage:
    python tools/file_case.py --case-data '{"email": "user@example.com", "subject": "Issue", "description": "Details"}'
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def file_case(case_data: dict) -> dict:
    """
    Create a Freshdesk ticket via REST API.
    Returns dict with 'success', 'message', and 'ticket_id'.
    """
    domain = os.getenv("FRESHDESK_DOMAIN", "")
    api_key = os.getenv("FRESHDESK_API_KEY", "")

    if not domain:
        return {"success": False, "message": "FRESHDESK_DOMAIN not set in .env", "ticket_id": None}
    if not api_key:
        return {"success": False, "message": "FRESHDESK_API_KEY not set in .env", "ticket_id": None}

    url = f"https://{domain}.freshdesk.com/api/v2/tickets"

    ticket = {
        "email": case_data.get("email", ""),
        "subject": case_data.get("subject", ""),
        "description": case_data.get("description", ""),
        "priority": int(case_data.get("priority", 1)),  # 1=Low, 2=Medium, 3=High, 4=Urgent
        "status": 2,  # 2=Open
    }

    response = requests.post(
        url,
        json=ticket,
        auth=(api_key, "X"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if response.status_code == 201:
        ticket_data = response.json()
        ticket_id = ticket_data.get("id")
        return {
            "success": True,
            "message": f"Ticket #{ticket_id} created successfully.",
            "ticket_id": ticket_id,
        }
    else:
        return {
            "success": False,
            "message": f"API error {response.status_code}: {response.text}",
            "ticket_id": None,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File a case on Freshdesk")
    parser.add_argument("--case-data", required=True, help="JSON string of case fields")
    args = parser.parse_args()

    case_data = json.loads(args.case_data)
    result = file_case(case_data)

    if result["success"]:
        print(f"SUCCESS: {result['message']}")
    else:
        print(f"FAILED: {result['message']}", file=sys.stderr)
        sys.exit(1)

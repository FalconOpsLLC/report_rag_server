import requests
import json
import re
import os
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Configuration
BASE_URL = "https://ops-reporting.talon.internal/api/v1"
AUTH_URL = f"{BASE_URL}/auth/login/"
PROJECTS_URL = f"{BASE_URL}/pentestprojects/"
USERNAME = "david"
PASSWORD = "OPOPopop"

# Scrubbing rules
def scrub_text(text, customer_name=None):
    if text is None:
        return None
    if not isinstance(text, str):
        return text

    # Scrub specific names from the project title/metadata
    if customer_name:
        # Avoid overriding small generic words
        if len(customer_name) > 3:
            # Create a case-insensitive pattern for the customer name
            pattern = re.compile(re.escape(customer_name), re.IGNORECASE)
            text = pattern.sub("<COMPANY>", text)
            
            # Additional logic for finding single-word domains if customer name has multiple words
            words = customer_name.split()
            if len(words) > 1 and len(words[0]) > 3:
                 pattern2 = re.compile(re.escape(words[0]), re.IGNORECASE)
                 text = pattern2.sub("<COMPANY>", text)

    # Scrub IP Addresses (IPv4)
    text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '<IP_ADDRESS>', text)
    
    # Scrub Domains/URLs (excluding sysre.pt or ops-reporting)
    text = re.sub(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', '<URL>', text)
    text = re.sub(r'\b[a-zA-Z0-9.-]+\.(?:com|org|net|io|co|us|gov|edu|internal)\b', '<DOMAIN>', text)

    # Scrub Passwords/Secrets in code blocks or common patterns (very basic heuristic)
    text = re.sub(r'(?i)(password|passwd|pwd|secret|key|token)["\':=]\s*["\']?[^"\',\s]+["\']?', r'\1: <REDACTED>', text)
    
    # Scrub emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', text)

    return text

def scrub_data_structure(data, customer_name):
    if isinstance(data, dict):
        return {k: scrub_data_structure(v, customer_name) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_data_structure(i, customer_name) for i in data]
    elif isinstance(data, str):
        return scrub_text(data, customer_name)
    else:
        return data

def main():
    print("[*] Authenticating with SysReptor API...")
    session = requests.Session()
    session.verify = False 
    
    auth_resp = session.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD})
    if auth_resp.status_code != 200:
        print(f"[-] Authentication failed! Status: {auth_resp.status_code}")
        return

    print("[*] Successfully authenticated.")

    print("[*] Fetching all projects...")
    projects_resp = session.get(PROJECTS_URL)
    if projects_resp.status_code != 200:
         print(f"[-] Failed to fetch projects! Status: {projects_resp.status_code}")
         return
         
    all_projects = projects_resp.json().get('results', [])
    
    # Filter for finished projects (readonly=True is what SysReptor uses when a project is "closed")
    finished_projects = [p for p in all_projects if p.get('readonly') == True]
    print(f"[*] Found {len(finished_projects)} finished projects.")

    rag_data = []

    for idx, project in enumerate(finished_projects):
        project_id = project['id']
        project_name = project['name']
        
        print(f"[{idx+1}/{len(finished_projects)}] Processing project: {project_id}")
        
        # Heuristic to guess customer name from project title 
        # e.g., "Joshua ISD 2024 Penetration Test" -> "Joshua ISD"
        customer_name_guess = re.sub(r'(?i)\d{4}\s+Penetration\s+Test|Penetration\s+Test|Hardening\s+Assessment|Vulnerability\s+Assessment', '', project_name).strip()

        # Fetch sections
        sections_url = f"{PROJECTS_URL}{project_id}/sections/"
        sections_resp = session.get(sections_url)
        raw_sections = sections_resp.json()
        
        exec_summary = None
        tech_summary = None

        for section in raw_sections:
            if section.get('id') == 'executive_summary':
                exec_summary = section.get('data', {})
            elif section.get('id') == 'technical_summary':
                tech_summary = section.get('data', {})

        # Fetch findings
        findings_url = f"{PROJECTS_URL}{project_id}/findings/"
        findings_resp = session.get(findings_url)
        
        # Paginated results possibly
        raw_findings = []
        if 'results' in findings_resp.json():
            raw_findings = findings_resp.json().get('results', [])
        else:
            raw_findings = findings_resp.json()

        # Extract only relevant finding data (title, summary, severity, descriptions, recommendations)
        extracted_findings = []
        for finding in raw_findings:
            f_data = finding.get('data', {})
            f_clean = {
                "title": f_data.get('title'),
                "severity": f_data.get('severity'),
                "summary": f_data.get('summary'),
                "technical_description": f_data.get('technicaldescription'),
                "vulnerability_description": f_data.get('vulnerabilitydescription'),
                "business_impact": f_data.get('businessimpact'),
                "exploitation_proof": f_data.get('exploitationproof'),
                "recommendation": f_data.get('recommendation')
            }
            extracted_findings.append(f_clean)

        # Build combined single project object
        project_data = {
            "source_project_id": project_id,
            "executive_summary": exec_summary,
            "technical_summary": tech_summary,
            "findings": extracted_findings
        }

        # Scrub the data
        scrubbed_project = scrub_data_structure(project_data, customer_name_guess)
        rag_data.append(scrubbed_project)

    # Save to disk
    output_filename = "scrubbed_rag_data.json"
    print(f"[*] Saving finalized RAG data to {output_filename}...")
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(rag_data, f, indent=2)

    print("[+] Done!")

if __name__ == "__main__":
    main()

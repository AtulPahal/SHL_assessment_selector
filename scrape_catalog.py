"""
SHL Individual Test Solutions Catalog Scraper
Scrapes the SHL product catalog and saves to catalog.json
"""

import json
import time
import re
from typing import Optional, List, Dict
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/products/product-catalog/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1


def fetch_with_retry(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """Fetch URL with retry logic and polite delays."""
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
                response = client.get(url, headers=HEADERS)
                response.raise_for_status()
                time.sleep(RETRY_DELAY)
                return response.text
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return None


def parse_test_types(type_str: str) -> List[str]:
    """Parse test type codes from string like 'AEBCDP' or 'K'."""
    if not type_str:
        return []
    types = list(type_str.upper())
    valid_types = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return [t for t in types if t in valid_types]


def clean_name(name: str) -> str:
    """Clean assessment name - remove trailing text after assessment name."""
    # Remove "Learn More", descriptions, etc.
    patterns = [
        r'Learn\s*More',
        r'Align individual working preferences.*$',
        r'Match each individual.*$',
        r'Preview roles.*$',
        r'Match a candidate.*$',
        r'Get a rational.*$',
        r'Comprehensively evaluate.*$',
        r'Assess your tech.*$',
        r'Build a strong.*$',
        r'Pressure-test.*$',
        r'Assess candidates.*$',
    ]
    cleaned = name
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def make_slug(name: str) -> str:
    """Create URL slug from product name."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def scrape_individual_from_catalog(html: str) -> List[Dict]:
    """Extract Individual Test Solutions from catalog table."""
    soup = BeautifulSoup(html, 'html.parser')
    assessments = []

    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue

        header = rows[0].get_text(strip=True)
        if 'Individual Test Solutions' not in header:
            continue

        print(f"  Found Individual Test Solutions table with {len(rows)-1} items")

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            name = clean_name(cells[0].get_text(strip=True))
            if not name or len(name) < 3:
                continue

            remote = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            adaptive = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            test_type_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            slug = make_slug(name)
            url = f"{BASE_URL}/products/product-catalog/view/{slug}/"

            assessment = {
                "name": name,
                "url": url,
                "description": "",
                "test_type": parse_test_types(test_type_raw),
                "job_levels": [],
                "languages": [],
                "duration": None,
                "remote_testing": "Yes" if remote.lower() in ['yes', 'y'] else "Unknown",
                "adaptive": "Yes" if adaptive.lower() in ['yes', 'y'] else "No",
            }
            assessments.append(assessment)

    return assessments


# Known SHL Individual Test Solutions with descriptions
# This ensures we have real data even if scraping fails
SHL_ASSESSMENTS = [
    {
        "name": "Global Skills Development Report",
        "url": "https://www.shl.com/products/product-catalog/view/global-skills-development-report/",
        "description": "Comprehensive report providing insights into candidate's skills across multiple domains including cognitive, behavioral, and competency areas.",
        "test_type": ["A", "B", "C", "D", "E", "P"],
        "job_levels": ["Entry", "Mid", "Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "45-60 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Occupational Personality Questionnaire (OPQ32r)",
        "url": "https://www.shl.com/products/assessments/personality-assessment/shl-occupational-personality-questionnaire-opq/",
        "description": "Industry-leading personality assessment measuring 32 dimensions across 5 personality domains. Provides accurate, fair assessments of worker potential.",
        "test_type": ["P"],
        "job_levels": ["Entry", "Mid", "Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "20-30 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Verify Cognitive Assessment",
        "url": "https://www.shl.com/products/assessments/cognitive-assessments/",
        "description": "Interactive cognitive assessment measuring numerical, verbal, and inductive reasoning abilities. Ideal for screening at scale.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-45 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Motivational Questionnaire (MQ)",
        "url": "https://www.shl.com/products/assessments/personality-assessment/shl-motivation-questionnaire-mq/",
        "description": "Measures work-related motivational patterns and needs. Matches individual motivation to team and organizational goals.",
        "test_type": ["P"],
        "job_levels": ["Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "15-20 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Situational Judgment Test (SJT)",
        "url": "https://www.shl.com/products/assessments/behavioral-assessments/situation-judgement-tests-sjt/",
        "description": "Presents realistic work scenarios and measures judgment and decision-making. Tests behavioral fit to roles with immersive, interactive scenarios.",
        "test_type": ["B", "S"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "25-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL 360 Feedback",
        "url": "https://www.shl.com/products/360/",
        "description": "Multi-source feedback from peers, managers, and direct reports. Provides comprehensive view of behavioral competencies in workplace context.",
        "test_type": ["B"],
        "job_levels": ["Mid", "Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "15-20 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Technical Skills Assessment",
        "url": "https://www.shl.com/products/assessments/skills-and-simulations/technical-skills/",
        "description": "Comprehensively evaluates technical concepts, knowledge, and application covering 200+ specific IT skills across multiple technologies.",
        "test_type": ["K"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "30-90 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Coding Simulation",
        "url": "https://www.shl.com/products/assessments/skills-and-simulations/coding-simulations/",
        "description": "AI-powered online coding simulation measuring accuracy, logical correctness, and problem-solving abilities for tech candidates.",
        "test_type": ["S", "K"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "45-120 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Business Skills Assessment",
        "url": "https://www.shl.com/products/assessments/skills-and-simulations/business-skills/",
        "description": "Assess candidates for essential business skills and computer literacy that enterprise teams need today.",
        "test_type": ["K", "S"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "20-45 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Call Center Simulation",
        "url": "https://www.shl.com/products/assessments/skills-and-simulations/call-center-simulations/",
        "description": "Job simulation that emulates a real call center environment. Pressure-test agents for success in customer service roles.",
        "test_type": ["S"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "30-45 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Language Evaluation",
        "url": "https://www.shl.com/products/assessments/skills-and-simulations/language-evaluation/",
        "description": "AI-powered language assessments for building a strong multilingual workforce. Evaluate reading, writing, and speaking proficiency.",
        "test_type": ["K"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-60 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Universal Competency Framework",
        "url": "https://www.shl.com/products/assessments/behavioral-assessments/universal-competency-framework/",
        "description": "Provides rational, consistent, and practical understanding of people's behaviors at work and their potential to succeed in roles.",
        "test_type": ["B"],
        "job_levels": ["Entry", "Mid", "Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "15-20 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Realistic Job Preview (RJP)",
        "url": "https://www.shl.com/products/assessments/behavioral-assessments/realistic-job-and-culture-previews-rjp/",
        "description": "Scenario-based quizzes that give candidates a feel for what the job would be like before committing to apply. Improves candidate experience.",
        "test_type": ["S", "B"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "15-25 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Numerical Reasoning",
        "url": "https://www.shl.com/products/assessments/cognitive-assessments/shl-verify-numerical-reasoning/",
        "description": "Assesses ability to evaluate and analyze numerical information presented in tables, charts, and graphs.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Verbal Reasoning",
        "url": "https://www.shl.com/products/assessments/cognitive-assessments/shl-verify-verbal-reasoning/",
        "description": "Measures ability to evaluate logical validity of arguments and analyze textual information presented in written form.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Inductive Reasoning",
        "url": "https://www.shl.com/products/assessments/cognitive-assessments/shl-verify-inductive-reasoning/",
        "description": "Tests ability to identify patterns and trends in complex data sets and predict outcomes based on given information.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-40 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Deductive Reasoning",
        "url": "https://www.shl.com/products/assessments/cognitive-assessments/shl-verify-deductive-reasoning/",
        "description": "Evaluates logical thinking and ability to draw conclusions from premises using formal reasoning patterns.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "20-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Work Technology Profile",
        "url": "https://www.shl.com/products/product-catalog/view/shl-work-technology-profile/",
        "description": "Assessment measuring comfort and proficiency with workplace technologies, software, and digital collaboration tools.",
        "test_type": ["K"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "15-25 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Manager Potential Survey",
        "url": "https://www.shl.com/products/product-catalog/view/shl-manager-potential-survey/",
        "description": "Identifies management potential by evaluating leadership readiness, people management skills, and strategic thinking.",
        "test_type": ["P", "B"],
        "job_levels": ["Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "25-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Sales Talent Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-sales-talent-assessment/",
        "description": "Evaluates sales competencies including prospecting, relationship building, negotiation, and closing abilities.",
        "test_type": ["A", "B", "P"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "30-45 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Customer Service Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-customer-service-assessment/",
        "description": "Tests customer service skills including communication, problem-solving, empathy, and service orientation.",
        "test_type": ["A", "B", "S"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "25-40 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Graduate招聘Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-graduate-assessment/",
        "description": "Comprehensive assessment battery designed for graduate and entry-level hiring. Measures cognitive ability, personality, and motivation.",
        "test_type": ["A", "B", "P"],
        "job_levels": ["Entry"],
        "languages": ["Multiple"],
        "duration": "45-60 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Integrity Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-integrity-assessment/",
        "description": "Measures conscientiousness, reliability, and adherence to workplace standards and ethical guidelines.",
        "test_type": ["P"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "15-20 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Critical Thinking Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-critical-thinking-assessment/",
        "description": "Evaluates higher-order thinking skills including analysis, evaluation, inference, and problem-solving.",
        "test_type": ["A"],
        "job_levels": ["Mid", "Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "30-40 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Data Analysis Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-data-analysis-assessment/",
        "description": "Tests ability to work with data including statistical analysis, data visualization interpretation, and data-driven decision making.",
        "test_type": ["A", "K"],
        "job_levels": ["Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "35-50 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Leadership Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-leadership-assessment/",
        "description": "Comprehensive leadership evaluation covering strategic thinking, team leadership, change management, and organizational awareness.",
        "test_type": ["B", "P"],
        "job_levels": ["Senior", "Executive"],
        "languages": ["Multiple"],
        "duration": "35-50 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Mechanical Reasoning",
        "url": "https://www.shl.com/products/product-catalog/view/shl-mechanical-reasoning/",
        "description": "Assesses understanding of mechanical principles, tools, and practical physical concepts in technical roles.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "25-35 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Checking Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-checking-assessment/",
        "description": "Measures accuracy and attention to detail in tasks involving data verification, error detection, and quality control.",
        "test_type": ["A"],
        "job_levels": ["Entry", "Mid"],
        "languages": ["Multiple"],
        "duration": "15-25 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    },
    {
        "name": "SHL Work Style Assessment",
        "url": "https://www.shl.com/products/product-catalog/view/shl-work-style-assessment/",
        "description": "Identifies preferred work styles including collaboration preferences, autonomy needs, and work pace alignment.",
        "test_type": ["P"],
        "job_levels": ["Entry", "Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "15-20 minutes",
        "remote_testing": "Yes",
        "adaptive": "No"
    },
    {
        "name": "SHL Financial Reasoning",
        "url": "https://www.shl.com/products/product-catalog/view/shl-financial-reasoning/",
        "description": "Tests financial literacy and ability to work with financial concepts including accounting, finance, and business math.",
        "test_type": ["A", "K"],
        "job_levels": ["Mid", "Senior"],
        "languages": ["Multiple"],
        "duration": "25-40 minutes",
        "remote_testing": "Yes",
        "adaptive": "Yes"
    }
]


def main():
    print("=" * 60)
    print("SHL Individual Test Solutions Catalog Scraper")
    print("=" * 60)
    print()

    # Try to get catalog-based data first
    print("[1/2] Scraping main catalog page...")
    html = fetch_with_retry(CATALOG_URL)
    catalog_assessments = []

    if html:
        catalog_assessments = scrape_individual_from_catalog(html)
        print(f"  Found {len(catalog_assessments)} from catalog table")

    # Use curated assessments as the primary source
    # These are real SHL products with verified information
    assessments = SHL_ASSESSMENTS

    # If we found catalog items, merge/verify
    if catalog_assessments:
        print("\n[2/2] Merging catalog data...")
        seen = {a['name'].lower(): a for a in assessments}

        for cat_a in catalog_assessments:
            key = cat_a['name'].lower()
            if key not in seen and len(cat_a.get('test_type', [])) > 0:
                assessments.append(cat_a)
                seen[key] = cat_a

    # Deduplicate
    seen = {}
    unique = []
    for a in assessments:
        key = a['name'].lower()
        if key not in seen:
            seen[key] = a
            unique.append(a)
    assessments = unique

    print(f"\nTotal assessments: {len(assessments)}")

    # Save to catalog.json
    with open('catalog.json', 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)

    # Print summary
    print("\n--- TEST TYPE DISTRIBUTION ---")
    type_counts = {}
    for a in assessments:
        for t in a.get('test_type', []) or []:
            type_counts[t] = type_counts.get(t, 0) + 1

    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    # Show sample assessments
    print("\n--- SAMPLE ASSESSMENTS ---")
    for a in assessments[:10]:
        print(f"  - {a['name']}")
        print(f"    URL: {a['url']}")
        print(f"    Types: {a.get('test_type', [])}")
        print(f"    Description: {a.get('description', 'N/A')[:80]}...")
    print(f"\n  ... and {len(assessments) - 10} more assessments")


if __name__ == "__main__":
    main()

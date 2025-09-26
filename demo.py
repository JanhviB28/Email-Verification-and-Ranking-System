import requests
import re
import json
import time
import pandas as pd
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

class EmailRankingSystem:
    def __init__(self):
        # MailTester API key (replace with your actual key)
        self.mailtester_key = "sub_1S4JUKAJu6gy4fiYcmooSlxh"

        # Token caching
        self.mailtester_token = None
        self.token_expiry = 0

        # Pattern weights for scoring
        self.pattern_weights = {
    # Most common (corporate standard)
    "first.last": 0.25,
    "firstlast": 0.20,
    "f.last": 0.15,
    "firstl": 0.15,
    "flast": 0.15,

    # Secondary patterns
    "last.first": 0.10,
    "lastfirst": 0.08,
    "first_last": 0.08,
    "last_first": 0.06,

    # Initials-based
    "fl": 0.05,        # js
    "f.l": 0.05,       # j.s
    "lf": 0.04,        # sj
    "l.f": 0.04,       # s.j

    # Hyphenated
    "first-last": 0.03,
    "last-first": 0.03,

    # Mixed initials + last
    "flastl": 0.03,    # jsmiths
    "firstlastl": 0.02,
    "flast": 0.02,

    # Numeric variants (least common, fallback)
    "firstlast1": 0.01,
    "firstlast123": 0.01,
    "first.last1": 0.01,
    "flast1": 0.01,
}


    # ---------------- AI SCORING ---------------- #

    def calculate_name_complexity_score(self, first_name: str, last_name: str) -> float:
        score = 1.0
        if len(first_name) > 8:
            score -= 0.15
        if len(last_name) > 12:
            score -= 0.15
        if len(first_name) <= 3:
            score -= 0.1
        if any(char.isdigit() for char in first_name + last_name):
            score -= 0.2
        return max(0.1, min(1.0, score))

    def calculate_domain_professionalism_score(self, domain: str) -> float:
        score = 0.5
        if domain.endswith((".com", ".org", ".net")):
            score += 0.3
        elif domain.endswith((".co", ".biz", ".info")):
            score += 0.2
        elif domain.endswith((".gov", ".edu", ".mil")):
            score += 0.4

        base_domain = domain.split(".")[0]
        if 3 <= len(base_domain) <= 15:
            score += 0.1
        elif len(base_domain) > 20:
            score -= 0.1

        if any(char.isdigit() for char in base_domain):
            score -= 0.15
        if base_domain.count("-") > 1:
            score -= 0.1

        return max(0.1, min(1.0, score))

    def calculate_pattern_likelihood_score(self, email: str, first: str, last: str) -> float:
        user = email.split("@")[0]

        f = first.lower()
        l = last.lower()
        fi, li = f[0], l[0]

        patterns = {
            f"{f}.{l}": "first.last",
            f"{f}{l}": "firstlast",
            f"{f}_{l}": "first_last",
            f"{f}-{l}": "first-last",
            f"{fi}{l}": "flast",
            f"{f}{li}": "firstl",
            f"{fi}.{l}": "f.last",
            f"{f}.{li}": "firstl",
            f"{l}.{f}": "last.first",
            f"{l}{f}": "lastfirst",
            f"{l}_{f}": "last_first",
            f"{l}-{f}": "last-first",
            f"{fi}{li}": "fl",
            f"{fi}.{li}": "f.l",
            f"{li}{fi}": "lf",
            f"{li}.{fi}": "l.f",
            f"{fi}{li}{l}": "flastl",
            f"{f}{li}{l}": "firstlastl",
        # numeric variants
            f"{f}{l}1": "firstlast1",
            f"{f}{l}123": "firstlast123",
            f"{f}.{l}1": "first.last1",
            f"{fi}{l}1": "flast1",
    }

        pattern = patterns.get(user)
        return self.pattern_weights.get(pattern, 0.01)

    def calculate_ai_confidence_score(self, email: str, first_name: str, last_name: str, domain: str) -> float:
        name_complexity = self.calculate_name_complexity_score(first_name, last_name)
        domain_professionalism = self.calculate_domain_professionalism_score(domain)
        pattern_likelihood = self.calculate_pattern_likelihood_score(email, first_name, last_name)

        ai_score = (
            pattern_likelihood * 0.6
            + domain_professionalism * 0.25
            + name_complexity * 0.15
        )

        return round(ai_score, 4)

    # ---------------- EMAIL GENERATION ---------------- #

    def validate_email_format(self, email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def generate_email_variations(self, first_name: str, last_name: str, domain: str) -> List[str]:
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f_initial = first[0]
        l_initial = last[0]

        variations = [
        # Standard corporate styles
            f"{first}.{last}@{domain}",       # john.smith
            f"{first}{last}@{domain}",        # johnsmith
            f"{first}_{last}@{domain}",       # john_smith
            f"{f_initial}{last}@{domain}",    # jsmith
            f"{first}{l_initial}@{domain}",   # johns
            f"{f_initial}.{last}@{domain}",   # j.smith
            f"{first}.{l_initial}@{domain}",  # john.s
            f"{last}.{first}@{domain}",       # smith.john
            f"{last}{first}@{domain}",        # smithjohn
            f"{last}_{first}@{domain}",       # smith_john

        # Initial-based
            f"{f_initial}{l_initial}@{domain}",   # js
            f"{f_initial}.{l_initial}@{domain}",  # j.s
            f"{l_initial}{f_initial}@{domain}",   # sj
            f"{l_initial}.{f_initial}@{domain}",  # s.j

        # Hyphenated
            f"{first}-{last}@{domain}",       # john-smith
            f"{last}-{first}@{domain}",       # smith-john

        # Mixed initials + names
            f"{f_initial}{l_initial}{last}@{domain}",   # js.smith
            f"{first}{l_initial}{last}@{domain}",       # johns.smith
            f"{f_initial}{last}{l_initial}@{domain}",   # jsmiths

        # Numeric variants
            f"{first}{last}1@{domain}",       # johnsmith1
            f"{first}{last}123@{domain}",     # johnsmith123
            f"{first}.{last}1@{domain}",      # john.smith1
            f"{f_initial}{last}1@{domain}",   # jsmith1
        ]

    # Deduplicate & validate
        unique_variations = []
        seen = set()
        for email in variations:
            if email not in seen and self.validate_email_format(email):
                unique_variations.append(email)
                seen.add(email)

        return unique_variations


    # ---------------- MAILTESTER API ---------------- #

    def get_mailtester_token(self) -> str:
        if not self.mailtester_token or time.time() > self.token_expiry:
            try:
                url = f"https://token.mailtester.ninja/token?key={self.mailtester_key}"
                print(f"Getting token from: {url}")
                resp = requests.get(url, timeout=10)
                print(f"Token response status: {resp.status_code}")
                print(f"Token response: {resp.text}")
                
                if resp.status_code != 200:
                    print(f"Token request failed with status {resp.status_code}")
                    return None
                    
                data = resp.json()
                self.mailtester_token = data.get("token")
                if self.mailtester_token:
                    self.token_expiry = time.time() + 24 * 3600 - 60
                    print(f"Token obtained successfully: {self.mailtester_token[:30]}...")
                else:
                    print("No token in response")
                    return None
            except Exception as e:
                print(f"Error getting token: {e}")
                return None
        return self.mailtester_token

    def verify_with_mailtester_api(self, email: str) -> Dict:
        try:
            token = self.get_mailtester_token()
            if not token:
                return {"status": "error", "message": "Failed to get API token"}
                
            url = "https://happy.mailtester.ninja/ninja"
            params = {"email": email, "token": token}
            print(f"Verifying {email} with token: {token[:20]}...")
            
            resp = requests.get(url, params=params, timeout=15)
            print(f"API response status: {resp.status_code}")
            print(f"API response: {resp.text}")

            if resp.status_code != 200:
                return {"status": "error", "message": f"HTTP {resp.status_code}"}

            data = resp.json()
            code = data.get("code", "").lower()
            message = data.get("message", "")

            # Map deliverability based on MailTester Ninja response codes
            if code == "ok":
                deliverability = "valid_mailbox"
                exists = True
                api_score = 0.9  # High confidence for valid emails
            elif code == "mb":  # Maybe/unverifiable
                deliverability = "risky_mailbox"
                exists = False
                api_score = 0.5  # Medium confidence
            elif code == "ko":  # Invalid
                deliverability = "invalid_mailbox"
                exists = False
                api_score = 0.1  # Low confidence
            else:
                deliverability = "unknown"
                exists = False
                api_score = 0.1

            print(f"Mapped: code={code}, deliverability={deliverability}, exists={exists}, api_score={api_score}")

            return {
                "email": email,
                "exists": exists,
                "deliverability": deliverability,
                "api_score": api_score,  # This is now always a float between 0.1-0.9
                "status": "success",
                "raw_response": data,
                "api_code": code,
                "api_message": message
            }

        except Exception as e:
            print(f"Error verifying {email}: {e}")
            return {"status": "error", "message": str(e)}

    # ---------------- FINAL PROBABILITY ---------------- #

    def calculate_final_probability(self, ai_confidence: float, api_result: Dict) -> float:
        if api_result.get("status") != "success":
            return round(ai_confidence * 100, 1)

        api_score = api_result.get("api_score", 0.1)  # This is now always a float

        # If MailTester says exists but gave a weak score, bump it
        if api_result.get("exists") and api_score < 0.3:
            api_score = 0.7

        final_prob = (api_score * 0.7) + (ai_confidence * 0.3)
        return round(final_prob * 100, 1)

    # ---------------- MAIN RANKING (FAST VERSION) ---------------- #

    def rank_emails(self, first_name: str, last_name: str, domain: str) -> Dict:
        print(f"Generating email variations for {first_name} {last_name} @ {domain}")
        variations = self.generate_email_variations(first_name, last_name, domain)
        results = []

        def process_email(email):
            print(f"Analyzing: {email}")
            ai_confidence = self.calculate_ai_confidence_score(email, first_name, last_name, domain)
            api_result = self.verify_with_mailtester_api(email)
            final_probability = self.calculate_final_probability(ai_confidence, api_result)

            return {
                "email": email,
                "probability": final_probability,
                "ai_confidence": ai_confidence,
                "api_score": api_result.get("api_score", 0.0),  # Always get numeric value
                "deliverability": api_result.get("deliverability", "unknown"),
                "exists": api_result.get("exists", False),
                "format_valid": True,  # Since we validated format during generation
                "mx_found": api_result.get("deliverability") in ["valid_mailbox", "risky_mailbox"],
                "smtp_check": api_result.get("exists", False)
            }

        # Run API calls in parallel (reduced workers for API rate limiting)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(process_email, email): email for email in variations}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    # Add delay between API calls to respect rate limits
                    time.sleep(1.2)
                except Exception as e:
                    email = futures[future]
                    print(f"Error checking {email}: {e}")
                    # Add fallback result for failed API calls
                    ai_confidence = self.calculate_ai_confidence_score(email, first_name, last_name, domain)
                    results.append({
                        "email": email,
                        "probability": round(ai_confidence * 100, 1),
                        "ai_confidence": ai_confidence,
                        "api_score": 0.0,
                        "deliverability": "unknown",
                        "exists": False,
                        "format_valid": True,
                        "mx_found": False,
                        "smtp_check": False
                    })

        results.sort(key=lambda x: x["probability"], reverse=True)
        return {
            "status": "success",
            "total_variations": len(results),
            "ranked_results": results,
            "best_email": results[0] if results else None,
        }


ranker = EmailRankingSystem()


# ---------------- BULK PROCESSING ---------------- #
def process_row(row, ranker):
    try:
        result = ranker.rank_emails(row["first_name"], row["last_name"], row["domain"])
        best = result.get("best_email", {})
        ranked = result.get("ranked_results", [])

        # Build rank columns
        rank_cols = {}
        for i, r in enumerate(ranked, 1):
            email = r.get("email", "")
            prob = r.get("probability", 0)
            api_score = r.get("api_score", 0)
            status = r.get("deliverability", "unknown")
            # Format API score properly - show as decimal if it's a valid score
            api_score_display = f"{api_score:.2f}" if isinstance(api_score, (int, float)) and api_score > 0 else "N/A"
            rank_cols[f"rank_{i}"] = f"{email} {prob}% AI:{r.get('ai_confidence'):.3f} API:{api_score_display} {status}"

        return {
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "domain": row["domain"],
            "best_email": best.get("email"),
            "best_probability": best.get("probability", 0),
            **rank_cols
        }

    except Exception as e:
        return {
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "domain": row["domain"],
            "best_email": None,
            "best_probability": None,
            "rank_1": f"Error: {e}"
        }

def bulk_process(file_bytes, workers=2):  # Reduced workers for API rate limiting
    df = pd.read_csv(BytesIO(file_bytes))
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_row, row.to_dict(), ranker): idx for idx, row in df.iterrows()}
        for future in as_completed(futures):
            results.append(future.result())

    out_df = pd.DataFrame(results)

    # Reorder columns
    cols = ["first_name", "last_name", "domain", "best_email", "best_probability"]
    rank_cols = sorted([c for c in out_df.columns if c.startswith("rank_")],
                       key=lambda x: int(x.split("_")[1]))
    out_df = out_df[cols + rank_cols]

    output = BytesIO()
    out_df.to_csv(output, index=False)
    return output.getvalue()


# ---------------- HTTP SERVER ---------------- #
class EmailRankingHandler(BaseHTTPRequestHandler):
    def _set_response(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
    def do_OPTIONS(self):
        self._set_response()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif parsed_path.path == "/style.css":
            self._serve_file("style.css", "text/css")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/rank_emails":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            result = ranker.rank_emails(
                data["first_name"], data["last_name"], data["domain"]
            )
            self._set_response()
            self.wfile.write(json.dumps(result).encode())

        elif self.path == "/bulk_rank":
            content_length = int(self.headers["Content-Length"])
            file_data = self.rfile.read(content_length)

            result_csv = bulk_process(file_data)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=bulk_output.csv")
            self.end_headers()
            self.wfile.write(result_csv)

        else:
            self.send_error(404)

    def _serve_file(self, filename, content_type):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self._set_response(content_type)
            self.wfile.write(content.encode())
        except FileNotFoundError:
            self.send_error(404, f"File {filename} not found")


def run_server():
    # Use 0.0.0.0 to listen on all network interfaces and read the assigned port from the environment
    port = int(os.environ.get("PORT", 8000))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, EmailRankingHandler)

    print("Email Ranking System (Web + Bulk Mode)")
    print("=" * 50)
    print(f"Server: http://localhost:{port}")
    print("Scoring: 70% API + 30% AI confidence")
    print("Supports bulk CSV upload -> download enriched CSV")
    print("=" * 50)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()


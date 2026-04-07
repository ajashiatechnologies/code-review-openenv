import random
import uuid
from datetime import datetime, timezone

# ── 25 diverse, realistic code diff templates ───────────────────────────────
# Each has: language, file_name, context, critical_module, diff,
#           additional_files, issue_types (list), severity, line_number, keywords

DIFF_TEMPLATES = [

    # ── SECURITY ────────────────────────────────────────────────────────────

    {
        "language": "python", "file_name": "auth.py",
        "context": "authentication module", "critical_module": True,
        "diff": (
            '+ query = "SELECT * FROM users WHERE name = \'" + name + "\'"\n'
            '+ cursor.execute(query)\n'
        ),
        "additional_files": [
            "# db_utils.py\ndef get_cursor():\n    return db.cursor()"
        ],
        "issue_types": ["security"], "severity": "critical",
        "line_number": 1,
        "keywords": ["sql injection", "parameterized", "prepared statement"]
    },

    {
        "language": "javascript", "file_name": "render.js",
        "context": "frontend rendering", "critical_module": False,
        "diff": (
            "+ element.innerHTML = userInput;\n"
        ),
        "additional_files": [],
        "issue_types": ["security"], "severity": "high",
        "line_number": 1,
        "keywords": ["xss", "innerHTML", "sanitize", "escape"]
    },

    {
        "language": "python", "file_name": "config.py",
        "context": "configuration loader", "critical_module": True,
        "diff": (
            '+ SECRET_KEY = "hardcoded_secret_abc123"\n'
            '+ DB_PASSWORD = "admin123"\n'
        ),
        "additional_files": [],
        "issue_types": ["security"], "severity": "critical",
        "line_number": 1,
        "keywords": ["hardcoded", "secret", "environment variable", "credential"]
    },

    {
        "language": "go", "file_name": "handler.go",
        "context": "HTTP handler", "critical_module": False,
        "diff": (
            '+ cmd := exec.Command("bash", "-c", userInput)\n'
            '+ cmd.Run()\n'
        ),
        "additional_files": [],
        "issue_types": ["security"], "severity": "critical",
        "line_number": 1,
        "keywords": ["command injection", "exec", "sanitize", "shell"]
    },

    {
        "language": "python", "file_name": "upload.py",
        "context": "file upload handler", "critical_module": False,
        "diff": (
            "+ filename = request.files['file'].filename\n"
            "+ open(os.path.join('/uploads', filename), 'wb').write(data)\n"
        ),
        "additional_files": [],
        "issue_types": ["security"], "severity": "high",
        "line_number": 1,
        "keywords": ["path traversal", "filename", "secure_filename", "validate"]
    },

    # ── BUG ─────────────────────────────────────────────────────────────────

    {
        "language": "java", "file_name": "UserService.java",
        "context": "user service", "critical_module": False,
        "diff": (
            "+ String name = user.getName();\n"
            "+ return name.toUpperCase();\n"
        ),
        "additional_files": [
            "// User.java\npublic String getName() { return this.name; } // may return null"
        ],
        "issue_types": ["bug"], "severity": "high",
        "line_number": 1,
        "keywords": ["null pointer", "NullPointerException", "null check"]
    },

    {
        "language": "python", "file_name": "parser.py",
        "context": "data parser", "critical_module": False,
        "diff": (
            "+ result = int(user_input)\n"
        ),
        "additional_files": [],
        "issue_types": ["bug"], "severity": "medium",
        "line_number": 1,
        "keywords": ["ValueError", "exception handling", "try except", "validate"]
    },

    {
        "language": "python", "file_name": "pagination.py",
        "context": "list pagination", "critical_module": False,
        "diff": (
            "+ for i in range(1, len(items)):\n"
            "+     process(items[i])\n"
        ),
        "additional_files": [],
        "issue_types": ["bug"], "severity": "medium",
        "line_number": 1,
        "keywords": ["off-by-one", "range", "index", "first element"]
    },

    {
        "language": "javascript", "file_name": "async_handler.js",
        "context": "async API handler", "critical_module": False,
        "diff": (
            "+ async function fetchData(url) {\n"
            "+     const res = await fetch(url);\n"
            "+     return res.json();\n"
            "+ }\n"
        ),
        "additional_files": [],
        "issue_types": ["bug"], "severity": "medium",
        "line_number": 1,
        "keywords": ["error handling", "try catch", "await", "rejected promise"]
    },

    {
        "language": "python", "file_name": "resource.py",
        "context": "file I/O", "critical_module": False,
        "diff": (
            "+ f = open('data.txt', 'r')\n"
            "+ data = f.read()\n"
            "+ process(data)\n"
        ),
        "additional_files": [],
        "issue_types": ["bug"], "severity": "medium",
        "line_number": 1,
        "keywords": ["file not closed", "resource leak", "context manager", "with open"]
    },

    # ── PERFORMANCE ──────────────────────────────────────────────────────────

    {
        "language": "python", "file_name": "data.py",
        "context": "data processing", "critical_module": False,
        "diff": (
            "+ for i in range(len(data)):\n"
            "+     for j in range(len(data)):\n"
            "+         compute(data[i], data[j])\n"
        ),
        "additional_files": [],
        "issue_types": ["performance"], "severity": "medium",
        "line_number": 1,
        "keywords": ["O(n^2)", "nested loop", "complexity", "vectorize"]
    },

    {
        "language": "python", "file_name": "search.py",
        "context": "search service", "critical_module": False,
        "diff": (
            "+ def find_user(user_id):\n"
            "+     for user in get_all_users_from_db():\n"
            "+         if user.id == user_id:\n"
            "+             return user\n"
        ),
        "additional_files": [],
        "issue_types": ["performance"], "severity": "high",
        "line_number": 1,
        "keywords": ["N+1", "full table scan", "index", "query optimization"]
    },

    {
        "language": "python", "file_name": "concatenate.py",
        "context": "string builder", "critical_module": False,
        "diff": (
            "+ result = ''\n"
            "+ for item in large_list:\n"
            "+     result += str(item)\n"
        ),
        "additional_files": [],
        "issue_types": ["performance"], "severity": "low",
        "line_number": 1,
        "keywords": ["string concatenation", "join", "immutable", "O(n^2) memory"]
    },

    {
        "language": "javascript", "file_name": "dom_update.js",
        "context": "UI rendering", "critical_module": False,
        "diff": (
            "+ items.forEach(item => {\n"
            "+     document.getElementById('list').innerHTML += `<li>${item}</li>`;\n"
            "+ });\n"
        ),
        "additional_files": [],
        "issue_types": ["performance"], "severity": "medium",
        "line_number": 1,
        "keywords": ["DOM reflow", "innerHTML", "DocumentFragment", "batch update"]
    },

    {
        "language": "python", "file_name": "cache.py",
        "context": "cache layer", "critical_module": False,
        "diff": (
            "+ def get_config():\n"
            "+     return json.loads(open('config.json').read())\n"
        ),
        "additional_files": [],
        "issue_types": ["performance"], "severity": "medium",
        "line_number": 1,
        "keywords": ["disk I/O", "cache", "memoize", "repeated reads"]
    },

    # ── MULTI-ISSUE ──────────────────────────────────────────────────────────

    {
        "language": "python", "file_name": "auth_query.py",
        "context": "authentication module", "critical_module": True,
        "diff": (
            '+ query = "SELECT * FROM users WHERE name = \'" + name + "\'"\n'
            "+ for i in range(len(results)):\n"
            "+     for j in range(len(results)):\n"
            "+         match(results[i], results[j])\n"
        ),
        "additional_files": [
            "# sanitizer.py\ndef sanitize(name):\n    return name.replace(\"'\", \"\")"
        ],
        "issue_types": ["security", "performance"], "severity": "critical",
        "line_number": 1,
        "keywords": ["sql injection", "nested loop", "parameterized", "O(n^2)"]
    },

    {
        "language": "python", "file_name": "api_client.py",
        "context": "external API client", "critical_module": False,
        "diff": (
            '+ API_KEY = "sk-abc123xyz"\n'
            "+ response = requests.get(url, verify=False)\n"
        ),
        "additional_files": [],
        "issue_types": ["security", "bug"], "severity": "critical",
        "line_number": 1,
        "keywords": ["hardcoded key", "SSL verification", "environment variable", "verify=True"]
    },

    {
        "language": "java", "file_name": "ReportService.java",
        "context": "report generation", "critical_module": False,
        "diff": (
            "+ List<Report> all = reportRepo.findAll();\n"
            "+ for (Report r : all) {\n"
            "+     String title = r.getTitle().toUpperCase();\n"
            "+ }\n"
        ),
        "additional_files": [],
        "issue_types": ["performance", "bug"], "severity": "high",
        "line_number": 1,
        "keywords": ["N+1", "null pointer", "findAll", "lazy loading"]
    },

    # ── STYLE ────────────────────────────────────────────────────────────────

    {
        "language": "python", "file_name": "utils.py",
        "context": "utility module", "critical_module": False,
        "diff": (
            "+ def x(a,b,c):\n"
            "+     r=a+b+c\n"
            "+     return r\n"
        ),
        "additional_files": [],
        "issue_types": ["style"], "severity": "low",
        "line_number": 1,
        "keywords": ["naming convention", "PEP8", "readability", "descriptive name"]
    },

    {
        "language": "javascript", "file_name": "helpers.js",
        "context": "helper module", "critical_module": False,
        "diff": (
            "+ var x = 1\n"
            "+ var y = 2\n"
            "+ var z = x + y\n"
        ),
        "additional_files": [],
        "issue_types": ["style"], "severity": "low",
        "line_number": 1,
        "keywords": ["var", "const", "let", "ES6", "semicolon"]
    },

    # ── NO ISSUE ─────────────────────────────────────────────────────────────

    {
        "language": "python", "file_name": "math_utils.py",
        "context": "math utilities", "critical_module": False,
        "diff": (
            "+ def add(a: int, b: int) -> int:\n"
            "+     return a + b\n"
        ),
        "additional_files": [],
        "issue_types": ["none"], "severity": "low",
        "line_number": 1,
        "keywords": []
    },

    {
        "language": "python", "file_name": "logger.py",
        "context": "logging module", "critical_module": False,
        "diff": (
            "+ import logging\n"
            "+ logger = logging.getLogger(__name__)\n"
        ),
        "additional_files": [],
        "issue_types": ["none"], "severity": "low",
        "line_number": 1,
        "keywords": []
    },

    {
        "language": "go", "file_name": "server.go",
        "context": "HTTP server", "critical_module": False,
        "diff": (
            "+ func healthCheck(w http.ResponseWriter, r *http.Request) {\n"
            '+     w.WriteHeader(http.StatusOK)\n'
            '+     fmt.Fprintln(w, "OK")\n'
            "+ }\n"
        ),
        "additional_files": [],
        "issue_types": ["none"], "severity": "low",
        "line_number": 1,
        "keywords": []
    },

    {
        "language": "java", "file_name": "Config.java",
        "context": "configuration", "critical_module": False,
        "diff": (
            "+ private static final int MAX_RETRIES = 3;\n"
            "+ private static final int TIMEOUT_MS  = 5000;\n"
        ),
        "additional_files": [],
        "issue_types": ["none"], "severity": "low",
        "line_number": 1,
        "keywords": []
    },

    # ── HARD COMBINED (multi-issue, multi-file, critical module) ────────────
    {
        "language": "python", "file_name": "payment.py",
        "context": "payment processing", "critical_module": True,
        "diff": (
            '+ query = "SELECT * FROM payments WHERE card = \'" + card_number + "\'"\n'
            "+ for txn in get_all_transactions():\n"
            "+     for check in get_all_rules():\n"
            "+         validate(txn, check)\n"
            "+ log.info(f'Processing card: {card_number}')\n"
        ),
        "additional_files": [
            "# transaction_db.py\ndef get_all_transactions():\n    return db.query('SELECT * FROM transactions')  # loads entire table",
            "# rules_engine.py\ndef get_all_rules():\n    return rules_db.findAll()"
        ],
        "issue_types": ["security", "performance", "bug"], "severity": "critical",
        "line_number": 1,
        "keywords": [
            "sql injection", "parameterized", "nested loop",
            "O(n^2)", "sensitive data", "card number", "logging", "PCI"
        ]
    },
]


def generate_code_diff(task: str = "easy") -> dict:
    """Generate a synthetic code diff seeded by task difficulty."""

    if task == "easy":
        # Easy: single-issue, non-critical, clear signal
        pool = [
            t for t in DIFF_TEMPLATES
            if len(t["issue_types"]) == 1
            and t["severity"] in ["low", "medium"]
            and not t["critical_module"]
        ]
    elif task == "medium":
        # Medium: may be multi-issue, high severity or critical module
        pool = [
            t for t in DIFF_TEMPLATES
            if t["severity"] in ["high", "critical"]
            or t["critical_module"]
        ]
    else:
        # Hard: multi-issue or multi-file context required
        pool = [
            t for t in DIFF_TEMPLATES
            if len(t["issue_types"]) > 1
            or len(t.get("additional_files", [])) > 0
            or t["critical_module"]
        ]

    # Fallback: use full pool if filtered pool is empty
    if not pool:
        pool = DIFF_TEMPLATES

    base = random.choice(pool).copy()
    base["id"]           = f"CR-{uuid.uuid4().hex[:6].upper()}"
    base["created_at"]   = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Expose ground truth separately — never mutate source template
    base["ground_truth_issues"]   = base["issue_types"]
    base["ground_truth_severity"] = base["severity"]
    base["required_keywords"]     = base["keywords"]

    return base

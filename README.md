# TechEasy Tutorials - Engineering Mathematics Portal

A full-stack Python (Flask) web application designed for Engineering Mathematics education. The platform features stream-isolated curriculum sets (**Degree B.E./B.Tech** vs. **Diploma Polytechnic**), chapter-wise MCQ practice with live **MathJax 3** formulas, an authentic **Computer-Based Testing (CBT)** examination engine, video tutorials, and a super-admin portal connected to an **online Cloud MySQL database**.

---

## 🌟 Key System Capabilities

### 🎓 1. Student Portal
- **Focused Profile Dashboard:**
  - The student home session displays a clean **Basic Student Information** card with Full Name, Student Account ID, Enrolled Course Stream, Email, Mobile Number, Enrollment Date, and Active Verification status.
  - Quick top-navigation bar for direct access to Subjects, Mock Tests, Video Tutorials, and My Test Results.
- **Stream Isolation (Degree vs. Diploma):**
  - **Diploma Students:** Access only Diploma Polytechnic Mathematics (Semesters I & II), Diploma Mock Tests, and Diploma Video Lectures.
  - **Degree Students:** Access only Degree Engineering Mathematics (I to IV), Degree Mock Tests, and Degree Video Lectures.
  - Cross-stream access via direct URL is blocked and redirected with security notifications.
- **Chapter-Wise MCQ Practice:**
  - Real-time mathematical derivations and formulas rendered via **MathJax 3** (integrals $\int f(x)dx$, partial derivatives $\frac{\partial u}{\partial x}$, matrices, etc.).
  - Detailed step-by-step mathematical explanations.
  - Interactive scorecard tracking correct, incorrect, and unattempted questions with accuracy metrics.
- **CBT Examination Engine (Computer-Based Test):**
  - Real-time countdown timer with automated submission when time expires.
  - Dynamic, color-coded question palette (*Answered*, *Unanswered*, *Marked for Review*, *Current*).
  - "Mark for Review" and "Clear Response" capabilities.
  - One-attempt enforcement per student with complete historical test records.
- **Security & Authentication:**
  - Password visibility toggle (`👁️` show/hide) on all login and registration inputs.
  - Secure password hashing via `werkzeug.security`.
  - Password reset with two-step validation (email + mobile).

---

### 🛡️ 2. Administration Portal
- **Administrative Navigation:**
  - Dedicated management tabs: **Home Overview**, **Degree Stream**, **Diploma Stream**, and **Students**.
- **Student Account Management:**
  - View registered students with instant stream-based filtering.
  - Manage student records and change enrolled streams (Diploma $\leftrightarrow$ Degree).
- **Curriculum & Question Bank Management:**
  - Create and manage subjects, chapters, and topics per course stream.
  - Question editor with **Quick-Insert Math Formula Toolbar** (integrals, fractions, square roots, matrices, greek symbols).
  - **Live MathJax LaTeX Preview** while creating questions and solutions.
  - Upload question and option diagram images.
- **Mock Test Builder & Scorecard Analytics:**
  - Build custom CBT mock test papers (stream, subject, time limit, question count).
  - Assign specific questions from the question bank.
  - View student test submissions filtered strictly by enrolled stream.
- **Video Tutorial Library:**
  - Manage YouTube lecture links with stream tagging (Degree / Diploma) and automatic thumbnail extraction.

---

## 🗄️ Database Architecture (Cloud MySQL & SQLite)

The application includes a dual-dialect database abstraction layer in [`database.py`](file:///c:/Users/vivek/OneDrive/Desktop/engineering_maths/database.py) that automatically handles parameter substitution (`?` $\leftrightarrow$ `%s`) and syntax compatibility across both engines.

- **Online Cloud Database (Active):** Connected to **Aiven Cloud MySQL** via encrypted SSL/TLS connection.
- **Local Database (Fallback):** SQLite (`engineering_maths.db`) for offline development.

### Database Tables:
| Table Name | Description |
| :--- | :--- |
| `users` | User credentials, roles (`admin` / `student`), and course streams (`Degree` / `Diploma`). |
| `subjects` | Course subjects categorized by stream and semester. |
| `chapters` | Subject chapters linked via foreign keys. |
| `topics` | Sub-topics within chapters. |
| `questions` | MCQ questions, choices, correct answers, LaTeX formulas, and explanations. |
| `tests` | Mock test paper definitions, duration, and stream assignment. |
| `test_questions` | Many-to-many mapping between test papers and questions. |
| `attempts` | Student CBT mock test submissions, scores, and percentages. |
| `attempt_answers` | Individual question responses recorded during CBT tests. |
| `test_results` | Practice session scores and evaluations. |
| `video_lectures` | Curated YouTube video lecture links and descriptions. |

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** (tested on Python 3.13)
- Installed dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Environment Configuration (`.env`)
Create a `.env` file in the root folder (or use [`.env.example`](file:///c:/Users/vivek/OneDrive/Desktop/engineering_maths/.env.example)):

```env
# Database Mode: 'mysql' for cloud database or 'sqlite' for local offline database
DB_TYPE=mysql

# Cloud MySQL Credentials (e.g. Aiven Cloud, TiDB Cloud, Railway, AWS RDS)
MYSQL_HOST=your-mysql-host.aivencloud.com
MYSQL_PORT=12087
MYSQL_USER=avnadmin
MYSQL_PASSWORD=your_password
MYSQL_DB=defaultdb
MYSQL_SSL=true

# Application Secret Key
SECRET_KEY=techeasy-engineering-maths-super-secret-key-2026
```

### 3. Utility Scripts
- **Migrate data to Cloud MySQL:**
  ```bash
  python migrate_to_mysql.py
  ```
- **Reset database (keep admin only):**
  ```bash
  python clean_database.py
  ```

### 4. Running the Server
Start the Flask application:
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Administrator Credentials

| Role | Email | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@techeasy.com` | `admin123` | `http://127.0.0.1:5000/admin/login` |

*New students can register directly through the registration form and choose their stream (Degree or Diploma).*

---

## 🧪 Automated Testing

The project includes an automated test suite covering authentication, stream isolation, CBT test taking, and database operations:

```bash
python -m unittest test_app.py
```
All **20 test cases** run against the active database configuration.

---

## 📁 Directory Structure

```
engineering_maths/
├── app.py                      # Application bootstrap, Blueprints registration, custom filters
├── config.py                   # Environment config loader (.env), MySQL / SQLite settings
├── database.py                 # Multi-dialect database abstraction (MySQL & SQLite)
├── migrate_to_mysql.py         # One-command migration tool from SQLite to Cloud MySQL
├── clean_database.py           # Database cleanup utility (keeps admin account)
├── requirements.txt            # Python dependencies (Flask, PyMySQL, Pillow, python-dotenv)
├── test_app.py                 # Automated unit and integration test suite (20 tests)
├── .env                        # Live environment configuration (git-ignored)
├── .env.example                # Example environment configuration template
├── routes/
│   ├── __init__.py             # Blueprint declarations
│   ├── auth_routes.py          # Student & admin login, registration, password recovery
│   ├── student_routes.py       # Student dashboard, practice sets, CBT engine, results
│   ├── admin_routes.py         # Admin management (Degree, Diploma, curriculum, questions)
│   └── api_routes.py           # REST endpoints for dynamic frontend dropdowns
├── static/
│   ├── css/
│   │   └── style.css           # Design system (Dark/Light mode, badges, CBT layout)
│   ├── js/
│   │   ├── main.js             # Theme toggle, password eye toggle, video modal
│   │   ├── test_runner.js      # Interactive Computer-Based Test (CBT) engine
│   │   └── admin.js            # Math toolbar, dynamic dropdowns, live LaTeX preview
│   └── uploads/
│       └── questions/          # Uploaded diagram images
└── templates/
    ├── base.html               # Main base template (navbar, footer, theme, MathJax 3)
    ├── index.html              # Clean portal gateway landing page
    ├── 404.html & 500.html     # Custom error pages
    ├── auth/                   # Login, register, and reset password templates
    ├── student/                # Student dashboard, practice, CBT test runner, results
    └── admin/                  # Dashboard, curriculum management, question bank, test builder
```

---

## 📄 License
This project is developed for educational and academic assessment purposes. All rights reserved.
#   T e c h E a s y - T u t o r i a l s - - - E n g i n e e r i n g - M a t h e m a t i c s - P o r t a l  
 
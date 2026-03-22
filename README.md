# The Bull Pen

### ROTC Battalion Management and Accountability Suite

The **Bull Pen** is a production-ready, mobile-responsive application designed to digitize and modernize Army ROTC accountability protocols. It replaces traditional manual tracking with a centralized, data-driven platform for real-time attendance, cadet performance analytics, and automated command reporting.

---

## Key Features

### 1. High-Concurrency Accountability

- **Asynchronous Batch Processing**  
  Built with Python `asyncio` to handle rapid, high-frequency attendance updates without UI freezing or database contention. Toggle-heavy workflows are queued and flushed efficiently.

- **Real-Time Dashboard**  
  Squad-based interface for managing:
  - TUE / WED / THU PT attendance
  - Leadership Lab attendance

- **Responsive UI**  
  Powered by **Flet**, enabling cross-platform (desktop + mobile) usability with a clean, fast interface.

---

### 2. Automated Command Reporting

- **PDF Report Generation**  
  Integrated `FPDF2` engine produces formal, command-ready attendance reports.

- **Embedded Data Visualization**  
  Uses `matplotlib` to generate MS-level distribution charts directly inside exported PDFs.

- **Export Capabilities**
  - CSV export
  - Excel export
  - Base64-encoded download support for portability

---

### 3. Security & Access Control

- **Password Security**  
  Uses `bcrypt` hashing for secure credential storage.

- **Role-Based Access Control (RBAC)**

| Tier   | Role          | Permissions                                                |
|--------|--------------|------------------------------------------------------------|
| Tier 1 | Admin / Staff | Full system control, database management, global reporting |
| Tier 2 | Squad Leader  | Unit-level accountability, dashboard access                |
| Tier 3 | Cadet         | Personal profile & performance tracking                    |

---

## System Architecture

| Component        | Technology                              |
|-----------------|------------------------------------------|
| Frontend        | Flet (Python-based Flutter framework)    |
| Backend         | Python (asyncio-driven)                  |
| Database        | SQLite3 (WAL mode enabled)               |
| Reporting       | Matplotlib + FPDF2                       |
| Authentication  | bcrypt                                  |

---

## Deployment (Fly.io)

This application is deployable via **Fly.io**.

### Prerequisites

- Install Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

- Authenticate:
```bash
flyctl auth login
```

### Deploy

```bash
flyctl deploy --remote-only
```

### CI/CD (GitHub Actions)

Set a secret:
- `FLY_API_TOKEN` (generated via `flyctl auth token`)

Example step:
```yaml
- name: Deploy to Fly.io
  run: flyctl deploy --remote-only
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

---

## Installation (Local Development)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/the-bull-pen.git
cd the-bull-pen
```

### 2. Install Dependencies

```bash
pip install flet bcrypt fpdf2 matplotlib
```

### 3. Initialize Database

```bash
python seed.py
```

### 4. Run Application

```bash
python main.py
```

---

## Roadmap

- Expanded cadet profiles (majors, branch preferences, emergency contacts)
- ACFT/APFT longitudinal performance tracking
- Advanced analytics dashboards
- Profile images & document storage
- University SSO integration
- Multi-battalion support

---

## Developer

**Marcus McFadden**  
Duke University  
Computer Science & Asian & Middle Eastern Studies

---

## Notes

The Bull Pen is designed with scalability, maintainability, and real-world ROTC operational efficiency in mind. The system emphasizes reliability under load, clean UI/UX, and actionable reporting for leadership.

Contributions, feature requests, and feedback are welcome.
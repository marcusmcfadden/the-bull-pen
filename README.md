# The Bull Pen

### ROTC Battalion Management and Accountability Suite

The **Bull Pen** is a mobile-responsive application designed to digitize and streamline Army ROTC accountability protocols. It replaces traditional manual tracking with a centralized, data-driven platform for real-time attendance, cadet performance analytics, and automated command reporting.

---

## Core System Functionality

### 1. High-Concurrency Accountability

* **Asynchronous Batch Processing**
  Utilizes `asyncio` flush-task logic to handle high-frequency UI updates efficiently. Rapid attendance toggles are queued and processed without database contention or UI freezing.

* **Task Organization Dashboard**
  Centralized squad-based interface for managing:

  * TUE / WED / THU PT attendance
  * Leadership Lab attendance

---

### 2. Automated Command Reporting

* **Document Generation**
  Integrated `FPDF2` engine for generating formal attendance reports.

* **Data Visualization**
  Uses `matplotlib` to embed MS-level distribution charts directly into PDF exports for immediate analysis.

* **Data Portability**
  Supports Base64-encoded exports:

  * CSV
  * Excel

---

### 3. Security and Access Control

* **Cryptographic Hashing**
  Passwords are secured using `bcrypt` to ensure data integrity and cadet privacy.

* **Role-Based Access Control (RBAC)**

  | Tier   | Role          | Permissions                                                |
  | ------ | ------------- | ---------------------------------------------------------- |
  | Tier 1 | Admin / Staff | Full system control, database management, global reporting |
  | Tier 2 | Squad Leader  | Unit-level accountability, dashboard access                |
  | Tier 3 | Cadet         | Personal profile management and performance tracking       |

---

## Technical Architecture

| Component        | Specification                          |
| ---------------- | -------------------------------------- |
| Frontend         | Flet (Python-based Flutter framework)  |
| Database         | SQLite3 with Write-Ahead Logging (WAL) |
| Async Runtime    | Python `asyncio`                       |
| Reporting Engine | Matplotlib + FPDF2                     |

---

## 🛣️ Development Roadmap

* **Expanded Cadet Profiles**
  Academic majors, branch preferences, and emergency contact integration.

* **Performance Analytics**
  Longitudinal tracking of APFT / ACFT scores with visual progress dashboards.

* **Asset Management**
  Support for profile images and digitized cadet records.

* **Authentication Integration**
  Single Sign-On (SSO) for university-level security compliance.

---

## Installation & Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/the-bull-pen.git
```

### 2. Install Dependencies

```bash
pip install flet bcrypt fpdf2 matplotlib
```

### 3. Initialize the Database

```bash
python seed.py
```

### 4. Run the Application

```bash
python main.py
```

---

## Lead Developer

**Marcus McFadden**
Duke University
Computer Science & Asian & Middle Eastern Studies

---

## Notes

This project is designed for scalability, maintainability, and real-world ROTC operational efficiency. Contributions and feature suggestions are welcome.

# MedFuse - Medical Image Fusion V2
### Final Year Production-Ready Web Application

## Overview
MedFuse is a complete web application for fusing MRI and PET medical images using Deep Learning. It includes full user authentication, a database for storing history, and a modern Dashboard UI.

## Features
- **Authentication**: Secure Login and Registration system.
- **Dashboard**: Central hub for user activity.
- **Deep Learning Fusion**: Upload MRI & PET images to generate a fused diagnostic image.
- **History Tracking**: All fusion results are saved to a SQLite database and can be viewed later.
- **Modern UI**: Clean, responsive medical-themed interface.

## Tech Stack
- **Frontend**: HTML5, CSS3, JavaScript (Fetch API)
- **Backend**: Python Flask, Flask-Login, Flask-SQLAlchemy
- **Database**: SQLite
- **AI/ML**: TensorFlow/Keras (CNN Model)

## Installation & Run Instructions

### 1. Install Requirements
Open terminal in `medical_fusion_project/backend`:
```bash
pip install -r requirements.txt
```

### 2. Start the Application
Run the `app.py` file. This will automatically update/create the database if needed.
```bash
python app.py
```

### 3. Usage
Open **http://127.0.0.1:5000** in your browser.
1. **Register** a new account.
2. **Login** with your credentials.
3. Go to **New Fusion**.
4. Upload MRI and PET images -> Click Fuse.
5. Download the result or view it in the **History** tab later.

## Folder Structure
- `backend/`
  - `app.py`: Main entry point.
  - `auth.py`: Authentication logic.
  - `models.py`: Database models (User, Fusion).
  - `database.db`: SQLite database file (auto-created).
- `frontend/`: Contains all HTML pages, CSS, and JS.

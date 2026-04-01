# 🚀 Setup Guide - BrainDump

## For first-time setup

### 1️⃣ Clone the repository Or download the ZIP file and extract it, then navigate to the project folder.
```bash
git clone [REPOSITORY-URL]
cd study-planner-project
```

### 2️⃣ Create virtual environment
```bash
python -m venv venv
```

### 3️⃣ Activate virtual environment
**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 5️⃣ Configure environment variables, if you have from zip file, you can skip this step, otherwise, create a `.env` file in the root directory of the project and add the following line:
```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Open the `.env` file and on the `SECRET_KEY` line, paste any long random text.

**Example:**
```
SECRET_KEY=my-super-secret-key-12345-xyz
```

### 6️⃣ Create the database
```bash
flask db upgrade
```

### 7️⃣ Run the application
```bash
python run.py
```

### 8️⃣ Access in browser
```
http://localhost:5000
```

---

## 🆘 Common Issues

**Error: "No module named 'flask'"**
- You forgot to activate the virtual environment
- Run: `venv\Scripts\activate`

**Error: "Could not locate a Flask application"**
- You're not in the right folder
- Run: `cd study-planner-project`

**Error running the app**
- Check if you created the `.env` file
- Check if you ran `flask db upgrade`

---

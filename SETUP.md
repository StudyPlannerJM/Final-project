# 🚀 Setup Guide - BrainDump

## For first-time setup

### 1️⃣ Clone the repository
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

### 5️⃣ Configure environment variables
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

## 🔄 For existing users updating the project

If someone made new database migrations:

```bash
git pull                      # Download updates
Remove-Item instance\*.db     # Delete old database (Windows)
# rm instance/*.db            # Delete old database (Mac/Linux)
flask db upgrade              # Create new database
python run.py                 # Run
```

**⚠️ WARNING:** You will lose local data when deleting the database.

---

## 📅 Google Calendar (Optional)

If you want to test Google Calendar integration:

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable "Google Calendar API"
4. Create OAuth 2.0 credentials
5. Download the `client_secret.json` file and place it in the root folder
6. Copy Client ID and Secret to your `.env` file

Detailed instructions are inside the `.env.example` file

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

## 📝 Files that should NEVER go to Git

- `.env` - Your secret keys
- `client_secret.json` - Google credentials
- `token.json` - Access token
- `*.db` - Your local database
- `__pycache__/` - Python cache

These files are already in `.gitignore`

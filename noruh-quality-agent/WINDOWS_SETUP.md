# Noruh Quality Agent — Windows Setup Guide

Follow every step in order. Do not skip any step.
Estimated total time: 30–60 minutes (most of that is waiting for downloads).

---

## Before you start — check your computer

This app requires:
- Windows 10 or Windows 11
- At least **8 GB of RAM** (check: Settings → System → About → Installed RAM)
- At least **15 GB of free disk space** (check: File Explorer → This PC)

If your computer does not meet these requirements, the app may crash or not install.

---

## Part 1 — Install Python

1. Open your browser and go to: **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button
3. Once downloaded, open the installer
4. **IMPORTANT:** On the first screen, tick the box that says **"Add Python to PATH"**
   (it is near the bottom of the screen — do not miss this step)
5. Click **Install Now**
6. Wait for it to finish, then click **Close**

**Verify it worked:**
1. Press the **Windows key**, type **cmd**, and press Enter — a black window opens
2. Type this and press Enter:
   ```
   python --version
   ```
3. You should see something like `Python 3.13.0`
   If you see an error, Python did not install correctly — repeat the steps above

---

## Part 2 — Install Git

1. Go to: **https://git-scm.com/download/win**
2. The download should start automatically. If not, click the link for the 64-bit version
3. Open the installer and click **Next** on every screen — the default options are all correct
4. Click **Finish** when done

---

## Part 3 — Get a GitHub access token

You need this to download the code. If you already have a token from a previous setup, you can reuse it.

1. Go to **https://github.com** and log in
2. Click your **profile picture** (top-right corner)
3. Click **Settings**
4. Scroll all the way down the left sidebar and click **Developer settings**
5. Click **Personal access tokens** → **Tokens (classic)**
6. Click **Generate new token** → **Generate new token (classic)**
7. In the **Note** field type: `windows-laptop`
8. Under **Expiration** select **No expiration**
9. Tick the box next to **repo** (the first checkbox under scopes)
10. Scroll down and click **Generate token**
11. You will see a long code starting with `ghp_` — **copy it now and save it somewhere**
    (paste it into Notepad — you cannot see it again after closing this page)

---

## Part 4 — Download the code

1. Press the **Windows key**, type **cmd**, press Enter
2. In the black window, type the following — replace `PASTE_YOUR_TOKEN_HERE` with the token you copied in Part 3:
   ```
   git clone https://PASTE_YOUR_TOKEN_HERE@github.com/lrsolano847-ux/noruh-quality-agent.git
   ```
   For example it will look like:
   ```
   git clone https://ghp_abc123xyz@github.com/lrsolano847-ux/noruh-quality-agent.git
   ```
3. Press Enter and wait for it to finish. You will see "done" when complete
4. Type this and press Enter:
   ```
   cd noruh-quality-agent
   ```
5. Verify you are in the right place by typing:
   ```
   dir
   ```
   You should see files including `setup_windows.bat` and `start_windows.bat`

---

## Part 5 — Run the setup script

1. Open **File Explorer** (the folder icon on your taskbar)
2. Navigate to: `C:\Users\YOUR_NAME\noruh-quality-agent`
   (replace YOUR_NAME with your Windows username)
3. Find the file called **setup_windows.bat**
4. **Right-click** it and select **Run as administrator**
   If Windows asks "Do you want to allow this app to make changes?" click **Yes**
5. A black window will open and begin installing packages
   - This takes **5–15 minutes** depending on your internet speed
   - You will see text scrolling — this is normal
   - If you see a red error about a package timing out, close the window and double-click **setup_windows.bat** again — it will continue from where it left off
6. When it finishes you will see the message **"Setup complete!"**
   Read the next steps printed on screen (they match Part 6 and 7 below)
7. Press any key to close the window

---

## Part 6 — Install Ollama (the AI model runner)

1. Go to: **https://ollama.com/download**
2. Click **Download for Windows**
3. Open the installer and follow the prompts
4. When it finishes, Ollama will be running in the background automatically
   (you will see a small llama icon in your system tray, near the clock)

---

## Part 7 — Download the AI models

The app uses two AI models totalling about **8 GB**. This is a one-time download.

1. Press the **Windows key**, type **cmd**, press Enter
2. Type this and press Enter (first model, ~4.7 GB):
   ```
   ollama pull qwen3-coder:7b
   ```
3. Wait for it to reach 100%, then type this and press Enter (second model, ~4.9 GB):
   ```
   ollama pull deepseek-r1:8b
   ```
4. Each download may take **15–60 minutes** depending on your internet speed.
   Do not close the window until each one says "success"

---

## Part 8 — Launch the app

1. Open **File Explorer**
2. Navigate to: `C:\Users\YOUR_NAME\noruh-quality-agent`
   (replace YOUR_NAME with your Windows username)
3. Find the file called **start_windows.bat**
4. **Double-click** it
5. A black window will open and you will see the app starting up
6. When you see the message **"You can now view your Streamlit app in your browser"**,
   open your browser and go to:
   ```
   http://localhost:8501
   ```
7. The Noruh Quality Agent dashboard will load

---

## Every time you want to use the app after the first setup

You only need to do this — everything else is already installed:

1. Open **File Explorer**
2. Navigate to: `C:\Users\YOUR_NAME\noruh-quality-agent`
3. Double-click **start_windows.bat**
4. Open your browser and go to `http://localhost:8501`

---

## Troubleshooting

**"Python was not found"** when running setup_windows.bat
→ Python is not installed or PATH was not ticked during install. Repeat Part 1.

**Setup script times out downloading a package**
→ Close the window and double-click setup_windows.bat again. It will retry.

**"Ollama not found" or Ollama offline in the app sidebar**
→ Ollama is not running. Click the Start menu, search for **Ollama**, and open it.
   Wait 10 seconds, then refresh the browser.

**App crashes or browser shows "connection refused"**
→ Close the black window and double-click start_windows.bat again.

**Screen asks "Do you want to allow this app to make changes?"**
→ Click Yes. This is Windows asking for permission to run the script.

**Windows Defender or antivirus blocks the batch file**
→ Right-click the file, select Properties, tick "Unblock" at the bottom, click OK,
   then try running it again.

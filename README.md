# SilentGram
**A Python/GnuPG terminal wrapper for secure, local PGP-encrypted Telegram communication.**

SilentGram is a lightweight terminal-based Telegram client written in Python that brings true local PGP encryption to standard chats. While Telegram's native "Secret Chats" are restricted to mobile devices, SilentGram allows you to secure any conversation using standard Telegram APIs.

**The Key Advantage**: Because encryption happens locally before the message is sent, the conversation remains completely unreadable within the official Telegram app or web interface. Anyone, including Telegram itself or someone with access to your account on another device, will see only a useless block of PGP-encrypted text. The messages can only be decrypted and read by someone using SilentGram (or a compatible GPG tool) with the correct private key.

### 🚀 How It Works

SilentGram acts as a secure layer between you and Telegram.

1. **Sending:** Before a message leaves your computer, SilentGram uses your local GPG installation to encrypt it using the recipient's Public Key. Telegram only sees (and stores) the encrypted PGP block.
2. **Receiving:** When a message arrives, SilentGram intercepts the encrypted block and uses your local Private Key to decrypt it on the fly, displaying the plain text only in your terminal.
3. **Storage:** Your keys and plain text messages are never stored on Telegram's servers.

---

## 💻 Prerequisites

You need **Python 3.7+** and **GnuPG** installed on your system.

### 1. Install GnuPG

SilentGram relies on the system's GPG binary to handle encryption.

* **macOS:**
```bash
brew install gnupg

```


* **Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install gnupg

```


* **Linux (Fedora/RedHat):**
```bash
sudo dnf install gnupg2

```



### 2. Install Python Dependencies

Run the following command to install the required Python libraries:

```bash
pip install telethon python-gnupg prompt_toolkit

```

> **⚠️ Important:** Ensure you install `python-gnupg` and **not** just `gnupg`. The latter is a different library that may cause conflicts.

---

## 🛠️ Setup & Configuration

SilentGram features an auto-setup wizard. You do not need to edit the code manually.

1. **Run the script:**
```bash
python silentgram.py

```


2. **API Configuration (First Run):**
* The script will detect that `api_config.json` is missing.
* It will ask you to enter your **API ID** and **API Hash**.
* *You can get these by logging into [my.telegram.org](https://my.telegram.org) and going to "API development tools".*


3. **PGP Key Setup:**
* The script will generate empty key files in the directory.
* **Exit the script** and open the newly created files:
* `my_private.asc`: Paste your **Private Key** block here.
* `friend_public.asc`: Paste your recipient's **Public Key** block here.


* Open `keys.json` and ensure the `target_username` is set to the correct Telegram handle (e.g., `@friend`).


4. **Launch:**
* Run `python silentgram.py` again.
* Log in with your phone number and 2FA code (if enabled).
* Start chatting securely!



---

## 🎮 Usage & Commands

Once inside the terminal, you can use the following commands:

| Command | Alias | Description |
| --- | --- | --- |
| `/help` | `/h` | Show the list of available commands. |
| `/recipient` | `/r` | Switch the active chat recipient (updates `keys.json`). |
| `/history [n]` | - | Fetch the last `n` messages (auto-decrypts). Default is 20. |
| `/encrypt on` | `/eon` | **(Default)** Enable encryption for outgoing messages. |
| `/encrypt off` | `/eof` | Disable encryption (send plain text). |
| `/panic` | - | **Emergency Wipe:** Deletes keys, configs, clears screen, and exits. |
| `/exit` | - | Quit the application safely. |

---

## 🐧 Linux Notes

* **Pinentry:** The script is configured to use `loopback` mode for GPG, which means you shouldn't need a graphical Pinentry window to enter your passphrase. It works entirely in the terminal.
* **Path Detection:** The script automatically finds the GPG binary on Linux (`/usr/bin/gpg` or similar), so no manual path configuration is required.

## ⚠️ Security Notice

* **Session Files:** The `silentgram_session` file contains your login token. **Never share or upload this file.**
* **Keys:** Your `*.asc` files contain your encryption keys. Keep them local.
* **Git:** If you fork this repository, ensure your `.gitignore` includes `keys.json`, `api_config.json`, and `*.session`.

---

**Disclaimer:** This tool is for educational and privacy-enhancing purposes. The security of the encryption depends entirely on the secrecy of your Private Keys and the security of your local machine.

'''
SilentGram
==========
A lightweight, terminal-based Telegram client that allows local PGP 
End-to-End Encryption (E2EE) on standard chats.

Version: 1.7
Author: Nat
GitHub: github.com/thegitmate
License: GNU GPLv3
Created: 7 Feb 2026
Last updated: 7 Feb 2026
'''

import os
import sys
import shutil
import json
import asyncio
import html
import gnupg
from datetime import datetime
from telethon import TelegramClient, events
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

# --- Configuration (Absolute Paths) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(SCRIPT_DIR, 'silentgram_session')
KEYS_FILE = os.path.join(SCRIPT_DIR, 'keys.json')
API_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'api_config.json') # <--- New config file
GPG_HOME = os.path.expanduser('/tmp/sg_gpg_final') 

# --- GPG Binary Detection ---
gpg_binary_path = shutil.which('gpg') or shutil.which('gpg2')
if not gpg_binary_path:
    common_paths = ['/usr/local/bin/gpg', '/opt/homebrew/bin/gpg', '/usr/bin/gpg']
    for path in common_paths:
        if os.path.exists(path):
            gpg_binary_path = path
            break

if not gpg_binary_path:
    print(f"❌ Error: Could not find 'gpg'. Please install GnuPG.")
    sys.exit(1)

# Clean Slate for GPG Home
if os.path.exists(GPG_HOME):
    shutil.rmtree(GPG_HOME)
os.makedirs(GPG_HOME, exist_ok=True)

gpg = gnupg.GPG(gnupghome=GPG_HOME, gpgbinary=gpg_binary_path)

style = Style.from_dict({
    'user': '#888888',       # Gray 
    'sent': "#11ba11",       # Dark Green
    'error': '#ff0000',      # Red
    'system': "#d5d518",     # Dark Yellow
    'plain': "#dedede",      # Light Gray
    'info': "#0bcece",       # Blue
})

# --- Helper Function for API Keys ---
def get_api_credentials():
    if not os.path.exists(API_CONFIG_FILE):
        print_formatted_text(HTML("<system>⚠️ api_config.json not found.</system>"), style=style)
        print_formatted_text(HTML("<info>ℹ️  To get your Telegram API keys:</info>"), style=style)
        print_formatted_text(HTML("<info>   1. Log in to https://my.telegram.org</info>"), style=style)
        print_formatted_text(HTML("<info>   2. Go to 'API development tools'</info>"), style=style)
        print_formatted_text(HTML("<info>   3. Create a new application (any name works)</info>"), style=style)
        print("")
        
        print("Please enter your API_ID: ", end="", flush=True)
        api_id = sys.stdin.readline().strip()
        print("Please enter your API_HASH: ", end="", flush=True)
        api_hash = sys.stdin.readline().strip()
        
        if not api_id or not api_hash:
             print_formatted_text(HTML("<error>❌ API credentials cannot be empty. Exiting.</error>"), style=style)
             sys.exit(1)

        data = {"api_id": api_id, "api_hash": api_hash}
        try:
            with open(API_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            print_formatted_text(HTML(f"<system>✅ Saved API credentials to {API_CONFIG_FILE}</system>"), style=style)
            return api_id, api_hash
        except Exception as e:
            print_formatted_text(HTML(f"<error>❌ Failed to write config file: {e}</error>"), style=style)
            sys.exit(1)
    else:
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                return data['api_id'], data['api_hash']
        except Exception as e:
            print_formatted_text(HTML(f"<error>❌ Error reading api_config.json: {e}</error>"), style=style)
            print_formatted_text(HTML(f"<error>Please check the file or delete it to reset.</error>"), style=style)
            sys.exit(1)

# --- Helper Class to Track State ---
class ChatSession:
    def __init__(self, entity):
        self.entity = entity

class PGPEngine:
    def __init__(self):
        self.target_fingerprint = None
        self.passphrase = None
        self.default_username = None
        self.check_and_create_files()
        self.load_keys()

    def check_and_create_files(self):
        if not os.path.exists(KEYS_FILE):
            print_formatted_text(HTML(f"<system>⚠️ {KEYS_FILE} not found. Creating default configuration...</system>"), style=style)
            
            default_config = {
                "my_private_key": "my_private.asc",
                "my_private_key_passphrase": "",
                "friends_public_key": "friend_public.asc",
                "target_username": ""
            }
            
            with open(KEYS_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)

            priv_key_path = os.path.join(SCRIPT_DIR, "my_private.asc")
            pub_key_path = os.path.join(SCRIPT_DIR, "friend_public.asc")

            if not os.path.exists(priv_key_path):
                with open(priv_key_path, "w") as f:
                    f.write("") 
                print_formatted_text(HTML(f"<info>   Created empty file: my_private.asc</info>"), style=style)

            if not os.path.exists(pub_key_path):
                with open(pub_key_path, "w") as f:
                    f.write("") 
                print_formatted_text(HTML(f"<info>   Created empty file: friend_public.asc</info>"), style=style)

            print_formatted_text(HTML("<error>❌ Configuration created. Please fill 'my_private.asc', 'friend_public.asc', and check 'keys.json'. Then run the script again.</error>"), style=style)
            sys.exit(0)

    def load_keys(self):
        try:
            print_formatted_text(HTML("<system>📂 Reading configuration...</system>"), style=style)
            with open(KEYS_FILE, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print_formatted_text(HTML("<error>❌ keys.json is corrupted or empty. Please fix or delete it.</error>"), style=style)
                    sys.exit(1)
            
            def resolve_path(p):
                return p if os.path.isabs(p) else os.path.join(SCRIPT_DIR, p)

            priv_path = resolve_path(data['my_private_key'])
            pub_path = resolve_path(data['friends_public_key'])

            # Load Private Key
            print_formatted_text(HTML(f"<user>   > Loading Private Key: {priv_path}</user>"), style=style)
            try:
                with open(priv_path, 'r') as key_file:
                    key_data = key_file.read()
                    if not key_data.strip():
                         print_formatted_text(HTML(f"<error>❌ Error: {priv_path} is empty!</error>"), style=style)
                         sys.exit(1)
                    import_result = gpg.import_keys(key_data)
            except FileNotFoundError:
                print_formatted_text(HTML(f"<error>❌ Error: File '{priv_path}' not found.</error>"), style=style)
                sys.exit(1)
            
            if not import_result.fingerprints:
                print_formatted_text(HTML("<error>❌ Failed to import Private Key! (Invalid format or corrupted)</error>"), style=style)
                sys.exit(1)

            my_fp = import_result.fingerprints[0]
            my_id = gpg.list_keys(keys=[my_fp])[0]['uids'][0]
            print_formatted_text(HTML(f"<info>   ✅ Loaded Identity: {my_id}</info>"), style=style)

            self.passphrase = data.get('my_private_key_passphrase', '')

            # Load Friend's Key
            print_formatted_text(HTML(f"<user>   > Loading Friend's Key: {pub_path}</user>"), style=style)
            try:
                with open(pub_path, 'r') as key_file:
                    key_data = key_file.read()
                    if not key_data.strip():
                         print_formatted_text(HTML(f"<error>❌ Error: {pub_path} is empty!</error>"), style=style)
                         sys.exit(1)
                    import_result = gpg.import_keys(key_data)
            except FileNotFoundError:
                print_formatted_text(HTML(f"<error>❌ Error: File '{pub_path}' not found.</error>"), style=style)
                sys.exit(1)
            
            if not import_result.fingerprints:
                print_formatted_text(HTML("<error>❌ Failed to import Public Key! (Invalid format or corrupted)</error>"), style=style)
                sys.exit(1)

            self.target_fingerprint = import_result.fingerprints[0]
            friend_id = gpg.list_keys(keys=[self.target_fingerprint])[0]['uids'][0]
            print_formatted_text(HTML(f"<info>   ✅ Loaded Friend: {friend_id}</info>"), style=style)

            gpg.trust_keys([self.target_fingerprint], 'TRUST_ULTIMATE')
            
            self.default_username = data.get('target_username')
            if self.default_username == "":
                self.default_username = None

            print_formatted_text(HTML("<system>🚀 System Ready.</system>"), style=style)

        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            sys.exit(1)

    def encrypt(self, message):
        encrypted_data = gpg.encrypt(message, self.target_fingerprint, always_trust=True)
        if encrypted_data.ok:
            return str(encrypted_data)
        else:
            return f"[Encryption Error: {encrypted_data.status}]"

    def decrypt(self, encrypted_message):
        decrypted_data = gpg.decrypt(
            encrypted_message, 
            passphrase=self.passphrase,
            extra_args=['--pinentry-mode', 'loopback'] 
        )
        return str(decrypted_data) if decrypted_data.ok else f"DECRYPTION_FAILED: {decrypted_data.stderr}"

async def main():
    # 1. Load API Keys first
    api_id, api_hash = get_api_credentials()

    pgp = PGPEngine()
    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    
    await client.start()

    # --- SETUP PHASE ---
    current_chat = None 
    target_user = pgp.default_username
    encryption_enabled = True 
    
    if not target_user:
        print_formatted_text(HTML("<system>⚠️ No 'target_username' found in keys.json.</system>"), style=style)
        
        while not target_user:
             print("Please enter the recipient username (e.g. @friend): ", end="", flush=True)
             target_user = sys.stdin.readline().strip()
             
             if not target_user:
                 print("Username cannot be empty.")

        try:
            with open(KEYS_FILE, 'r') as f:
                config_data = json.load(f)
            config_data['target_username'] = target_user
            with open(KEYS_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
            print_formatted_text(HTML(f"<system>💾 Saved '{target_user}' to {KEYS_FILE}</system>"), style=style)
        except Exception as e:
             print_formatted_text(HTML(f"<error>⚠️ Failed to save recipient to JSON: {e}</error>"), style=style)

    try:
        initial_entity = await client.get_entity(target_user)
        print_formatted_text(HTML(f"<system>--- Chatting with {initial_entity.first_name} ---</system>"), style=style)
        current_chat = ChatSession(initial_entity)
    except Exception as e:
        print_formatted_text(HTML(f"<error>❌ Connection error: Could not find user '{target_user}'. Error: {e}</error>"), style=style)
        print_formatted_text(HTML(f"<error>Please check the username and restart, or use /recipient to switch.</error>"), style=style)

    # --- CHAT PHASE ---
    session = PromptSession()

    @client.on(events.NewMessage())
    async def handler(event):
        if not current_chat or event.chat_id != current_chat.entity.id:
            return

        with patch_stdout():
            raw_text = event.raw_text
            # Get local time from event
            time_str = event.date.astimezone().strftime('%H:%M')
            
            if "BEGIN PGP MESSAGE" in raw_text:
                decrypted = pgp.decrypt(raw_text)
                if "DECRYPTION_FAILED" in decrypted:
                    if not event.out:
                        label = f"[{time_str}] [{current_chat.entity.first_name}]"
                        safe_err = html.escape(str(decrypted))
                        print_formatted_text(HTML(f"<error>{label} 🔒 Error: {safe_err}</error>"), style=style)
                else:
                    safe_decrypted = html.escape(str(decrypted))
                    if event.out:
                        print_formatted_text(HTML(f"<sent>[{time_str}] [You] verified: {safe_decrypted}</sent>"), style=style)
                    else:
                        print_formatted_text(HTML(f"<user>[{time_str}] [{current_chat.entity.first_name}] decrypted: {safe_decrypted}</user>"), style=style)
            else:
                label = f"[{time_str}] [You]" if event.out else f"[{time_str}] [{current_chat.entity.first_name}]"
                safe_raw = html.escape(str(raw_text))
                print_formatted_text(HTML(f"<plain>{label}: {safe_raw}</plain>"), style=style)

    print("Use /help to see the list of commands and /exit to quit.")
    
    while True:
        try:
            with patch_stdout():
                status_char = "🔒" if encryption_enabled else "🔓"
                msg = await session.prompt_async(HTML(f"<b>You {status_char}: </b>"))

            cmd = msg.strip().split()
            msg_clean = msg.strip()
            
            if msg_clean in ['/exit', '--exit']:
                break
            
            elif msg_clean in ['/help', '/h']:
                help_text = """
<system>Available Commands:
/help, /h           : Show this list of commands.
/recipient, /r      : Change the recipient (e.g. /r @username).
/encrypt off, /eof  : Turn OFF encryption (send plain text).
/encrypt on, /eon   : Turn ON encryption.
/history [n]        : Show last n messages (max 50, default 20).
/panic              : Wipe keys, clear screen, and exit immediately.
/exit               : Quit the application.</system>
"""
                print_formatted_text(HTML(help_text), style=style)

            elif msg_clean == '/panic':
                with patch_stdout():
                    confirm = await session.prompt_async(HTML("<error>⚠️  CONFIRM PANIC WIPE? (y/n): </error>"))
                
                if confirm.lower().strip() == 'y':
                    try:
                        open(KEYS_FILE, 'w').close()
                        open(API_CONFIG_FILE, 'w').close() # Wiping API config too
                        open(os.path.join(SCRIPT_DIR, "my_private.asc"), 'w').close()
                        open(os.path.join(SCRIPT_DIR, "friend_public.asc"), 'w').close()
                        os.system('cls' if os.name == 'nt' else 'clear')
                        sys.exit(0)
                    except Exception as e:
                        print_formatted_text(HTML(f"<error>❌ Panic failed: {e}</error>"), style=style)

            elif msg_clean.startswith('/recipient') or msg_clean.startswith('/r '):
                new_username = None
                if len(cmd) > 1:
                    new_username = cmd[1]
                else:
                    with patch_stdout():
                        new_username = await session.prompt_async(HTML("<system>Enter new username (e.g. @friendlyuser): </system>"))
                
                if new_username:
                    try:
                        print_formatted_text(HTML(f"<system>🔍 Searching for {new_username}...</system>"), style=style)
                        new_entity = await client.get_entity(new_username)
                        current_chat = ChatSession(new_entity) 
                        print_formatted_text(HTML(f"<system>✅ Switched chat to: {new_entity.first_name}</system>"), style=style)
                        
                        try:
                            with open(KEYS_FILE, 'r') as f:
                                config_data = json.load(f)
                            config_data['target_username'] = new_username
                            with open(KEYS_FILE, 'w') as f:
                                json.dump(config_data, f, indent=4) 
                            print_formatted_text(HTML(f"<system>💾 Updated 'target_username' in {KEYS_FILE}</system>"), style=style)
                        except Exception as file_err:
                            print_formatted_text(HTML(f"<error>⚠️ Chat switched, but failed to update JSON: {file_err}</error>"), style=style)
                    except Exception as e:
                        print_formatted_text(HTML(f"<error>❌ Could not find user: {e}</error>"), style=style)

            elif msg_clean.startswith('/history'):
                limit = 20
                if len(cmd) > 1 and cmd[1].isdigit():
                    limit = min(int(cmd[1]), 50) 
                
                if current_chat:
                    print_formatted_text(HTML(f"<system>⏳ Fetching last {limit} messages...</system>"), style=style)
                    try:
                        history_msgs = await client.get_messages(current_chat.entity, limit=limit)
                        
                        print_formatted_text(HTML(f"<system>--- History ({limit}) ---</system>"), style=style)
                        
                        for message in reversed(history_msgs):
                            time_str = message.date.astimezone().strftime('%H:%M')
                            sender_label = f"[{time_str}] [You]" if message.out else f"[{time_str}] [{current_chat.entity.first_name}]"
                            content = ""

                            if message.file:
                                file_name = "file"
                                # Check if 'document' exists and has 'attributes' before accessing
                                if hasattr(message.file, 'name') and message.file.name:
                                    file_name = message.file.name
                                elif message.document and hasattr(message.document, 'attributes'):
                                    for attr in message.document.attributes:
                                        if hasattr(attr, 'file_name') and attr.file_name:
                                            file_name = attr.file_name
                                content = f"[{file_name}]"
                            
                            elif message.text:
                                if "BEGIN PGP MESSAGE" in message.text:
                                    decrypted = pgp.decrypt(message.text)
                                    if "DECRYPTION_FAILED" in decrypted:
                                        content = f"<error>🔒 [PGP Error]</error>"
                                    else:
                                        content = f"<info>{html.escape(str(decrypted))}</info>"
                                else:
                                    content = html.escape(str(message.text))
                            
                            elif message.action:
                                # New check for Calls
                                if "PhoneCall" in type(message.action).__name__:
                                    content = "[Call]"

                            if message.out:
                                print_formatted_text(HTML(f"<sent>{sender_label}: {content}</sent>"), style=style)
                            else:
                                print_formatted_text(HTML(f"<user>{sender_label}: {content}</user>"), style=style)
                                
                        print_formatted_text(HTML(f"<system>--- End of History ---</system>"), style=style)
                    except Exception as e:
                         print_formatted_text(HTML(f"<error>❌ Error fetching history: {e}</error>"), style=style)

                else:
                    print_formatted_text(HTML(f"<error>❌ No active chat.</error>"), style=style)

            elif msg_clean in ['/encrypt off', '/eof']:
                encryption_enabled = False
                print_formatted_text(HTML("<system>🔓 Encryption DISABLED. Sending plain text.</system>"), style=style)
            
            elif msg_clean in ['/encrypt on', '/eon']:
                encryption_enabled = True
                print_formatted_text(HTML("<system>🔒 Encryption ENABLED.</system>"), style=style)

            elif msg_clean:
                if current_chat:
                    now_str = datetime.now().strftime('%H:%M')
                    if encryption_enabled:
                        ciphertext = pgp.encrypt(msg_clean)
                        await client.send_message(current_chat.entity, ciphertext)
                        with patch_stdout():
                            safe_msg = html.escape(msg_clean)
                            print_formatted_text(HTML(f"<sent>[{now_str}] [You] encrypted: {safe_msg}</sent>"), style=style)
                    else:
                        await client.send_message(current_chat.entity, msg_clean)
                        with patch_stdout():
                            safe_msg = html.escape(msg_clean)
                            print_formatted_text(HTML(f"<plain>[{now_str}] [You]: {safe_msg}</plain>"), style=style)
                else:
                     print_formatted_text(HTML(f"<error>❌ No recipient selected! Use /r to set one.</error>"), style=style)
                
        except (KeyboardInterrupt, EOFError):
            break

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

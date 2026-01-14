import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3


# Server Connection Details
SERVER_IP = '127.0.0.1' # Localhost (change this if server is on another machine)
SERVER_PORT = 4000

class ChatApp:
    def __init__(self,root):
        self.root = root
        self.client_socket = None
        self.recipient = None
        self.username = ""

        self.db=DatabaseManager()

        self.setup_window()
        self.load_theme()

        self.create_login_ui()
        self.create_chat_ui()

        self.show_login_frame()

    def setup_window(self):
        self.root.title("Chat App")
        self.root.geometry("850x650")
        self.root.configure(bg="#121b22")

    def load_theme(self):
        self.root.tk.call('source', 'forest-dark.tcl')
        ttk.Style().theme_use('forest-dark')

    def create_login_ui(self):
        self.login_frame = ttk.Frame(self.root)

        self.lbl_instruction = ttk.Label(self.login_frame, text="Welcome! Please Log In:", font=("Arial", 16))
        self.lbl_instruction.pack(pady=20)

        self.name_entry = ttk.Entry(self.login_frame, font=("Arial", 12))
        self.name_entry.pack(pady=10, ipadx=10, ipady=5)
        self.name_entry.bind('<Return>', self.connect_and_login)

        btn=ttk.Button(self.login_frame, text="Enter Chat", style="Accent.TButton", command=self.connect_and_login)
        btn.pack(pady=20, fill='x')

    def create_chat_ui(self):
        self.chat_frame = tk.Frame(self.root, bg="#121b22")

        self.sidebar = tk.Frame(self.chat_frame, width=250, bg="#202c33")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="Contacts", background="#202c33", foreground="white", font=("Arial", 12)).pack(pady=10)
        self.contacts = ttk.Treeview(self.sidebar, columns=("Username"), show="headings",selectmode="browse")
        self.contacts.heading("Username", text="Online Users")
        self.contacts.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.contacts.bind("<<TreeviewSelect>>", self.on_contact_click)

        self.message_alert_label = ttk.Label(self.sidebar, text="", background="#202c33", foreground="red", font=("Arial", 10))
        self.message_alert_label.pack(pady=5)

        self.alert_clear_button = ttk.Button(self.sidebar, text="Clear Alert", command=lambda: self.message_alert_label.config(text=""))
        self.alert_clear_button.pack(pady=5)

        self.main_area = tk.Frame(self.chat_frame, bg="#0b141a")
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header_frame = tk.Frame(self.main_area, bg="#202c33", height=50)
        self.header_frame.pack(fill="x")
        self.chat_label = tk.Label(self.header_frame, text="Select a user...", bg="#202c33", fg="white",font=("Arial", 12))
        self.chat_label.pack(pady=10)

        self.chat_history = scrolledtext.ScrolledText(self.main_area, state='disabled', bg="#0b141a", fg="white")
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_history.tag_config('me', justify='right', foreground='#00ff00')
        self.chat_history.tag_config('other', justify='left', foreground='#ffffff')

        input_area = tk.Frame(self.main_area, bg="#202c33", height=60)
        input_area.pack(fill="x",side="bottom")

        self.msg_entry = ttk.Entry(input_area, font=("Arial", 11))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        self.msg_entry.bind("<Return>", self.send_message)

        send_button = ttk.Button(input_area, text="Send",style="Accent.TButton",command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=10)

    def show_login_frame(self):
        self.chat_frame.pack_forget()
        self.login_frame.pack(expand=True)

    def show_chat_frame(self):
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill='both', expand=True)

    def connect_and_login(self,event=None):
        # Create a TCP/IP socket
        username=self.name_entry.get()
        if not username:
            messagebox.showwarning("Input Error", "Please enter a username.")
            return
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to the server
            self.client_socket.connect((SERVER_IP, SERVER_PORT))

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            root.destroy()
        # Registration Phase
        try:
            # Receive welcome message
            welcome_msg = self.client_socket.recv(1024).decode('utf-8')
            print(f"[Server]: {welcome_msg}")
            # Send username
            self.username = username
            self.client_socket.send(username.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Error", "Failed during login phase")
            self.client_socket.close()
        self.show_chat_frame()
        self.root.title(f"Chat App - Logged in as: {self.username}")

        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.daemon = True  # Thread ends when main program ends
        receive_thread.start()

    def update_contact_list(self, new_contact):
        existing_names = {self.contacts.item(item)['values'][0] for item in self.contacts.get_children()}
        names = new_contact.split(",")
        for contact in names:
            contact = contact.strip()
            if contact == self.username:
                continue  # Skip adding self to contact list
            if contact and contact not in existing_names:  # Avoid adding empty names or duplicates
                self.contacts.insert("", tk.END, values=(contact,))
        print(f"[DEBUG CONTACT LIST UPDATED]: {new_contact}")

    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                print(f"[DEBUG RAW MSG]: {msg}")
                if not msg:
                    break
                if msg.startswith("[Server]:") and "Username already taken" in msg:
                    msg = msg.replace("[Server]:", "").strip()
                    messagebox.showerror("Login Error", msg)
                    self.client_socket.close()
                    self.root.destroy()
                    return

                if msg.startswith("CONTACTS:"):
                    print(">> Updating contact list...")
                    print(f"[DEBUG USERNAME]: {self.username}")
                    contact_data = msg.replace("CONTACTS:", "").strip()
                    print(f"[DEBUG CONTACT DATA]: {contact_data}")

                    self.update_contact_list(contact_data)

                else:
                    if ":" in msg:
                        sender,content = msg.split(":",1)
                        sender = sender.strip()
                        content = content.strip()
                        self.db.save_message(sender,self.username,content)

                        if self.recipient == sender:
                            self.chat_history.config(state='normal')
                            self.chat_history.insert(tk.END, f"{content}\n","other")
                            self.chat_history.see(tk.END)
                            self.chat_history.config(state='disabled')
                        else:
                            print(f"[NEW MSG] Saved from {sender}, but chat not open.")
                            self.message_alert_label.config(text=f"New message from {sender}!")
            except:
                break

    def send_message(self,event=None):
        msg = self.msg_entry.get()
        if not msg:
            return
        if not self.recipient:
            messagebox.showwarning("Error", "Please select a user from the list first!")
            return
        try:
            final_msg = f"{self.recipient}:{msg}"
            print(f"[DEBUG SENDING MSG]: {final_msg}")
            self.client_socket.send(final_msg.encode('utf-8'))

            self.db.save_message(self.username,self.recipient,msg)

            self.chat_history.config(state='normal')
            self.chat_history.insert(tk.END, f"{msg}\n","me")
            self.chat_history.see(tk.END)
            self.chat_history.config(state='disabled')

            self.msg_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send: {e}")

    def on_contact_click(self, event):
        selected_item = self.contacts.selection()
        if selected_item:
            item_data = self.contacts.item(selected_item)
            clicked_name = item_data['values'][0]
            self.recipient = clicked_name
            print(f"Opening chat with: {self.recipient}")
            self.chat_label.config(text=f"Chat with: {self.recipient}", fg="#00ff00")

            self.load_history_from_db(self.recipient)
    def load_history_from_db(self, other_user):
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, tk.END)

        rows=self.db.get_chat_history(self.username, other_user)

        for sender ,msg in rows:
            if sender==self.username:
                self.chat_history.insert(tk.END, f"{msg}\n","me")
            else:
                self.chat_history.insert(tk.END, f"{msg}\n","other")
            self.chat_history.see(tk.END)
            self.chat_history.config(state='disabled')

class DatabaseManager:
    """ Class to manage SQLite database operations for chat history."""
    def __init__(self, db_name="chat_history.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()
        self.connection.commit()

    def create_table(self):
        cursor=self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                sender TEXT,
                receiver TEXT,
                message TEXT
            )
        ''')
        self.connection.commit()
        cursor.close()

    def save_message(self, sender, receiver, message):
        try:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO messages VALUES (?, ?, ?)", (sender, receiver, message))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"DB Save Error: {e}")
    def get_chat_history(self, user1 ,user2):
        try:
            cursor = self.connection.cursor()
            cursor.execute(''' SELECT sender, message FROM messages WHERE (sender= ? AND receiver=?) OR (sender=? AND receiver=?) ''', (user1, user2, user2, user1))
            rows=cursor.fetchall()
            cursor.close()
            return rows
        except Exception as e:
            print(f"DB Fetch Error: {e}")
            return []
    def close(self):
        self.connection.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()


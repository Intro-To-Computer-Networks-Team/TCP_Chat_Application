import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import os
from datetime import datetime

# Server Connection Details
SERVER_IP = '127.0.0.1' # Localhost (change this if server is on another machine)
SERVER_PORT = 4000

class ChatApp:
    def __init__(self,root):
        self.root = root
        self.client_socket = None
        self.recipient = None
        self.username = ""
        self.unread_messages = {}

        self.db=DatabaseManager()

        self.setup_window()
        self.load_theme()

        self.create_login_ui()
        self.create_chat_ui()

        self.show_login_frame()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """ Handle application closure."""
        try:
            # Close socket and database connection
            if self.client_socket:
                self.client_socket.close()
            self.db.close()
        except Exception as e:
            print(f"Error closing connections: {e}")

        self.root.destroy()
        # Delete the database file on exit
        try:
            if os.path.exists("chat_history.db"):
                os.remove("chat_history.db")
        except Exception as e:
            print(f"Error deleting database file: {e}")


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
        """ Main chat UI frame."""
        self.chat_frame = tk.Frame(self.root, bg="#121b22")
        """ Sidebar for contacts and main chat area."""
        self.sidebar = tk.Frame(self.chat_frame, width=250, bg="#202c33")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="Contacts", background="#202c33", foreground="white", font=("Arial", 12)).pack(pady=10)
        self.contacts = ttk.Treeview(self.sidebar, columns=("Username","Alerts"), show="headings",selectmode="browse")
        self.contacts.heading("Username", text="Online Users")
        self.contacts.heading("Alerts", text="New Msgs")

        self.contacts.column("Username", width=160, anchor=tk.W)
        self.contacts.column("Alerts", width=80, anchor=tk.CENTER)
        self.contacts.tag_configure('msg_alert', foreground='#ff4444')

        self.contacts.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.contacts.bind("<<TreeviewSelect>>", self.on_contact_click)

        self.main_area = tk.Frame(self.chat_frame, bg="#0b141a")
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header_frame = tk.Frame(self.main_area, bg="#202c33", height=50)
        self.header_frame.pack(fill="x")
        self.chat_label = tk.Label(self.header_frame, text="Select a user...", bg="#202c33", fg="white",font=("Arial", 12))
        self.chat_label.pack(pady=10)
        """ Chat history area."""
        self.chat_history = scrolledtext.ScrolledText(self.main_area, state='disabled', bg="#0b141a", fg="white")
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_history.tag_config('me', justify='right', foreground='#00ff00')
        self.chat_history.tag_config('other', justify='left', foreground='#ffffff')
        self.chat_history.tag_config("time_tag", foreground="gray", font=("Arial", 8))


        input_area = tk.Frame(self.main_area, bg="#202c33", height=60)
        input_area.pack(fill="x",side="bottom")

        self.msg_entry = ttk.Entry(input_area, font=("Arial", 11))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        self.msg_entry.bind("<Return>", self.send_message)

        send_button = ttk.Button(input_area, text="Send",style="Accent.TButton",command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=10)

    def show_login_frame(self):
        """ Display the login frame and hide the chat frame."""
        self.chat_frame.pack_forget()
        self.login_frame.pack(expand=True)

    def show_chat_frame(self):
        """ Display the chat frame and hide the login frame."""
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
        """ Update the contact list in the UI."""
        existing_names = {self.contacts.item(item)['values'][0] for item in self.contacts.get_children()}
        names = new_contact.split(",")
        for contact in names:
            contact = contact.strip()
            if contact == self.username:
                continue  # Skip adding self to contact list
            if contact and contact not in existing_names:  # Avoid adding empty names or duplicates
                self.unread_messages[contact] = 0
                self.contacts.insert("", tk.END, values=(contact,))
        print(f"[DEBUG CONTACT LIST UPDATED]: {new_contact}")

    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                print(f"[DEBUG RAW MSG]: {msg}")
                if not msg:
                    break
                #Receive messages from the server.
                if msg.startswith("[Server]:"):
                    print (f"[SERVER MSG]: {msg}")
                    print(f"[DEBUG USERNAME]: {self.recipient}")
                    if msg == f"[Server]: User '{self.recipient}' not found.":
                        messagebox.showerror("Error", "User not found")
                        self.recipient = None
                        self.chat_label.config(text="Select a user...", fg="white")
                    if  msg == f"[Server]: Username already taken. Disconnecting.":
                        msg = msg.replace("[Server]:", "").strip()
                        messagebox.showerror("Login Error", msg)
                        self.client_socket.close()
                        self.root.destroy()
                        return
                #Update contact list if message starts with CONTACTS:
                if msg.startswith("CONTACTS:"):
                    print(">> Updating contact list...")
                    print(f"[DEBUG USERNAME]: {self.username}")
                    contact_data = msg.replace("CONTACTS:", "").strip()
                    print(f"[DEBUG CONTACT DATA]: {contact_data}")

                    self.update_contact_list(contact_data)
                #Handle regular messages
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
                        # If chat with sender is not open, show alert
                        else:
                            print(f"[NEW MSG] Saved from {sender}, but chat not open.")
                            self.unread_messages[sender] = self.unread_messages.get(sender, 0) + 1
                            self.update_unread_alerts()

            except:
                break

    def update_unread_alerts(self):
        """ Update unread message alerts in the contact list."""
        for item in self.contacts.get_children():
            item_data = self.contacts.item(item)
            name = item_data['values'][0]
            if name in self.unread_messages:
                alert_count = self.unread_messages[name]
                self.contacts.set(item, "Alerts", f"{alert_count} New" if alert_count > 0 else "")
                if alert_count > 0:
                    self.contacts.item(item, tags=('msg_alert',))
                else:
                    self.contacts.item(item, tags=())
            else:
                self.contacts.set(item, "Alerts", "")
                self.contacts.item(item, tags=())

    def send_message(self,event=None):
        """ Send message to the selected recipient."""
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
        """ Handle contact selection from the contact list."""
        selected_item = self.contacts.selection()
        if selected_item:
            item_data = self.contacts.item(selected_item)
            clicked_name = item_data['values'][0]
            if self.recipient == clicked_name:
                return  # Already chatting with this user

            self.recipient = clicked_name
            self.chat_label.config(text=f"Chat with: {self.recipient}", fg="#00ff00")
            # Clear unread messages for this contact
            if clicked_name in self.unread_messages:
                del self.unread_messages[clicked_name]
                self.update_unread_alerts()
            # Load chat history from the database
            self.load_history_from_db(clicked_name)
            self.chat_history.config(state='normal')



    def load_history_from_db(self, other_user):
        """ Load chat history from the database and display it in the chat history area."""
        print(f"--- Loading history for {other_user} ---")
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, 'end')

        rows=self.db.get_chat_history(self.username, other_user)

        for sender ,msg,timestamp in rows:
            if sender==self.username:
                self.chat_history.insert(tk.END, f"{msg}\n","me")
            else:
                self.chat_history.insert(tk.END, f"{msg}\n","other")
            self.chat_history.insert(tk.END, f"{timestamp}\n","time_tag")

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
                message TEXT,
                timestamp TEXT
            )
        ''')
        self.connection.commit()
        cursor.close()

    def save_message(self, sender, receiver, message):
        try:
            timestamp = datetime.now().strftime("%H:%M")
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO messages VALUES (?, ?, ?,?)", (sender, receiver, message, timestamp))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"DB Save Error: {e}")
    def get_chat_history(self, user1 ,user2):
        try:
            cursor = self.connection.cursor()
            cursor.execute(''' SELECT sender, message,timestamp FROM messages WHERE (sender= ? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY timestamp ASC ''', (user1, user2, user2, user1))
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


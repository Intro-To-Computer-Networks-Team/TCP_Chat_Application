import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import os
from datetime import datetime
import time
#Custom tkinter theme 
import customtkinter as ctk
# Server Connection Details
SERVER_IP = '127.0.0.1' # Localhost (change this if server is on another machine)
SERVER_PORT = 4000

class ChatApp:
    """Main GUI application for the chat client."""

    def __init__(self,root):
        """Initialize the chat application with UI components and database."""
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
        # Delete the database file after all chats with the client are closed (to ensure no locks remain)
        try:
            time.sleep(0.5) # Wait briefly to ensure all connections are closed
            if os.path.exists("chat_history.db"):
                os.remove("chat_history.db")
        except Exception as e:
            print(f"Error deleting database file: {e}")

    # ==================== UI SETUP ====================
    def setup_window(self):
        """Configure main window size and appearance."""
        self.root.title("Chat App")
        self.root.geometry("850x650")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, "assets", "logo.png")
        try:
            icon_img = tk.PhotoImage(file=image_path)
            self.root.iconphoto(True, icon_img)
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")

        #Backgroud color 
        self.root.configure(bg="#131417")

    def load_theme(self):
        # Load the theme file relative to this script's directory so it works
        # regardless of the current working directory when the script is run.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tcl_path = os.path.join(current_dir, "forest-dark.tcl")
        try:
            self.root.tk.call('source', tcl_path)
            ttk.Style().theme_use('forest-dark')
        except Exception as e:
            print(f"Warning: Could not load theme '{tcl_path}': {e}")

    def create_login_ui(self):
        """Build the login interface."""
        self.login_frame = tk.Frame(self.root, bg="#131417")
        # Instruction Label
        #Changing the font the Monserrat
        self.lbl_instruction = tk.Label(self.login_frame, text="Enter your name below:", font=("Helvatica", 15), background="#131417")
        self.lbl_instruction.pack(pady=20)

        # Username Entry
#        self.name_entry = tk.Entry(self.login_frame, font=("Helvatica", 12),background="#131417")
        self.name_entry = ctk.CTkEntry(
            self.login_frame, 
            width=250, 
            height=40, 
            corner_radius=20,       # Rounded corners
            fg_color="#2D2D31",     # Background color
            border_color="#2D2D31", 
            text_color="#EEEFF3"
        )
        self.name_entry.pack(pady=2)
 
        self.name_entry.pack(pady=10, ipadx=10, ipady=5)
        self.name_entry.bind('<Return>', self.connect_and_login)
        
        btn = ctk.CTkButton(
            self.login_frame,
            text="Enter Chat",
            command=self.connect_and_login,
            
            # Font Style
            font=('Helvetica', 12),
            
            # Colors
            fg_color="#3B95FF",        # Default background color 
            text_color="#FFFFFF",    # Text color 
            hover_color="#5DA7FC",  # Color when mouse hovers 
            
            
            # Shape & Padding
            corner_radius=20,        
            height=40,               
        )
        
        btn.pack(pady=20,fill='x')
        self.login_frame.pack(expand=True)
        
    def create_chat_ui(self):
        """Build the main chat interface with contacts list and message area."""
        self.chat_frame = tk.Frame(self.root, bg="#131417")

        # ==================== SIDEBAR: CONTACTS LIST ====================
        self.sidebar = tk.Frame(self.chat_frame, width=250, bg="#131417")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="Contacts", bg="#131417", foreground="white", font=("Montserrat", 12)).pack(pady=10)
        #Adding a bottom border to the contacts list
        tk.Frame(
            self.sidebar, 
            background="#D3D3D3",   # Light Grey
            height=1                # Thickness
        ).pack(fill="x", pady=(0, 10))
        self.contacts = ttk.Treeview(self.sidebar, columns=("Username","Alerts"), show="headings",selectmode="browse")
        self.contacts.heading("Username", text="Online Users")
        self.contacts.heading("Alerts", text="New Msgs")

        self.contacts.column("Username", width=160, anchor=tk.W)
        self.contacts.column("Alerts", width=80, anchor=tk.CENTER)
        self.contacts.tag_configure('msg_alert')

        self.contacts.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.contacts.bind("<<TreeviewSelect>>", self.on_contact_click)

        # ==================== MAIN CHAT AREA ====================
        self.main_area = tk.Frame(self.chat_frame, bg="#131417")
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Header showing current chat recipient
        self.header_frame = tk.Frame(self.main_area, bg="#131417", height=50)
        self.header_frame.pack(fill="x")
        self.chat_label = tk.Label(self.header_frame, text="Select a user...", bg="#131417", fg="white",font=("Montserrat", 12))
        self.chat_label.pack(pady=10)

        # Chat history display area
        self.chat_history = scrolledtext.ScrolledText(self.main_area, state='disabled', bg="#131417",fg="white")
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_history.tag_config('me', justify='right', foreground='#3B95FF')
        self.chat_history.tag_config('other', justify='left',foreground='#ffffff')
        self.chat_history.tag_config("time_tag", foreground="gray", font=("Montserrat", 8))

# ==================== MESSAGE INPUT AREA ====================
        input_area = tk.Frame(self.main_area, bg="#131417", height=60)
        input_area.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Message Entry Field
        self.msg_entry = ctk.CTkEntry(
            input_area,             
            font=("Montserrat", 11),
            bg_color="#1B1D22",    
            corner_radius=10,
            fg_color="#2A2A2E",
            border_color="#3C3C40",
            text_color="#FFFFFF"
        )
        # Pack to the LEFT and let it expand to fill available space
        self.msg_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 10), pady=15)
        self.msg_entry.bind("<Return>", self.send_message)

        # Send Button
        send_btn = ctk.CTkButton(
            input_area,
            text="Send",
            command=self.send_message, 
            
            # Font Style
            font=('Helvetica', 12),
            
            # Colors
            fg_color="#3B95FF",
            text_color="#FFFFFF",
            hover_color="#5DA7FC",
            
            # Shape & Size
            corner_radius=10,
            height=30,      
            width=80        
        )
        
        # Pack to the RIGHT side
        send_btn.pack(side=tk.RIGHT, padx=(0, 20), pady=15)
    # ==================== FRAME SWITCHING ====================
    def show_login_frame(self):
        """ Display the login frame and hide the chat frame."""
        self.chat_frame.pack_forget()
        self.login_frame.pack(expand=True)

    def show_chat_frame(self):
        """ Display the chat frame and hide the login frame."""
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill='both', expand=True)


    # ==================== CONNECTION & AUTHENTICATION ====================
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

            # Handle maximum connections reached
            if welcome_msg == "[Server]: Maximum connections reached. Try again later.":
                error= welcome_msg.replace("[Server]:", "").strip()
                messagebox.showerror("Connection Error", error)
                self.client_socket.close()
                self.db.close()
                root.destroy()
                return

            print(f"[Server]: {welcome_msg}")
            # Send username
            self.username = username
            self.client_socket.send(username.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Error", "Failed during login phase")
            self.client_socket.close()
        self.show_chat_frame()
        self.root.title(f"Chat App - Logged in as: {self.username}")

        # Start thread to receive messages
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.daemon = True  # Thread ends when main program ends
        receive_thread.start()


    # ==================== CONTACTS MANAGEMENT ====================
    def update_contact_list(self, new_contact,contact_to_remove=None):
        """ Update the contact list in the UI."""
        existing_names = {self.contacts.item(item)['values'][0] for item in self.contacts.get_children()}
        names = new_contact.split(",") if new_contact else []

        # Add new contacts that are not already in the list
        for contact in names:
            contact = contact.strip()
            if not contact or contact==self.username:# Avoid adding empty names and self
                continue

            if contact not in existing_names:
                print(f"[DEBUG ADDING CONTACT]: {contact}")
                #set initial unread messages to 0
                self.unread_messages[contact] = 0
                self.contacts.insert("", tk.END, values=(contact,))
                existing_names.add(contact)
        # Remove contacts that are no longer online
        for item in self.contacts.get_children():
            item_data = self.contacts.item(item)
            contact_name = item_data['values'][0]
            if contact_name not in names and contact_name != self.username:
                print(f"[DEBUG REMOVING STALE CONTACT]: {contact_name}")
                self.contacts.delete(item)
                if contact_name in self.unread_messages:
                    del self.unread_messages[contact_name]
        # Remove specific contact if provided
        if contact_to_remove:
            print(f"[DEBUG REMOVING CONTACT]: {contact_to_remove}")
            for item in self.contacts.get_children():
                item_data = self.contacts.item(item)
                if item_data['values'][0] == contact_to_remove:
                    self.contacts.delete(item)
                    if contact_to_remove in self.unread_messages:
                        del self.unread_messages[contact_to_remove]
                    break

        print(f"[DEBUG CONTACT LIST UPDATED]: {new_contact}")

    # ==================== MESSAGE RECEIVING ====================
    def receive_messages(self):
        """ Thread function to receive messages from the server."""
        while True:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                print(f"[DEBUG RAW MSG]: {msg}")
                if not msg:
                    break
                #Handle messages from the server.
                if msg.startswith("[Server]:"):
                    print (f"[SERVER MSG]: {msg}")

                    # Handle user disconnected notification
                    if "has disconnected." in msg:
                        try:
                            disconnected_user = msg.split("'")[1]
                            print(f"[DEBUG DISCONNECTED USER]: {disconnected_user}")
                            if self.recipient == disconnected_user:
                                messagebox.showerror("Disconnected", f"User '{disconnected_user}' has disconnected.")
                                self.recipient = None
                                self.chat_label.config(text="Select a user...", fg="white")

                                # Clear chat history
                                self.chat_history.config(state='normal')
                                self.chat_history.delete('1.0', 'end')
                                self.chat_history.config(state='disabled')

                                self.update_contact_list("",disconnected_user)
                        except Exception as e:
                            print(f"[ERROR HANDLING DISCONNECTION]: {e}")

                    # Handle user not found error (when sending message to offline user)
                    elif "not found." in msg:
                        try:
                            user_to_delete=self.recipient
                            messagebox.showerror("Error", f"User '{user_to_delete}' not found or offline.")
                            self.recipient = None
                            self.chat_label.config(text="Select a user...", fg="white")
                            # Clear chat history
                            self.chat_history.config(state='normal')
                            self.chat_history.delete('1.0', 'end')
                            self.chat_history.config(state='disabled')
                            self.update_contact_list("",user_to_delete)
                        except Exception as e:
                            print(f"[ERROR HANDLING USER NOT FOUND]: {e}")

                    # Handle username already taken error
                    elif "Username already taken" in msg:
                        error = msg.replace("[Server]:", "").strip()
                        messagebox.showerror("Username Taken Error", error)
                        try:
                            self.client_socket.close()
                            self.db.close()
                        except Exception as e:
                            print(f"[ERROR CLOSING CONNECTIONS]: {e}")
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
                        timestamp= datetime.now().strftime("%H:%M")
                        sender,content = msg.split(":",1)
                        sender = sender.strip()
                        content = content.strip()
                        self.db.save_message(sender,self.username,content,timestamp)
                        # If chat with sender is open, display message
                        if self.recipient == sender:
                            self.chat_history.config(state='normal')
                            self.chat_history.insert(tk.END, f"{content}\n","other")
                            self.chat_history.insert(tk.END, f"{timestamp}\n", ("other","time_tag"))
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

    # ==================== MESSAGE SENDING ====================
    def send_message(self,event=None):
        """ Send message to the selected recipient."""
        msg = self.msg_entry.get()
        if not msg:
            return
        if not self.recipient:
            messagebox.showwarning("Error", "Please select a user from the list first!")
            return
        try:
            timestamp = datetime.now().strftime("%H:%M")
            final_msg = f"{self.recipient}:{msg}"
            print(f"[DEBUG SENDING MSG]: {final_msg}")
            self.client_socket.send(final_msg.encode('utf-8'))
            # Save sent message to the database
            self.db.save_message(self.username,self.recipient,msg,timestamp)

            self.chat_history.config(state='normal')
            self.chat_history.insert(tk.END, f"{msg}\n","me")
            self.chat_history.insert(tk.END, f"{timestamp}\n", ("me","time_tag"))

            self.chat_history.see(tk.END)
            self.chat_history.config(state='disabled')

            self.msg_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send: {e}")
            
    # ==================== CONTACT SELECTION ====================
    def on_contact_click(self, event):
        """ Handle contact selection from the contact list."""
        selected_item = self.contacts.selection()
        if selected_item:
            item_data = self.contacts.item(selected_item)
            clicked_name = item_data['values'][0]
            print(f"[CONTACT CLICKED]: {clicked_name}")
            if clicked_name == self.username:
                self.update_contact_list("",clicked_name)
                return  # Prevent chatting with self
            if self.recipient == clicked_name:
                return  # Already chatting with this user
            self.recipient = clicked_name
            self.chat_label.config(text=f"Chat with: {self.recipient}", fg="#becbd1")
            # Clear unread messages for this contact
            if clicked_name in self.unread_messages:
                del self.unread_messages[clicked_name]
                self.update_unread_alerts()
            # Load chat history from the database
            self.load_history_from_db(clicked_name)
            self.chat_history.config(state='normal')

    # ==================== CHAT HISTORY ====================
    def load_history_from_db(self, other_user):
        """ Load chat history from the database and display it in the chat history area."""
        print(f"--- Loading history for {other_user} ---")
        self.chat_history.config(state='normal')
        self.chat_history.delete('1.0', 'end')

        rows=self.db.get_chat_history(self.username, other_user)

        for sender ,msg,timestamp in rows:
            if sender==self.username:
                self.chat_history.insert(tk.END, f"{msg}\n","me")
            else:
                self.chat_history.insert(tk.END, f"{msg}\n","other")
            self.chat_history.insert(tk.END, f"{timestamp}\n","time_tag")

        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')


# ==================== DATABASE MANAGEMENT ====================
class DatabaseManager:
    """ Class to manage SQLite database operations for chat history."""
    def __init__(self, db_name="chat_history.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()
        self.connection.commit()

    def create_table(self):
        """ Create messages table if it doesn't exist."""
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

    def save_message(self, sender, receiver, message,timestamp=None):
        """ Save a message to the database."""
        try:
            timestamp = datetime.now().strftime("%H:%M")
            cursor = self.connection.cursor()
            query = """
                    INSERT INTO messages (sender, receiver, message, timestamp)
                    VALUES (?, ?, ?, ?)
                    """
            cursor.execute(query, (sender, receiver, message, timestamp))
            #cursor.execute("INSERT INTO messages VALUES (?, ?, ?,?)", (sender, receiver, message, timestamp))
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"DB Save Error: {e}")
    def get_chat_history(self, user1 ,user2):
        """ Retrieve chat history between two users."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(''' SELECT DISTINCT sender, message,timestamp FROM messages WHERE (sender= ? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY timestamp ASC ''', (user1, user2, user2, user1))
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


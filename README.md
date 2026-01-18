# TCP Messaging System

A lightweight, multi-threaded chat application built from scratch using Python's raw TCP sockets. 
This project demonstrates the implementation of a custom application-layer protocol and manages concurrent client connections without relying on high-level frameworks.

## About The Project

The goal of this project was to dive deep into low-level networking concepts by building a distributed system "the hard way." Instead of using abstract libraries like Socket.IO or HTTP frameworks, this application manages the raw byte streams directly over the TCP/IP stack.

It features a central server that acts as a switchboard, routing messages between connected clients in real-time using a dedicated thread-per-client architecture.

## Key Features

* **Custom Protocol:** Implements a text-based application protocol for user registration and message routing.
* **Concurrency:** Handles multiple simultaneous users using Python's `threading` module (non-blocking server).
* **Robust Networking:** Built on top of TCP to ensure guaranteed packet delivery and ordered data streams.
* **Zero Dependencies:** Runs on pure Python standard library (`socket`, `threading`).
* **Traffic Analysis:** Designed to be easily analyzed with tools like Wireshark for protocol verification.

## Built With

* **Language:** Python 3
* **Networking:** Raw BSD Sockets (`socket` library)
* **Concurrency:** Multi-threading

##  Getting Started

### Prerequisites
* Python 3.x installed on your machine.

### Installation
1.  Clone the repo:
    ```sh
    git clone [https://github.com/your-username/pychat-tcp.git](https://github.com/your-username/pychat-tcp.git)
    ```
2.  Navigate to the project directory:
    ```sh
    cd pychat-tcp
    ```

##  Usage
To simulate a chat environment, you will need to run the server in one terminal and multiple client instances in separate terminals.

### Step 1: Start the Server
The server binds to all interfaces (`0.0.0.0`) on port `[DESIRED PORT NUMBER]`.
```bash
python server.py

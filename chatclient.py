import socket
import time
import sys
import threading
import os


def send():
    """
    Handles message sending of the client
    """
    global send_user
    global file_path

    while True:
        try:
            message = input("").strip("\n").split(" ")
            if message[0] == "/send":
                try:
                    send_user = message[1]
                    file_path = message[2]
                except:
                    continue

            server.sendall((' '.join(message)).encode('ascii'))
            if message[0] == "/quit":
                exit()
        except EOFError:
            continue


def receive():
    """
    Parses all messages received by the client
    """
    while True:
        try:
            msg = str(server.recv(2048).decode('utf-8'))

            if not msg:
                break

            # Checks if the server is fine with the client sending the file
            if msg == "/send_ok":
                try:
                    file = open(file_path, 'r')
                    data = file.read()
                    server.sendall(data.encode('ascii'))
                    file.close()
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] You sent {file_path} to {send_user}.",
                          flush=True)
                except:
                    server.sendall("/bad_path".encode('ascii'))
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] {file_path} does not exist.", flush=True)

            # Checks if /send was targeting an invalid client
            elif msg == "/send_bad_user":
                print(f"[Server message ({time.strftime('%H:%M:%S')})] {send_user} is not here.", flush=True)
                try:
                    file = open(file_path, 'r')
                    file.close()
                except:
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] {file_path} does not exist.", flush=True)

            # Processes receiving the file
            elif msg.split(" ")[0] == "/sending":
                name = msg.split("/")[-1]

                file = open(f"{name}", "w")
                content = server.recv(2048).decode('utf-8')
                file.write(content)
                file.close()
            else:
                print(msg.strip('\n'), flush=True)
        except:
            break
    os._exit(os.X_OK)


if __name__ == '__main__':
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = socket.gethostbyname(socket.gethostname())
        port = int(sys.argv[1])
        username = sys.argv[2]

        addr = (host, port)
        server.connect(addr)
        server.sendall(username.encode('ascii'))

        to = threading.Thread(target=send, daemon=True)
        to.start()

        rc = threading.Thread(target=receive, daemon=True)
        rc.start()

        while True:
            pass
    except:
        exit(1)


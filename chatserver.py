import socket
import sys
import threading
import time

TIMEOUT = 2
ADD = 1
REMOVE = 0
channels = []
DISCONNECTED = 2
CONNECTED = 1
QUEUE = 0
RANDEXIT = 3


def check_name(name, channel):
    """
    Checks if the name is present in the given channel

    :param name: Name to check
    :param channel: Channel to check in
    :return: The client object of the name if it exists, else the name is returned back
    """
    for client in channel.connected:
        if name == client.name:
            return client
    return name


def check_channel(name):
    """
    Checks if the given name belongs to one of the channels in the server/

    :param name: The name to check
    :return: The channel class with that name is returned, else the name is returned.
    """
    for channel in channels:
        if channel.name == name:
            return channel
    return name


def broadcast(message, client_list):
    """
    Sends the given message to every client within the given client list.

    :param message: The message to send
    :param client_list: All recipients of the message
    """
    for client in client_list:
        try:
            client.conn.sendall(message.encode('ascii'))
        except BrokenPipeError:
            continue


def name_exists(name, channel):
    """
    Checks if the name exists in the channel regardless of whether they're connected or in queue.

    :param name: The name to check
    :param channel: The channel to check in
    :return: True if client exists, false otherwise
    """
    for client in channel.connected:
        if client.name == name:
            return True
    for client in channel.queue:
        if client.name == name:
            return True
    return False


def parse_config():
    """
    Parses the channel config file
    """
    try:
        file = open(sys.argv[1], 'r')
        content = file.read().split('\n')
        file.close()

        for config in content:
            config = config.split(" ")

            if int(config[2]) <= 0:
                exit(1)

            this_channel = Channel(config[1], int(config[2]), int(config[3]))

            if this_channel.name[0].isdigit():
                exit(1)

            for channel in channels:
                if channel.name == this_channel.name or channel.port == this_channel.port or channel.capacity < 5:
                    exit(1)
            channels.append(this_channel)

        if len(channels) < 3:
            exit(1)
    except:
        exit(1)


class Client:
    """
    This class stores information regarding the client, keeps track of their status, and handles all client messages
    """
    def __init__(self, name, conn, channel, status):
        """
        Constructor of the Client instance which is connected to the server

        :param name: Name of the client
        :param conn: Socket object which represents the connection to the client
        :param channel: The specific channel that the client is connected to
        :param status: Used to track the current client status
        """
        self.name = name
        self.conn = conn
        self.channel = channel
        self.status = status
        self.muted = 0
        self.last_message = time.time()
        self.kicked = False

    def handle_client(self):
        """
        The Client handler which continuously calls recv and parses the message/command.
        Runs on a thread started in the channel class.
        """
        # The thread which tracks if the client has gone afk
        afk = threading.Thread(target=self.timeout, daemon=True)
        afk.start()

        while self.status == CONNECTED or self.status == QUEUE:
            try:
                message = self.conn.recv(1024).decode('UTF-8')
                message = message.strip("\n").split(" ")

                if len(' '.join(message)) == 0:
                    self.channel.process_connection(RANDEXIT, self)
                    self.status = DISCONNECTED
                    break

                if message[0] == "/quit" or not message:
                    self.channel.process_connection(REMOVE, self)
                    break
                elif message[0] == "/whisper":
                    if self.status == CONNECTED:
                        if self.muted > 0:
                            self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] You are still muted for "
                                              f"{self.muted - round(time.time())} seconds.\n".encode('ascii'))
                        else:
                            if len(message) >= 2:
                                self.whisper(message)
                            else:
                                self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})]  is not here."
                                                  .encode('ascii'))
                elif message[0] == "/list":
                    self.list()
                elif message[0] == "/switch":
                    if len(message) == 2:
                        self.switch(message)
                    else:
                        self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})]  does not exist.\n"
                                          .encode('ascii'))
                elif message[0] == "/send":
                    self.send(message)
                else:
                    if self.status == CONNECTED:
                        if self.muted > 0:
                            self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] You are still muted for "
                                              f"{self.muted - round(time.time())} seconds.\n".encode('ascii'))
                        else:
                            broadcast(f"[{self.name} ({time.strftime('%H:%M:%S')})] {' '.join(message)}",
                                      self.channel.connected)
                            print(f"[{self.name} ({time.strftime('%H:%M:%S')})] {' '.join(message)}", flush=True)
                if self.muted == 0:
                    self.last_message = time.time()
            except:
                break

        self.status = DISCONNECTED
        self.conn.close()
        return

    def update_status(self, status):
        """
        For the Server to update the client status i.e. muting the client

        :param status: The new client status
        """
        self.status = status
        return

    def mute(self, duration):
        """
        Sets the duration for which the client is muted and set the client to be muted

        :param duration: How long the client will be muted for
        """
        self.muted = int(time.time()) + duration
        self.last_message += duration
        time.sleep(duration)
        self.muted = 0
        return

    def send(self, message):
        """
        Handles the file sending if the client is trying to send a file

        :param message: The contents of the command
        """
        target = check_name(message[1], self.channel)
        if isinstance(target, Client):
            # Informs the client that the sending target is valid
            self.conn.sendall("/send_ok".encode('ascii'))
            file = self.conn.recv(2048).decode('UTF-8')

            if file == "/bad_path":
                return

            # Sends the recipient the filename and then sends the file contents
            target.conn.sendall(f"/sending {message[2]}".encode('ascii'))
            target.conn.sendall(file.encode('ascii'))
            print(f"[Server message ({time.strftime('%H:%M:%S')})] {self.name} sent {message[2]} to {target.name}.",
                  flush=True)
            return

        self.conn.sendall("/send_bad_user".encode('ascii'))

    def get_name(self):
        """
        Fetches the name of the client
        """
        return self.name

    def update_lastmsg(self, time):
        """
        Updates the last message the client sent, used to track AFK timeout
        :param time: The time the last message was sent
        """
        self.last_message = time

    def list(self):
        """
        Sends the client a list of all current channels and channel information
        """
        message = ""
        for channel in channels:
            message += f"[Channel] {channel.name} {len(channel.connected)}/{channel.capacity}/{len(channel.queue)}.\n"
        self.conn.sendall(message[:-1].encode('ascii'))

    def whisper(self, message):
        """
        Parses the message for the whisper command where the message is only sent to the target

        :param message: The message to be whispered
        """
        target = check_name(message[1], self.channel)
        print(f"[{self.name} whispers to {target.get_name() if isinstance(target, Client) else target}: "
              f"({time.strftime('%H:%M:%S')})] {' '.join(message[2:])}", flush=True)
        if isinstance(target, Client):
            target.conn.sendall(
                f"[{self.name} whispers to you: ({time.strftime('%H:%M:%S')})] {' '.join(message[2:])}".encode('ascii'))
        else:
            self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] {target} is not here.".encode('ascii'))

    def switch(self, message):
        """
        Handles the switch command and moves the client to the specified channel

        :param message: The message containing the destination channel the client wants to be placed in
        """
        target = check_channel(message[1].strip('\n'))
        if isinstance(target, Channel):
            if not name_exists(self.name, target):
                self.channel.process_connection(REMOVE, self)
                target.process_connection(ADD, self)
                self.channel = target
            else:
                # Informs the client they cannot switch because a user of their name is already in the channel
                self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] Cannot switch to the "
                                  f"{target.name} channel.\n".encode('ascii'))
        else:
            self.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] {target} does not exist.\n"
                              .encode('ascii'))

    def timeout(self):
        """
        Handles the AFK timeout function, is run from a thread in handle_client because this function blocks
        """
        while (time.time() <= self.last_message + 100 and self.status == CONNECTED) or self.status == QUEUE:
            time.sleep(0.1)

        if self.status != DISCONNECTED:
            self.channel.process_connection(TIMEOUT, self)
            self.status = DISCONNECTED
            self.conn.close()
        return

    def kick(self):
        """
        Used by the channel to set the status of client to be kicked
        """
        self.kicked = True


class Channel:
    """
    Stores channel information, initializes connections, and spawns new client threads when clients connect are found.
    Besides these the other responsibility of channel is to clean up after the client has disconnected.
    """
    def __init__(self, name, port, capacity):
        """
        Constructor of channel which listens for client connections

        :param name: The channel name
        :param port: Port number which the channel operates on
        :param capacity: How many clients may be connected at once
        """
        self.name = name
        self.port = port
        self.capacity = capacity
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = []
        self.queue = []
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        """
        Initializes the channel connection to listen for new clients.
        """
        host = socket.gethostbyname(socket.gethostname())
        addr = (host, self.port)
        self.socket.bind(addr)
        self.socket.listen()

        count = 0

        while self.running:
            conn, addr = self.socket.accept()
            username = str(conn.recv(1024).decode('UTF-8')).strip('\n')
            client = Client(username, conn, self, None)
            count += 1
            if not name_exists(client.get_name(), self):
                self.process_connection(ADD, client)
                thread = threading.Thread(target=client.handle_client, daemon=True)
                thread.start()

            else:
                # Reject the incoming connection because client name already exists
                client.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] Cannot connect to the "
                                    f"{self.name} channel.\n".encode('ascii'))
                client.conn.close()
        socket.close(socket.SHUT_RDWR)
        return

    def process_connection(self, operation, client):
        """
        Processes the client operation, handles adding, removing, timeout, and unexpected exit of the client.

        :param operation: The operation to be performed on the client, be it to add, remove, timeout the client.
        :param client: The target client
        """
        self.lock.acquire()
        if operation == ADD:
            client.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] Welcome to the {self.name} channel, "
                                f"{client.get_name()}.\n".encode('ascii'))
            if len(self.connected) < self.capacity:
                self.edit_connections(ADD, client)
            else:
                self.edit_queue(ADD, client)

        elif operation == REMOVE or TIMEOUT:
            if client.status == CONNECTED or operation == RANDEXIT:
                self.edit_connections(operation, client)
                # checks if clients in the queue can be added to the channel after the current client is gone
                if len(self.connected) < self.capacity:
                    if len(self.queue) > 0:
                        client = self.edit_queue(REMOVE)
                        self.edit_connections(ADD, client)

            elif client.status == QUEUE:
                self.queue.remove(client)
                for other_client in self.queue:
                    other_client.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] "
                                              f"You are in the waiting queue and there are "
                                              f"{self.queue.index(other_client)} user(s) ahead of you.\n"
                                              .encode('ascii'))
                if operation != RANDEXIT:
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] {client.get_name()} has left the channel.",
                          flush=True)

        self.lock.release()

    def edit_connections(self, operation, current_client):
        """
        Called by process_connection to performs the actual operation on the client.

        :param operation: The operation to be performed
        :param current_client: The target client
        """
        if operation == ADD:
            current_client.update_status(CONNECTED)
            current_client.update_lastmsg(time.time())
            self.connected.append(current_client)
            broadcast(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.get_name()} "
                      f"has joined the channel.\n", self.connected)
            print(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.get_name()} "
                  f"has joined the {self.name} channel.", flush=True)

        elif operation == REMOVE:
            self.connected.remove(current_client)
            broadcast(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.get_name()} "
                      f"has left the channel.\n", self.connected)

            if not current_client.kicked:
                print(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.get_name()} "
                      f"has left the channel.", flush=True)

        elif operation == TIMEOUT:
            self.connected.remove(current_client)
            broadcast(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.name} "
                      f"went AFK.\n", self.connected)
            print(f"[Server message ({time.strftime('%H:%M:%S')})] {current_client.name} went AFK.", flush=True)

        elif operation == RANDEXIT:
            if current_client.status == CONNECTED:
                self.connected.remove(current_client)
            else:
                self.queue.remove(current_client)

    def edit_queue(self, operation, current_client=None):
        """
        Processes the client operation for clients in the waiting queue.

        :param operation: The operation to be performed
        :param current_client: The target client
        """
        if operation == ADD:
            current_client.update_status(QUEUE)
            self.queue.append(current_client)
            current_client.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] "
                                        f"You are in the waiting queue and there are "
                                        f"{self.queue.index(current_client)} user(s) ahead of you.\n".encode('ascii'))

        elif operation == REMOVE:
            current_client = self.queue.pop(0)
            for client in self.queue:
                client.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] "
                                    f"You are in the waiting queue and there are "
                                    f"{self.queue.index(client)} user(s) ahead of you.\n".encode('ascii'))

        return current_client

    def disconnect(self):
        """
        Called in main to end the current channel
        """
        self.running = False


if __name__ == '__main__':
    """
    The main program, launches all the channels and handles any server commands.
    """
    parse_config()

    for channel in channels:
        thread = threading.Thread(target=channel.start, daemon=True)
        thread.start()

    running = True

    while running:
        try:
            cmd = input("").split(" ")

            # Disconnects the target client from the selected channel
            if cmd[0] == "/kick":
                channel, user = cmd[1].split(":")
                channel = check_channel(channel)
                if isinstance(channel, Channel):
                    user = check_name(user, channel)
                    if isinstance(user, Client):
                        user.kick()
                        channel.process_connection(REMOVE, user)
                        user.status = DISCONNECTED
                        user.conn.shutdown(socket.SHUT_RDWR)
                        user.conn.close()
                        print(f"[Server message ({time.strftime('%H:%M:%S')})] Kicked {user.get_name()}.", flush=True)
                    else:
                        print(f"[Server message ({time.strftime('%H:%M:%S')})] {user} is not in {channel.name}.",
                              flush=True)
                else:
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] {channel} does not exist.", flush=True)

            # Mutes the target client in the selected channel
            elif cmd[0] == "/mute":
                channel, user = cmd[1].split(":")
                duration = cmd[2].strip('\n')
                channel = check_channel(channel)
                if isinstance(channel, Channel):
                    user = check_name(user, channel)
                    if isinstance(user, Client):
                        if duration.isdigit():
                            if int(duration) > 0:
                                user.conn.sendall(f"[Server message ({time.strftime('%H:%M:%S')})] "
                                                  f"You have been muted for {duration} seconds.\n".encode('ascii'))
                                print(f"[Server message ({time.strftime('%H:%M:%S')})] Muted {user.get_name()} for "
                                      f"{duration} seconds.", flush=True)

                                # Separate thread to track how long the client is muted for
                                mute = threading.Thread(target=user.mute(int(duration)), daemon=True)
                                mute.start()
                                continue
                        print(f"[Server message ({time.strftime('%H:%M:%S')})] Invalid mute time.", flush=True)
                        continue
                print(f"[Server message ({time.strftime('%H:%M:%S')})] {user} is not here.", flush=True)

            # Disconnects all connected and in queue clients for the given channel
            elif cmd[0] == "/empty":
                channel = cmd[1].strip('\n')
                channel = check_channel(channel)
                if isinstance(channel, Channel):
                    for client in channel.queue[:]:
                        client.update_status(DISCONNECTED)
                        client.conn.shutdown(socket.SHUT_RDWR)
                        client.conn.close()
                    for client in channel.connected[:]:
                        client.update_status(DISCONNECTED)
                        client.conn.shutdown(socket.SHUT_RDWR)
                        client.conn.close()
                    channel.connected = []
                    channel.queue = []
                    print(f"[Server message ({time.strftime('%H:%M:%S')})] {channel.name} has been emptied.",
                          flush=True)
                    continue
                print(f"[Server message ({time.strftime('%H:%M:%S')})] {channel} does not exist.", flush=True)

            # Shut down entire server including all channels
            elif cmd[0] == "/shutdown":
                for channel in channels:
                    for client in channel.queue[:]:
                        client.update_status(DISCONNECTED)
                    for client in channel.connected[:]:
                        client.update_status(DISCONNECTED)
                    channel.disconnect()
                running = False
        except:
            continue


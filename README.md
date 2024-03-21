# Python Chat Program

<p> A more complex than usual chat server and client. </p>

## Features
<ul>
    <li>Multi-threaded chat server with multiple channels, each allowing for concurrent client connections </li>
    <li>Each channel has a configurable port and max client amount </li>
    <li>Should the max client amount be reached, any incoming clients are added to a waiting queue and notified of how 
many are ahead of them in the queue</li>
    <li>Any messages in the channel are broadcast to all clients in the channel</li>
    <li>Client names must be unique in the channel</li>
    <li>Clients are automatically kicked after 100 seconds of inactivity</li>
</ul>

Run commands:
```
python3 chatserver.py [config_path]
python3 chatclient.py [port] [username]
```

## Client commands
```
/whisper [target_name] [message]
```
Sends a private message to the target. Error message will be returned if target is not in the channel.

```
/quit
```
The client will be disconnected from the server and other clients in the channel will be notified of the departure.

```
/list
```
Will list out all available channels and its current connections, max connections, and queue length.

```
/switch [channel_name]
```
The client will be connected to the specified channel or added to the queue. An error message will be displayed if the 
channel does not exist or the client name is not unique in the new channel.

```
/send [target] [file_path]
```
Attempts to send the file at the specified file path to the target client in the same channel. An error message will be 
displayed if the file path is invalid or the target client is not in the same channel.

## Server commands
```
/kick [channel]:[target_client]
```
Kicks the target client out of the channel if the client is inside the channel, otherwise error message will be returned.

```
/mute [channel]:[target_client] [time]
```

Will mute the target client for the specified amount of time. During this period the client cannot send messages but may
still use other commands (besides /whisper). Attempts to send messages will be met with a reminder on how long the client
will be muted for.

```
/empty [channel]
```
All connected and in queue clients will be disconnected from the channel.

```
/shutdown
```
The server will shut down and disconnect all clients.

## Configuration File
Channels in the configuration file must be in the below format:
```
channel [name] [port] [max_capacity]
```
Where name is the channel name, port is the connection port for the channel, and max_capacity is the maximum number of 
clients that can be concurrently connected at once.

Rules:
<ol>
<li> Each channel must have a max capacity of at least 5</li>
<li> There must be at least three channels in the config file</li>
<li> No two channels can have the same name or port</li>
<li> Channel names cannot begin with a number</li>
</ol>

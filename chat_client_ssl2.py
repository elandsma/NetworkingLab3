
import socket
import sys
import threading
import queue
import gnupg
import time
import signal
import ssl

from chat_server import ClientClosedConnection, read_lines

recv_q = queue.Queue(10)   #q of messages, received from others
exit_event = threading.Event()

HANDLE = ""

try:
    gpg = gnupg.GPG(homedir="/Users/elias/.gnupg", binary="/usr/local/bin/gpg")  #works on my mac
except:
    gpg = gnupg.GPG(gnupghome="/home/elandsma/.gnupg")   #works on montreat


def client_reader_thread(conn, process):
    try:
        lines=[]
        while True:
            if exit_event.is_set():
                conn.close()
                break
            #lines.extend(read_lines(conn))
            #only add non-blank lines to be processed
            for line in read_lines(conn):
                if line !='':
                    lines.append(line)
            while True:
                msg_start = None
                msg_end = None
                #print(f"\nlines received by reader_thread():\n{format(lines)}\n")  #debug
                #looking for "BEGIN"
                for i in range(len(lines)):
                    if lines[i]=="BEGIN":
                        msg_start = i
                        break
                # looking for "END"
                if msg_start is not None:
                    for i in range(len(lines)):
                        if lines[i]=="END":
                            msg_end = i
                            break
                if msg_start is not None and msg_end is not None:
                    process(lines[msg_start:msg_end+1])
                    #remove message portion from lines[] that has already been processed
                    del lines[0:msg_end+1]
                else:
                    break
    except ClientClosedConnection as e:
        print(e)
        exit()


def process_received_message_client(lines):
    #print("got in to process_received_message_client\n")
    assert (lines[0]=="BEGIN")
    assert (lines[-1] == "END")
    msg = {}
    for i in range(1, len(lines)-1):
        try:
            (key, value)=lines[i].split(":")
            msg[key] = value
        except ValueError as e:
            print("Bad Formatting Found, Message discarded")
            print(e)
            print(lines)
            print("EndOfMessage")
    if len(msg)>0:
        recv_q.put(msg, False)


def send_hello(sock, username):
    buff="BEGIN\n"
    buff+="type:hello\n"                    #type of message
    buff+="name: {0}\n".format(username)    #tell everyone our name
    buff+="END\n"
    sock.sendall(str.encode(buff))          #send over 'sock' tcp connection

def send_hello_ack(sock, username):
    buff="BEGIN\n"
    buff+="type:hello_ack\n"                    #type of message
    buff+="name: {0}\n".format(username)    #tell everyone our name
    buff+="END\n"
    sock.sendall(str.encode(buff))          #send over 'sock' tcp connection

def send_goodbye(conn, USERNAME):
    msg = f"{USERNAME} has left the chat"
    send_message(conn, {'message':msg, 'name':USERNAME, 'type':"goodbye"})

def send_publickey_request(conn, USERNAME):
    msg = f"{USERNAME} requests public key"
    send_message(conn, {'message':msg, 'name':USERNAME, 'type':"publickeyrequest"})

def tell_joke(conn):
    while True:
        time.sleep(5)
        send_message(conn, {'message':"this is a joke", 'type':"broadcast"})

def send_message( sock, msg):
    buff=''
    for key,value in msg.items():
        buff+="{0}:{1}\n".format(key,value)
    #sign_data=gpg.sign(buff)
    #todo : fix this.
    sign_data="FIXME"
    buff+="signed:{0}\n".format(sign_data)
    buff="BEGIN\n{0}END\n".format(buff)
    #print(f"Debug: sending: {format(buff)}")
    sock.sendall(str.encode(buff))  #send

def constructMessage(conn, USERNAME):
    type = ""
    while type != 'broadcast' and type != 'private':
        type = input("Enter message type: ('broadcast' or 'private'):")
    if(type=="private"):
        recipient = input("Enter recipient:")
    msgbody = input("Enter Message Body:")
    if(type=="private"):
        send_message(conn, {'name': USERNAME, 'message': msgbody, 'type': type, 'recipient':recipient})
    else:
        send_message(conn, {'name': USERNAME, 'message': msgbody, 'type': type, 'recipient': 'all'})


def recvq_thread(s, USERNAME):
    while True:
        # get next message
        if exit_event.is_set():
            s.close()
            break
        msg = recv_q.get()
        #print(msg)
        # if somebody says hello to enter chat, show they have entered, and respond
        if msg['type'] == "hello":
            print("{0} has joined the chat".format(msg['name']))
            send_hello_ack(s, USERNAME)
        # show that others have responded to somebody else entering chat and saying hello.
        elif msg['type'] == "hello_ack":
            print("{0} is in the chatroom".format(msg['name']))
        # if not hello or hello_ack, process message otherwise:
        elif msg['type'] == "private":
            if msg['recipient']==USERNAME:
                print(f"{msg['name']}(private): {msg['message']}\n")
            else:
                pass
                # print("debug:private message sent to somebody else.")
        elif msg['type'] == "goodbye":
            print(msg['message'])
        elif msg['type']=="broadcast":
            print(f"{msg['name']}: {msg['message']}")
        else:
            print("unknown message type received. Discarded message.")


def main( HOST, PORT, USERNAME):
    def sighandler(signum, frame):
        send_goodbye(s, USERNAME)
        exit_event.set()
        for t in threads:
            t.join()
        s.close()
        exit()
    signal.signal(signal.SIGINT, sighandler)
    threads = []
    try:
        #connect to remote chat_server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, int(PORT)))
            print("Connected to server.")
            print("Type \"NEW\" to send message. Type \"QUIT\" to quit.")
            #create reader thread
            tr = threading.Thread(target=client_reader_thread, args=(s, process_received_message_client, ))
            tr.daemon=True
            threads.append(tr)
            tr.start()

            #Joke Daemon.
            #tj = threading.Thread(target=tell_joke, args=(s, ))
            #tj.daemon = True
            #tj.start()

            #start chat protocol
            send_hello(s, USERNAME)

            recvqthread = threading.Thread(target=recvq_thread, args=(s, USERNAME,))
            recvqthread.daemon = True
            threads.append(recvqthread)
            recvqthread.start()
            while True:
                for line in sys.stdin:
                    if line.rstrip() == "NEW":
                        constructMessage(s, USERNAME)
                    if line.rstrip() == "QUIT":
                        send_goodbye(s, USERNAME)
                        exit_event.set()
                        for t in threads:
                            t.join()
                        s.close()
                        exit(0)
    except ConnectionRefusedError:
        print("Connection Refused Error")


if __name__=="__main__":
    if (len(sys.argv) < 4 ):     #name, host, port, username
        print("Usage: chat_client.py HOSTNAME PORT USERNAME")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
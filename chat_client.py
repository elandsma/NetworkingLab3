#!/usr/bin/env python3

import socket
import sys
import threading
import queue
import gnupg
import time

from chat_server import ClientClosedConnection, read_lines, reader_thread

recv_q = queue.Queue(10)
gpg = gnupg.GPG(gnupghome="mypathtothefile")   #TODO change this to reflect

def process_received_message_client(lines):
    print("got in to process_received_message_client")
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
    buff+="name: {0}\n".format(username)    #tell everynone our name
    buff+="END\n"
    sock.sendall(str.encode(buff))          #send over 'sock' tcp connection

def send_message( sock, msg):
    buff=''
    for key,value in msg.items():
        buff+="{0}:{1}\n".format(key,value)
    sign_data=gpg.sign(buff)
    print("send_message()\nbuff={0}\nsign_data={1}\n".format(buff, sign_data))
    buff+="signed:{0}\n".format(sign_data)
    buff="BEGIN\n{0}END\n".format(buff)
    sock.sendall(str.encode(buff))  #send

def tell_joke(conn):
    while True:
        time.sleep(5)
        send_message(conn, {'message':"this is a joke", 'type':"broadcast"})

def main( HOST, PORT, USERNAME):
    #connect to remote chat_server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, int(PORT)))
        #create reader thread
        tr = threading.Thread(target=reader_thread, args=(s, process_received_message_client))
        tr.daemon=True
        tr.start()

        tj = threading.Thread(target=tell_joke, args=(s, ))
        tj.daemon = True
        tj.start()

        #start chat protocol
        send_hello(s, USERNAME)
        while True:
            #get next message
            msg = recv_q.get()
            if msg['type'] == "hello":
                print("{0} has joined the chat".format(msg['name']))
                send_hello_ack(s, USERNAME)
            elif msg['type'] == "hello_ack":
                print("{0} is in the chatroom".format(msg['name']))
            else:
                msg={}
                msg['type']="broadcast"
                msg['name']=USERNAME
                msg['message'] = "Got an unknown message"
                send_message(s, msg)

if __name__=="__main__":
    if (len(sys.argv) < 4 ):     #name, host, port, username
        print("Usage: chat_client.py HOSTNAME PORT USERNAME")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
#!/user/bin/env python3
'''
Elias Landsman
April 2021
CSCI373 Cybersecurity
Networking Lab 3
'''

PORT_START=37301
HOST = '0.0.0.0'

import socket
import threading
import queue

list_of_queues = []

class ClientClosedConnection(Exception):
    '''empty class for custom exception'''
    pass

def read_lines(conn):
    '''read from a socket, return array of strings'''
    buff = ''
    while True:
        data = conn.recv(1024)
        if not data:
            raise ClientClosedConnection('client closed connection')
            #break # reached end of message
        buff += data.decode('utf-8', "ignore")
        if buff.endswith("\n"):
            break
    print(f"RECV: {format(buff)}")
    buff.replace("\r", "")   #remove all "\r" chars
    return buff.split("\n")

def reader_thread(conn):
    try:
        lines=[]
        while True:
            lines.extend(read_lines(conn))
            #only add non-blank lines to be processed
            for line in read_lines(conn):
                if line !='':
                    lines.append(line)
            while True:
                msg_start = None
                msg_end = None
                #print("reader_thread() lines={0}".format(lines))  #debug
                #looking for "BEGIN"
                for i in range(len(lines)):
                    if lines[i]=="BEGIN\n":
                        #print(f"Got BEGIN at line {format(i)}")   #debug
                        msg_start = i
                        break
                # looking for "END"
                if msg_start is not None:
                    for i in range(len(lines)):
                        if lines[i]=="END":
                            #print(f"got END at line {format(i)}")  #debug
                            msg_end = i
                            break
                if msg_start is not None and msg_end is not None:
                    process_message_server(lines[msg_start:msg_end+1])
                    #remove message portion from lines[] that has already been processed
                    del lines[0:msg_end+1]
                else:
                    break
    except ClientClosedConnection as e:
        print(e)

def process_message_server(message_lines):
    for q in list_of_queues:
        q.put(message_lines, False)

def writer_thread(conn):
    while True:
        msg_to_send = queue.get()
        msg_data = "\n".join(msg_to_send) + "\n"
        conn.sendall(str.encode(msg_data))

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #find available port
    PORT = PORT_START
    while(PORT<PORT_START+20): #check for 20 ports
        try:
            s.bind( (HOST, PORT) )
            print(f"Server bound to port {format(PORT)}")
            break
        except:
            PORT+=1
    #found an open port.
    try:
        s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.listen()
        while True:
            # wait  for connection
            conn, addr = s.accept()
            print(f"New connection from {format(addr)}")
            #create queue for this client
            q = queue.Queue(10)
            list_of_queues.append(q)
            #create threads to handle connection to client
            #reader thread
            tr = threading.Thread(target=reader_thread, args=(conn,process_message_server ))
            tr.daemon=True
            tr.start()
            #writer thread
            tw = threading.Thread(target=writer_thread, args=(conn, ))
            tw.daemon=True
            tw.start()

    finally:
        s.shutdown(socket.SHUT_WR)
        s.close()


if __name__=="__main__":
    main()
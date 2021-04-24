'''
Elias Landsman
April 2021
CSCI373 Cybersecurity
Networking Lab 3
'''

import socket
import threading
import queue
import sys
import ssl

PORT_START=37301
HOST = '0.0.0.0'
list_of_queues = []
context = ssl.create_default_context()


class ClientClosedConnection(Exception):
    '''empty class for custom exception'''
    pass

def read_lines(conn):
    '''read from a socket, return array of strings'''
    buff = ''
    while True:
        data = conn.recv(1024)
        if not data:
            raise ClientClosedConnection(f"client closed connection.")
            # reached end of message
        buff += data.decode('utf-8', "ignore")
        if buff.endswith("\n"):
            break
    #print(f"read_lines got raw message.\n")
    buff.replace("\r", "")   #remove all "\r" chars
    return buff.split("\n")

def server_reader_thread(conn, process):
    try:
        lines=[]
        while True:
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
                    #turn lines[] into dictionary so we can access key:value pairs
                    #only do this for lines BETWEEN 'begin' and 'end'.
                    msgDict = {}
                    #for line in lines:
                    for line in lines[msg_start+1:msg_end]:
                        if line != "BEGIN" and line!="END":
                            i = line.split(':')
                            msgDict[i[0]] = i[1]
                    process(lines[msg_start:msg_end +1])
                    del lines[0:msg_end+1]
                else:
                    break
    except ClientClosedConnection as e:
        conn.close()
        print(e)
        sys.exit()



def process_received_message_server(message_lines):
    '''this is passed as a process() function parameter into the reader_thread function'''
    print(f"Sending message to all client queues.")
    for q in list_of_queues:
        q.put(message_lines, False)

def writer_thread(conn, q):
    while True:
        msg_to_send = q.get()
        msg_data = "\n".join(msg_to_send) + "\n"
        try:
            conn.sendall(str.encode(msg_data))
        except ClientClosedConnection as e:
            print(e)
            list_of_queues.remove(q)
            break
        except:
            print("killing writer_thread, removing q")
            list_of_queues.remove(q)
            break


def main():
    threads = []
    clients = []

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('./montreat-fullchain.pem', './montreat-privkey.pem')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as rawsocket:
        #find available port
        PORT = PORT_START
        while(PORT<PORT_START+20): #check for 20 ports
            try:
                rawsocket.bind( (HOST, PORT) )
                print(f"Server bound to port {format(PORT)}")
                break
            except:
                PORT+=1
    #found an open port.
    s=None
    rawsocket.listen()
    try:
        while True:
            # wait  for connection
            with context.wrap_socket(rawsocket, server_side=True) as s:

                conn, addr = s.accept()

            #add client to list of current clients.
            clients.append(s)
            print(f"New connection from {format(addr)}")
            #create queue for this client, add to list of q's
            q = queue.Queue(10)
            list_of_queues.append(q)
            #create threads to handle connection to client
            #reader thread
            tr = threading.Thread(target=server_reader_thread, args=(s, process_received_message_server, ))
            tr.daemon=True
            threads.append(tr)
            tr.start()
            #writer thread
            tw = threading.Thread(target=writer_thread, args=(s, q, ))
            tw.daemon=True
            threads.append(tw)
            tw.start()

    finally:
        if s is not None:
            s.shutdown(socket.SHUT_RDWR)
            s.close()

if __name__=="__main__":
    main()
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

    try:
        s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.listen()
        while True:
            # wait  for connection
    except:
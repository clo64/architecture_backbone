import socket
from queue import Queue
import json
import pickle

class Nano_Server:

    def __init__(self, received_data_queue, send_data_queue):

        #Globally relevant
        self.ip_addr = '10.0.0.237'

        #UDP Receiver 
        self.received_data_queue = received_data_queue
        self.UDP_Receive_PORT = 17778
        self.receive_serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_serversocket.bind((self.ip_addr, self.UDP_Receive_PORT))

        #UDP Sender
        self.send_data_queue = send_data_queue
        self.send_to_ip_addr = '10.0.0.43'
        self.UDP_Send_PORT = 15555
        self.send_serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No bind component for sender
        
        
    
    def receive_data(self):
        """
        Looping blocking call that receives data from UDP source
        data is then put into Queue that can be read from outside
        the thread
        """

        while True:
    
            #print('Listening')
            #print(self.ip_addr)  
            data, addr = self.receive_serversocket.recvfrom(65507)
            self.received_data_queue.put(data)



    def send_data(self):
        """
        Looping call that send ML data outbound
        as quickly as it's placed into send_data_queue
        """

        while True:

            #print("Sending")
            self.send_serversocket.sendto(self.send_data_queue.get(), (self.send_to_ip_addr, self.UDP_Send_PORT))
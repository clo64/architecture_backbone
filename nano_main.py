import nano_server as ns
from keras.models import model_from_json
import numpy as np
import tensorflow as tf
import socket
import queue as Qthread
from collections import deque
import threading
import multiprocessing as mp
import os
import pickle
import time

def red_blue_buffer(nano_serv, cross_process_signal, cross_process_data):

    received_data_queue_red = deque(maxlen=32)
    received_data_queue_blue = deque(maxlen=32)
    
    red_active = True
    blue_active = False

    receiver_thread = threading.Thread(target=nano_serv.receive_data, args=())
    receiver_thread.start()

    first_capture = True

    while True:

        start = time.time()

        print(len(received_data_queue_red))
        print(len(received_data_queue_blue))

        try:

            if cross_process_signal.get_nowait() == 'switch':
                print("Buffer Switch")

                if red_active:
                    cross_process_data.put(received_data_queue_red)
                    cross_process_data.join()
                    received_data_queue_red.clear()
                    red_active = not red_active
                    blue_active = not blue_active

                    if first_capture == True:
                        first_capture = not first_capture

                elif blue_active:
                    cross_process_data.put(received_data_queue_blue)
                    cross_process_data.join()
                    received_data_queue_blue.clear()
                    blue_active = not blue_active
                    red_active = not red_active

                    if first_capture == True:
                        first_capture = not first_capture

        except Qthread.Empty:
            print('No Switch')

        ##-- Red Buffer --##
        if first_capture or red_active:

            try:

                print("red buffer")

                received_data_queue_red.append(received_data_queue.get(block=True, timeout=3))

                #logic to send the first buffer when it's full
                if (len(received_data_queue_red) == 32) and first_capture:
                    cross_process_data.put(received_data_queue_red)
                    cross_process_data.join()
                    received_data_queue_red.clear()
                    #first buffer switch indicated here
                    red_active = False
                    blue_active = True
                    first_capture = not first_capture

            except Qthread.Empty:

                print("Queue timeout, reset")
                red_active = False
                blue_active = False
                first_capture = True
                received_data_queue.queue.clear()
                received_data_queue_red.clear()
                received_data_queue_blue.clear()
            
        ##-- Blue Buffer --##
        elif blue_active:

            print("blue buffer")
            
            try:

                received_data_queue_blue.append(received_data_queue.get(block=True, timeout=3))
    
            except Qthread.Empty:

                print("Queue timeout, reset")
                red_active = False
                blue_active = False
                first_capture = True
                received_data_queue.queue.clear()
                received_data_queue_red.clear()
                received_data_queue_blue.clear()
            
        end = time.time()
        print(end-start)

def inference_machine(nano_serv, cross_process_signal, cross_process_data):

    sender_thread = threading.Thread(target=nano_serv.send_data, args=())
    sender_thread.start()

    heatmap_list = []
    i = 0

    print("Ill run inference")
    log_File = open('log_File.txt', 'w')

    while True:
   
        latest_frames = cross_process_data.get(block=True)
        cross_process_data.task_done()
        #capture = passTest.pop()
        
        
        #if this is the first deque sent over then it will be 32 in length
        #check for this first
        if(len(latest_frames)==32):
            for item in latest_frames:
                #extract each pickled heatmap, then unpickle it
                heatmap_list.append(pickle.loads(item))
        print(len(heatmap_list))
        print(heatmap_list[0])

        """
        #Was used to log the arrays and check for frame numbering continuity
        for item in passTest:
            for_test_print = pickle.loads(item)
            for_test_print[0][0][0].tofile(log_File, sep=" ")
        """

        ##-- Here we need heatmap stacking elements

        """
        ##--time.sleep used to simulate inference delay. Should be much
        ##--longer than a real delay
        time.sleep(2)
        """

        #passTest.clear()
        cross_process_signal.put('switch')
        
   

if __name__ == "__main__":

    cross_process_signal = mp.Queue()
    cross_process_data = mp.JoinableQueue()
    received_data_queue = Qthread.Queue(5)
    send_data_queue =  Qthread.Queue(5)

    nano_serv = ns.Nano_Server(received_data_queue, send_data_queue)

    pid = os.fork()

    if(pid):
        red_blue_buffer(nano_serv, cross_process_signal, cross_process_data)
    else:
        inference_machine(nano_serv, cross_process_signal, cross_process_data)
    
        """
        #This code tests the raw input/output functionality 
        #of the pipeline
        start_time = time.time()
        data = received_data_queue.get()
        elapsed_time = time.time() - start_time
        print(elapsed_time)
        #print(data)
        send_data_queue.put(data)
        """
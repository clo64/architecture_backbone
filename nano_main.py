import nano_server as ns
import numpy as np
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

        #print(len(received_data_queue_red))
        #print(len(received_data_queue_blue))

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
            #should simply conintue running
            pass

        ##-- Red Buffer --##
        if first_capture or red_active:

            try:

                #print("red buffer")

                received_data_queue_red.appendleft(received_data_queue.get(block=True, timeout=3))

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

            #print("blue buffer")
            
            try:

                received_data_queue_blue.appendleft(received_data_queue.get(block=True, timeout=3))
    
            except Qthread.Empty:

                print("Queue timeout, reset")
                red_active = False
                blue_active = False
                first_capture = True
                received_data_queue.queue.clear()
                received_data_queue_red.clear()
                received_data_queue_blue.clear()

def inference_machine(nano_serv, cross_process_signal, cross_process_data):

    from keras.models import model_from_json
    import tensorflow as tf

    physical_devices = tf.config.list_physical_devices('GPU') 
    try: 
        tf.config.experimental.set_memory_growth(physical_devices[0], True) 
        assert tf.config.experimental.get_memory_growth(physical_devices[0]) 
    except: 
        # Invalid device or cannot modify virtual devices once initialized.
        print("init device cannot modify") 
        pass

    json_file = open('saved_model.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    loaded_model.load_weights('saved_model.h5')
    print('Loaded model from disk.')

    sender_thread = threading.Thread(target=nano_serv.send_data, args=())
    sender_thread.start()
    
    while True:
   
        latest_frames = cross_process_data.get(block=True)
        cross_process_data.task_done()
        #capture = passTest.pop()
        
        #if this is the first deque sent over then it will be 32 in length
        #check for this first
        if(len(latest_frames)==32):
            heatmap_list = []
            for i in range(len(latest_frames)):
                heatmap_list.append(pickle.loads(latest_frames.pop()))
            heatmap_arr = np.array(heatmap_list)
            horizontal_heatmap = np.stack(heatmap_arr[:, 0])
            vertical_heatmap = np.stack(heatmap_arr[:, 1])
            horizontal_heatmap = np.reshape(horizontal_heatmap, (1,32,57,28,1))
            vertical_heatmap = np.reshape(vertical_heatmap, (1,32,37,28,1))
            model_input = ((horizontal_heatmap, vertical_heatmap), ())
            start = time.time()
            predictions = loaded_model.predict(model_input)
            end = time.time()
            print(end-start)
            print(predictions)
            nano_serv.send_data_queue.put(predictions)
            print('inference done')
        
        else:
            #if less than 32 items we want to reuse the old heatmap_list and simply knock off the old entries and 
            #slice in the new ones. 
            #here, slice the beginning frame off the heatmap_list to make room for appending the new ones. 
            heatmap_list = heatmap_list[len(latest_frames):]
            for i in range(len(latest_frames)):
                heatmap_list.append(pickle.loads(latest_frames.pop()))
            heatmap_arr = np.array(heatmap_list)
            horizontal_heatmap = np.stack(heatmap_arr[:, 0])
            vertical_heatmap = np.stack(heatmap_arr[:, 1])
            horizontal_heatmap = np.reshape(horizontal_heatmap, (1,32,57,28,1))
            vertical_heatmap = np.reshape(vertical_heatmap, (1,32,37,28,1))
            model_input = ((horizontal_heatmap, vertical_heatmap), ())
            start = time.time()
            predictions = loaded_model.predict(model_input)
            end = time.time()
            print(end-start)
            nano_serv.send_data_queue.put(predictions)  
            print('inference done')
        
        cross_process_signal.put('switch')
        
   

if __name__ == "__main__":

    cross_process_signal = mp.Queue()
    cross_process_data = mp.JoinableQueue()
    received_data_queue = Qthread.Queue(5)
    send_data_queue =  Qthread.Queue(5)

    nano_serv = ns.Nano_Server(received_data_queue, send_data_queue)

    pid = os.fork()

    if(pid):
        time.sleep(30)
        red_blue_buffer(nano_serv, cross_process_signal, cross_process_data)
    else:  
        inference_machine(nano_serv, cross_process_signal, cross_process_data)
    
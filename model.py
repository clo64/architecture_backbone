from keras.models import model_from_json
import numpy as np
import tensorflow as tf
import time

# load the model
json_file = open('saved_model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
loaded_model.load_weights('saved_model.h5')
print('Loaded model from disk.')

# load the heatmap
heatmaps = np.load('heatmaps.npz', allow_pickle=True)['arr_0']
print('Loaded the heatmaps')

# time the model
start_time = time.time()
prediction_counter = 0

for i in range(32, len(heatmaps)):
    # swap out the heatmaps
    heatmap_list = heatmaps[(i-32):i]

    # recreate the horizontal and vertical heatmpas
    heatmap_arr = np.array(heatmap_list)
    horizontal_heatmap = np.stack(heatmap_arr[:, 0])
    vertical_heatmap = np.stack(heatmap_arr[:, 1])

    # adjust array sizes
    horizontal_heatmap = np.reshape(horizontal_heatmap, (1,32,57,28,1))
    vertical_heatmap = np.reshape(vertical_heatmap, (1,32,37,28,1))

    # run the model
    model_input = ((horizontal_heatmap, vertical_heatmap), ())
    predictions = loaded_model.predict(model_input)

    # keep track
    prediction_counter += 1

stop_time = time.time()

total_time = stop_time - start_time
average_fps = prediction_counter / total_time
average_time = total_time / prediction_counter

print("Total time:", total_time, "seconds to run", prediction_counter, "predictions.")
print("Averaging", average_time, "seconds per set of 32 heat maps.")
print("Averaging", average_fps, "frames processed per second.")




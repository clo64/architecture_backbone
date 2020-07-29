import threading

switch = threading.Event()
switch.clear()

print(switch.isSet())
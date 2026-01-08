
### Example run using Sockets
- In terminal 1:
```
socat UNIX-LISTEN:/tmp/accel_2048.sock,fork -
# Type any messages
# To end: ctrl + c
```
- In terminal 2 run the Python file with `drava.init("socket")`:
```
python run.py
```

### Example run using Jetstream
- In terminal 1:
```
cd ~/nats_binary
./nats-server -js -sd ./jsdata
# Type any messages
# To end: ctrl + c
```
- In terminal 2 run the Python file with `drava.init("nats")`:
```
python run.py
```
- In terminal 3, publish dummy JSON:
```shell
cd examples/dataflow
pip install -r requirements.txt
python publisher_jetstream.py
```


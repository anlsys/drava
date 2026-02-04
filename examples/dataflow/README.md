
### Run using Socket

- In terminal 1, create the FIFO and start `socat` to forward FIFO input into the socket:

```shell
# Create the FIFO if it doesn't already exist (suppress error if it does)
mkfifo /tmp/drava_in 2>/dev/null || true

# Start socat to forward everything from the FIFO into the Unix domain socket
socat -u OPEN:/tmp/drava_in,rdonly,ignoreeof UNIX-LISTEN:/tmp/accel_2048.sock,fork
```

- In terminal 2, run the publisher script

```shell
cd examples/dataflow
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python publisher_socket.py
```

- In terminal 3, run the app ensuring it is using `"export DRAVA_TRANSPORT=socket"`:

```shell
cd examples/dataflow
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
- In terminal 2 run the Python file with `"export DRAVA_TRANSPORT=nats"`:
```
python run.py
```
- In terminal 3, publish dummy JSON:
```shell
cd examples/dataflow
pip install -r requirements.txt
python publisher_jetstream.py
```


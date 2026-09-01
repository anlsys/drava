
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

- In terminal 3, run the app. With no `DRAVA_STAGE_CONFIG` set, the runtime uses
  the **socket** transport by default, matching this data flow:

```shell
cd examples/dataflow
python app.py
```


### Example run using Jetstream
- In terminal 1:
```
cd ~/nats_binary
./nats-server -js -sd ./jsdata
# Type any messages
# To end: ctrl + c
```
- In terminal 2 run the app. To use the JetStream transport, create a
  `pipeline.yaml` with `transport.type: nats` and a `stage1` entry (see
  `examples/ptychonn/pipeline.yaml`), then point the runtime at it:
```
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
export DRAVA_STAGE_NAME=stage1
python app.py
```
- In terminal 3, run the the publisher script:
```shell
cd examples/dataflow
pip install -r requirements.txt
python publisher_jetstream.py
```


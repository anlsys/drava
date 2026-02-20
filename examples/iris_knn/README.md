## Iris Dataset Inference Example

This example demonstrates an end-to-end publisher (Jetstream) → Drava (consumer) → app inference
workflow using a pre-trained KNN model. A one-row Iris feature vector is published through JetStream,
delivered by Drava as raw bytes, and consumed by the app for KNN inference.

### Dataset and model

The Iris dataset is a classic benchmark in pattern recognition containing 150 samples (50 per class) of 3 Iris
species. Each sample includes 4 numeric features: [sepal length, sepal width, petal length, petal width]
The target label is one of the species: [Iris setosa, Iris versicolor, Iris virginica]

We generate the [iris_knn_model.pkl](iris_knn_model.pkl) file by training
a 3-NN classifier on the Iris dataset using scikit-learn and serializing it with joblib.
At inference time, the app receives a single feature row with the four feature values.
Using the fixed KNN model, the app returns the predicted species name.


## Build

Follow the build instructions for Drava from the root [README file](../../README.md). To ensure Jetstream support, put the `NATS_ROOT` path in the environment variable.

## Transport layers

Transport layer → Drava → app.py

Supported transport layers:

- JetStream (NATS JetStream)
- Socket (Unix domain socket)

Both ultimately deliver raw frame bytes to `app.py` (no JSON/base64).

## JetStream Transport

JetStream → (pull) → Drava → (push) → app.py

1. Publisher [publisher_jetstream.py](publisher_jetstream.py):
   - Creates one Iris sample using NumPy (`float32[4]`).
   - Publishes the raw bytes to JetStream subject (`frames.raw`).

2. Transport Layer (JetStream + Drava runtime):
   - JetStream provides a reliable messaging backend.
   - Drava receives the raw message from the JetStream device.
   - Drava invokes the registered Python callback (`func`) with the message payload.

3. Application (`app.py`):
   - Drava passes raw bytes to the application callback.
   - Application reconstructs a NumPy row vector (`1x4`, float32).
   - A KNN model (`iris_knn_model.pkl`) is loaded once at startup.
   - The model predicts the Iris species.
   - Application prints the predicted class.

### Run using Jetstream

- In terminal 1, run the NATS server

```shell
cd ~/nats_binary
./nats-server -js -sd ./jsdata
```

- In terminal 2, run the publisher script

```shell
cd examples/iris_knn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python publisher_jetstream.py
```

- In terminal 3, run the app ensuring it is using `"export DRAVA_TRANSPORT=nats"`:

```shell
cd examples/iris_knn
source venv/bin/activate
python app.py
```

## Socket Transport

The socket backend provides a lightweight alternative to JetStream using a Unix domain socket.
The data flow is:

```shell
publisher_socket.py → FIFO (/tmp/drava_in) → socat → /tmp/accel_2048.sock → Drava → app.py
```

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
cd examples/iris_knn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python publisher_socket.py
```

- In terminal 3, run the app ensuring it is using `"export DRAVA_TRANSPORT=socket"`:

```shell
cd examples/iris_knn
source venv/bin/activate
python app.py
```

### Common error and fix
#### `Drava` module error in Python app
#### Scenario
While running `python app.py` may raise the following error:
```shell
Traceback (most recent call last):
File "/home/ashovon/drava/examples/iris_knn/app.py", line 1, in <module>
import drava
ModuleNotFoundError: No module named 'drava'
```
This error shows Python cannot locate the Drava Python bindings. This happens because the drava Python module is generated inside build directory (e.g., `build-debug-nats`) and is not installed into the virtual environment.

#### Solution
Add the build directory to `PYTHONPATH` before running the app.
```shell
cd ~/drava/build-debug-nats # the build dir
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### References

- [Iris plants dataset](https://scikit-learn.org/stable/datasets/toy_dataset.html#iris-plants-dataset)
- [KNeighborsClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html)

## Iris Dataset Inference Example

This example demonstrates an end-to-end publisher (Jetstream) → Drava (consumer) → app inference
workflow using a pre-trained KNN model. A one-row Iris feature vector is published through JetStream,
delivered by Drava, decoded by the app which then classify it using a pre-trained KNN model.

### Dataset and model

The Iris dataset is a classic benchmark in pattern recognition containing 150 samples (50 per class) of 3 Iris
species. Each sample includes 4 numeric features: [sepal length, sepal width, petal length, petal width]
The target label is one of the species: [Iris setosa, Iris versicolor, Iris virginica]

We generate the [iris_knn_model.pkl](iris_knn_model.pkl) file by training
a 3-NN classifier on the Iris dataset using scikit-learn and serializing it with joblib.
At inference time, the app receives a single feature row with the four feature values.
Using the fixed KNN model, the app returns the predicted species name.

## Workflow

JetStream → (pull) → Drava → (push) → app.py

1. **Publisher (`publisher.py`)**
    - Creates a single-row Iris sample using NumPy/Pandas.
    - Encodes the feature matrix into base64 for transport.
    - Packages metadata (rows, cols, dtype, frame_id, feature names).
    - Publishes the message to a JetStream subject (`frames.raw`).

2. **Transport Layer (JetStream + Drava runtime)**
    - JetStream provides a reliable messaging backend.
    - Drava receives the raw message from the JetStream device.
    - Drava invokes the registered Python callback (`func`) with the message payload.

3. **Application (`app.py`)**
    - Drava passes the JSON payload to the application.
    - Application reconstructs the NumPy array and DataFrame.
    - A KNN model (`iris_knn_model.pkl`) is loaded once at startup.
    - The model predicts the Iris species.
    - Application prints the prediction with its associated `frame_id`.

### Build

Follow the build instructions for Drava from the root [README file](../../README.md).

### Run using Jetstream

- In terminal 1, run the NATS server

```bash
cd ~/nats_binary
./nats-server -js -sd ./jsdata
```

- In terminal 2, run the publisher script

```bash
cd examples/iris_knn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python publisher.py
```

- In terminal 3, run the app

```bash
cd examples/iris_knn
source venv/bin/activate
python app.py
```

### References

- [Iris plants dataset](https://scikit-learn.org/stable/datasets/toy_dataset.html#iris-plants-dataset)
- [KNeighborsClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html)
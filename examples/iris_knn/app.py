import drava
import base64, json
import numpy as np
import pandas as pd
import joblib

# Load once at module import
model = joblib.load("iris_knn_model.pkl")
iris_target_names = ['setosa', 'versicolor', 'virginica']

def func(s: str):
    """
    s is a JSON string that contains:
      rows, cols, dtype, order, feature_names, frame_id, data_b64
    """
    print("Hello Python, received: {}".format(s))
    # Parse
    msg = json.loads(s)

    rows = int(msg["rows"])
    cols = int(msg["cols"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")
    feature_names = msg.get("feature_names")

    # Decode base64 -> bytes -> ndarray
    raw = base64.b64decode(msg["data_b64"])
    expected_bytes = rows * cols * dtype.itemsize
    if len(raw) != expected_bytes:
        raise ValueError(f"payload size mismatch: got {len(raw)} bytes, expected {expected_bytes}")

    arr = np.frombuffer(raw, dtype=dtype)
    arr = arr.reshape((rows, cols), order=order)

    # Rebuild DataFrame with correct columns (if provided)
    if feature_names is not None:
        if len(feature_names) != cols:
            raise ValueError("feature_names length does not match 'cols'")
        df = pd.DataFrame(arr, columns=feature_names)
    else:
        df = pd.DataFrame(arr)

    # Inference
    pred = model.predict(df)
    predicted_species = iris_target_names[int(pred[0])]

    print(f"frame_id={msg.get('frame_id')} | prediction={predicted_species}")

# initialization supports nats or socket
drava.init("nats")
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()





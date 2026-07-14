import drava
import numpy as np
import joblib

# Load once at module import
model = joblib.load("iris_knn_model.pkl")
iris_target_names = ['setosa', 'versicolor', 'virginica']
FRAME_DTYPE = np.float32
FRAME_VALUES = 4
FRAME_BYTES = FRAME_VALUES * np.dtype(FRAME_DTYPE).itemsize

def func(frames):
    for f in frames:
        if len(f) != FRAME_BYTES:
            raise ValueError(
                f"payload size mismatch: got {len(f)} bytes, expected {FRAME_BYTES}"
            )
        arr = np.frombuffer(f, dtype=FRAME_DTYPE).reshape((1, FRAME_VALUES), order="C")
        pred = model.predict(arr)
        predicted_species = iris_target_names[int(pred[0])]

        print(f"prediction={predicted_species}")

# Set the transport using env var variable
# export DRAVA_TRANSPORT=nats/socket
drava.run(func)

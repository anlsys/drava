import pandas as pd
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier
import joblib

# Load the iris dataset
iris = load_iris()
X = pd.DataFrame(iris.data, columns=iris.feature_names)
y = pd.Series(iris.target)

# Create a KNN classifier instance
knn = KNeighborsClassifier(n_neighbors=3)

# Train the model
knn.fit(X, y)

# Save the trained model to a file
joblib.dump(knn, 'iris_knn_model.pkl')

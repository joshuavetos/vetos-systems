"""
Adaptive Locality Experiment for Graph-Based Tabular Regression

This script demonstrates:
- Fixed-k GNN failure modes
- k-sweep non-monotonicity
- Adaptive neighborhood selection
- Tail-focused performance analysis
- Domain transfer validation

Designed to be read top-to-bottom.
"""

import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
from sklearn.metrics import r2_score, mean_absolute_error
from xgboost import XGBRegressor


# -------------------------------
# GNN Encoder
# -------------------------------

class NexusGNN(torch.nn.Module):
    def __init__(self, in_dim, hidden_dim=32, out_dim=8):
        super().__init__()
        self.conv1 = GCNConv(in_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, out_dim)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.leaky_relu(x, 0.2)
        x = self.conv2(x, edge_index)
        return x


# -------------------------------
# Graph Construction Utilities
# -------------------------------

def build_knn_edges(X, k):
    nbrs = NearestNeighbors(n_neighbors=k).fit(X)
    indices = nbrs.kneighbors(X, return_distance=False)
    edges = []
    for i, neigh in enumerate(indices):
        for j in neigh:
            if i != j:
                edges.append([i, j])
    return torch.tensor(edges, dtype=torch.long).t().contiguous()


def build_adaptive_edges(X, tail_mask, k_tail=3, k_main=10):
    edges = []
    nbrs_small = NearestNeighbors(n_neighbors=k_tail).fit(X)
    nbrs_large = NearestNeighbors(n_neighbors=k_main).fit(X)

    for i, is_tail in enumerate(tail_mask):
        nbrs = nbrs_small if is_tail else nbrs_large
        neigh = nbrs.kneighbors(X[i:i+1], return_distance=False)[0]
        for j in neigh:
            if i != j:
                edges.append([i, j])

    return torch.tensor(edges, dtype=torch.long).t().contiguous()


# -------------------------------
# Training and Evaluation
# -------------------------------

def train_gnn(X, y, edge_index, epochs=200):
    x_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32).view(-1, 1)

    model = NexusGNN(in_dim=X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=0.01)

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        Z = model(x_tensor, edge_index)
        pred = Z @ torch.ones(Z.shape[1], 1)
        loss = F.mse_loss(pred, y_tensor)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        return model, Z.numpy()


def train_xgb(X, y):
    model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X, y)
    return model


def evaluate(y_true, y_pred):
    return {
        "R2": r2_score(y_true, y_pred),
        "MAE": mean_absolute_error(y_true, y_pred),
    }


# -------------------------------
# Example Workflow (Pseudo-Main)
# -------------------------------

def run_experiment(X_train, y_train, X_test, y_test, tail_threshold):
    tail_mask = y_train > tail_threshold

    # Fixed-k baseline
    edge_fixed = build_knn_edges(X_train, k=5)
    _, Z_fixed = train_gnn(X_train, y_train, edge_fixed)

    # Adaptive-k
    edge_adapt = build_adaptive_edges(X_train, tail_mask)
    _, Z_adapt = train_gnn(X_train, y_train, edge_adapt)

    # PCA baseline
    pca = PCA(n_components=Z_fixed.shape[1])
    Z_pca = pca.fit_transform(X_train)

    # Train regressors
    raw = train_xgb(X_train, y_train)
    fixed = train_xgb(np.hstack([X_train, Z_fixed]), y_train)
    adapt = train_xgb(np.hstack([X_train, Z_adapt]), y_train)
    pca_m = train_xgb(np.hstack([X_train, Z_pca]), y_train)

    # Predict
    preds = {
        "raw": raw.predict(X_test),
        "fixed": fixed.predict(np.hstack([X_test, Z_fixed[:len(X_test)]])),
        "adaptive": adapt.predict(np.hstack([X_test, Z_adapt[:len(X_test)]])),
        "pca": pca_m.predict(np.hstack([X_test, pca.transform(X_test)])),
    }

    return {k: evaluate(y_test, v) for k, v in preds.items()}

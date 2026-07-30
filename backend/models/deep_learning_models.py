# models/deep_learning_models.py — LSTM/GRU Deep Learning Models for Forecasting

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict, List, Optional
import warnings
import os
import pickle
warnings.filterwarnings("ignore")

# Check for GPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[DeepLearning] Using device: {DEVICE}")


class TimeSeriesDataset(Dataset):
    """PyTorch Dataset for time series sequences."""
    
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class LSTMForecaster(nn.Module):
    """
    LSTM-based energy demand forecaster.
    
    Architecture:
    - Multi-layer LSTM with dropout
    - Fully connected output layers
    - Supports sequence-to-one and sequence-to-sequence
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_size: int = 1,
        bidirectional: bool = False
    ):
        super(LSTMForecaster, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * self.num_directions, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size)
        )
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use last hidden state
        if self.bidirectional:
            hidden = torch.cat((h_n[-2], h_n[-1]), dim=1)
        else:
            hidden = h_n[-1]
        
        out = self.fc(hidden)
        return out


class GRUForecaster(nn.Module):
    """
    GRU-based energy demand forecaster.
    
    GRU is faster than LSTM with comparable performance.
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_size: int = 1,
        bidirectional: bool = False
    ):
        super(GRUForecaster, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * self.num_directions, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size)
        )
    
    def forward(self, x):
        gru_out, h_n = self.gru(x)
        
        if self.bidirectional:
            hidden = torch.cat((h_n[-2], h_n[-1]), dim=1)
        else:
            hidden = h_n[-1]
        
        out = self.fc(hidden)
        return out


class LSTMAutoencoder(nn.Module):
    """
    LSTM Autoencoder for anomaly detection.
    
    Learns to reconstruct normal patterns; high reconstruction
    error indicates anomalies.
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        latent_size: int = 32,
        num_layers: int = 1
    ):
        super(LSTMAutoencoder, self).__init__()
        
        # Encoder
        self.encoder_lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.encoder_fc = nn.Linear(hidden_size, latent_size)
        
        # Decoder
        self.decoder_fc = nn.Linear(latent_size, hidden_size)
        self.decoder_lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.output_fc = nn.Linear(hidden_size, input_size)
        
        self.hidden_size = hidden_size
        self.latent_size = latent_size
    
    def encode(self, x):
        _, (h_n, _) = self.encoder_lstm(x)
        latent = self.encoder_fc(h_n[-1])
        return latent
    
    def decode(self, latent, seq_len):
        hidden = self.decoder_fc(latent)
        hidden = hidden.unsqueeze(1).repeat(1, seq_len, 1)
        decoder_out, _ = self.decoder_lstm(hidden)
        out = self.output_fc(decoder_out)
        return out
    
    def forward(self, x):
        latent = self.encode(x)
        reconstructed = self.decode(latent, x.size(1))
        return reconstructed


class DeepLearningTrainer:
    """
    Trainer class for deep learning forecasting models.
    Handles data preparation, training, and prediction.
    """
    
    def __init__(
        self,
        model_type: str = "lstm",
        sequence_length: int = 24,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        epochs: int = 100,
        early_stopping_patience: int = 10,
        bidirectional: bool = False
    ):
        self.model_type = model_type
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.early_stopping_patience = early_stopping_patience
        self.bidirectional = bidirectional
        
        self.model = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.feature_cols = None
        self.target_col = None
        self.training_history = {"train_loss": [], "val_loss": []}
        self.best_val_loss = float("inf")
    
    def _create_sequences(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM/GRU input."""
        X_seq, y_seq = [], []
        
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            y_seq.append(y[i + self.sequence_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def _get_feature_cols(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns for training."""
        exclude = {"timestamp", "is_anomaly", "failure_label", "efficiency_score"}
        return [c for c in df.select_dtypes(include=[np.number]).columns 
                if c not in exclude and c != self.target_col]
    
    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = "consumption_kwh",
        val_split: float = 0.2
    ) -> "DeepLearningTrainer":
        """
        Train the deep learning model.
        """
        self.target_col = target_col
        self.feature_cols = self._get_feature_cols(df)
        
        # Prepare data
        X = df[self.feature_cols].fillna(0).values
        y = df[target_col].values.reshape(-1, 1)
        
        # Scale data
        X_scaled = self.scaler_X.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(y)
        
        # Create sequences
        X_seq, y_seq = self._create_sequences(X_scaled, y_scaled)
        
        # Train/val split (time-series aware - no shuffle)
        split_idx = int(len(X_seq) * (1 - val_split))
        X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]
        
        # Create data loaders
        train_dataset = TimeSeriesDataset(X_train, y_train)
        val_dataset = TimeSeriesDataset(X_val, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)
        
        # Initialize model
        input_size = X_seq.shape[2]
        
        if self.model_type.lower() == "lstm":
            self.model = LSTMForecaster(
                input_size=input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                dropout=self.dropout,
                bidirectional=self.bidirectional
            )
        elif self.model_type.lower() == "gru":
            self.model = GRUForecaster(
                input_size=input_size,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                dropout=self.dropout,
                bidirectional=self.bidirectional
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        self.model = self.model.to(DEVICE)
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training loop
        best_model_state = None
        patience_counter = 0
        
        print(f"[{self.model_type.upper()}] Training on {len(X_train)} sequences...")
        
        for epoch in range(self.epochs):
            # Training phase
            self.model.train()
            train_loss = 0
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(DEVICE)
                batch_y = batch_y.to(DEVICE)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation phase
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    batch_X = batch_X.to(DEVICE)
                    batch_y = batch_y.to(DEVICE)
                    
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)
            
            # Update learning rate
            scheduler.step(val_loss)
            
            # Record history
            self.training_history["train_loss"].append(train_loss)
            self.training_history["val_loss"].append(val_loss)
            
            # Early stopping check
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                best_model_state = self.model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{self.epochs} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")
            
            if patience_counter >= self.early_stopping_patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break
        
        # Load best model
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
        
        # Calculate final metrics
        self.model.eval()
        with torch.no_grad():
            X_val_tensor = torch.FloatTensor(X_val).to(DEVICE)
            y_pred_scaled = self.model(X_val_tensor).cpu().numpy()
            y_pred = self.scaler_y.inverse_transform(y_pred_scaled)
            y_true = self.scaler_y.inverse_transform(y_val)
            
            mae = np.mean(np.abs(y_pred - y_true))
            rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))
            mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
        
        print(f"[{self.model_type.upper()}] Final Metrics: MAE={mae:.2f} | RMSE={rmse:.2f} | MAPE={mape:.1f}%")
        
        return self
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data."""
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")
        
        X = df[self.feature_cols].fillna(0).values
        X_scaled = self.scaler_X.transform(X)
        
        # Create sequences
        X_seq = []
        for i in range(len(X_scaled) - self.sequence_length + 1):
            X_seq.append(X_scaled[i:i + self.sequence_length])
        X_seq = np.array(X_seq)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_seq).to(DEVICE)
            y_pred_scaled = self.model(X_tensor).cpu().numpy()
            y_pred = self.scaler_y.inverse_transform(y_pred_scaled)
        
        return y_pred.flatten()
    
    def forecast_next_n_hours(self, df: pd.DataFrame, n: int = 24) -> pd.DataFrame:
        """
        Forecast energy consumption for the next N hours.
        Uses recursive multi-step forecasting.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")
        
        # Get last sequence
        X = df[self.feature_cols].fillna(0).values
        X_scaled = self.scaler_X.transform(X)
        
        last_sequence = X_scaled[-self.sequence_length:].copy()
        
        forecasts = []
        last_time = df["timestamp"].iloc[-1]
        
        self.model.eval()
        with torch.no_grad():
            for i in range(n):
                # Predict next step
                X_tensor = torch.FloatTensor(last_sequence).unsqueeze(0).to(DEVICE)
                pred_scaled = self.model(X_tensor).cpu().numpy()[0, 0]
                pred = self.scaler_y.inverse_transform([[pred_scaled]])[0, 0]
                
                # Store forecast
                forecast_time = last_time + pd.Timedelta(hours=i + 1)
                forecasts.append({
                    "timestamp": forecast_time,
                    "forecast_kwh": pred,
                    "lower_bound": pred * 0.9,
                    "upper_bound": pred * 1.1
                })
                
                # Update sequence for next prediction (shift and add new prediction)
                new_features = last_sequence[-1].copy()
                new_features[0] = pred_scaled  # Assuming first feature is target-related
                last_sequence = np.vstack([last_sequence[1:], new_features])
        
        return pd.DataFrame(forecasts)
    
    def get_training_history(self) -> Dict:
        """Get training history for visualization."""
        return {
            "epochs": list(range(1, len(self.training_history["train_loss"]) + 1)),
            "train_loss": self.training_history["train_loss"],
            "val_loss": self.training_history["val_loss"],
            "best_val_loss": self.best_val_loss
        }
    
    def save(self, path: str):
        """Save the trained model."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        state = {
            "model_state": self.model.state_dict() if self.model else None,
            "model_type": self.model_type,
            "sequence_length": self.sequence_length,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
            "bidirectional": self.bidirectional,
            "scaler_X": self.scaler_X,
            "scaler_y": self.scaler_y,
            "feature_cols": self.feature_cols,
            "target_col": self.target_col,
            "training_history": self.training_history,
            "best_val_loss": self.best_val_loss
        }
        
        with open(path, "wb") as f:
            pickle.dump(state, f)
        
        print(f"[{self.model_type.upper()}] Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> "DeepLearningTrainer":
        """Load a trained model."""
        with open(path, "rb") as f:
            state = pickle.load(f)
        
        trainer = cls(
            model_type=state["model_type"],
            sequence_length=state["sequence_length"],
            hidden_size=state["hidden_size"],
            num_layers=state["num_layers"],
            dropout=state["dropout"],
            bidirectional=state["bidirectional"]
        )
        
        trainer.scaler_X = state["scaler_X"]
        trainer.scaler_y = state["scaler_y"]
        trainer.feature_cols = state["feature_cols"]
        trainer.target_col = state["target_col"]
        trainer.training_history = state["training_history"]
        trainer.best_val_loss = state["best_val_loss"]
        
        # Reconstruct model
        if state["model_state"] is not None:
            input_size = len(state["feature_cols"])
            
            if state["model_type"].lower() == "lstm":
                trainer.model = LSTMForecaster(
                    input_size=input_size,
                    hidden_size=state["hidden_size"],
                    num_layers=state["num_layers"],
                    dropout=state["dropout"],
                    bidirectional=state["bidirectional"]
                )
            else:
                trainer.model = GRUForecaster(
                    input_size=input_size,
                    hidden_size=state["hidden_size"],
                    num_layers=state["num_layers"],
                    dropout=state["dropout"],
                    bidirectional=state["bidirectional"]
                )
            
            trainer.model.load_state_dict(state["model_state"])
            trainer.model = trainer.model.to(DEVICE)
        
        print(f"[{trainer.model_type.upper()}] Model loaded from {path}")
        return trainer


# Model paths
LSTM_MODEL_PATH = "models/saved/lstm_forecaster.pkl"
GRU_MODEL_PATH = "models/saved/gru_forecaster.pkl"


def train_deep_learning_models(df: pd.DataFrame) -> Dict[str, DeepLearningTrainer]:
    """
    Train both LSTM and GRU models on the dataset.
    """
    print("\n" + "=" * 50)
    print("TRAINING DEEP LEARNING MODELS")
    print("=" * 50)
    
    models = {}
    
    # Train LSTM
    print("\n[1/2] Training LSTM...")
    lstm_trainer = DeepLearningTrainer(
        model_type="lstm",
        sequence_length=24,
        hidden_size=128,
        num_layers=2,
        dropout=0.2,
        epochs=50,
        early_stopping_patience=10
    )
    lstm_trainer.fit(df)
    lstm_trainer.save(LSTM_MODEL_PATH)
    models["lstm"] = lstm_trainer
    
    # Train GRU
    print("\n[2/2] Training GRU...")
    gru_trainer = DeepLearningTrainer(
        model_type="gru",
        sequence_length=24,
        hidden_size=128,
        num_layers=2,
        dropout=0.2,
        epochs=50,
        early_stopping_patience=10
    )
    gru_trainer.fit(df)
    gru_trainer.save(GRU_MODEL_PATH)
    models["gru"] = gru_trainer
    
    print("\n[Deep Learning] All models trained successfully!")
    return models


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")
    from data.pipeline import run_pipeline
    
    # Load data
    df = run_pipeline()
    
    # Train models
    models = train_deep_learning_models(df)
    
    # Test forecasting
    print("\n=== LSTM 24-hour Forecast ===")
    lstm_forecast = models["lstm"].forecast_next_n_hours(df, n=24)
    print(lstm_forecast.head())
    
    print("\n=== GRU 24-hour Forecast ===")
    gru_forecast = models["gru"].forecast_next_n_hours(df, n=24)
    print(gru_forecast.head())

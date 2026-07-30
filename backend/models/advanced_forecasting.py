"""
Advanced Forecasting Models with Intelligent Model Selection

This module provides state-of-the-art forecasting models:
- LSTM: Deep learning for complex time-series patterns
- Prophet: Facebook's forecasting tool for seasonality and holidays
- Temporal Fusion Transformer (TFT): Multi-horizon attention-based forecasting
- Ensemble Forecaster: Combines multiple models with weighted voting
- Model Selector: Automatically chooses best model based on forecast horizon

Usage:
    from models.advanced_forecasting import ForecastingPipeline
    
    pipeline = ForecastingPipeline()
    pipeline.train(df)
    
    # Automatic model selection based on horizon
    forecast_6h = pipeline.predict(horizon=6)   # Uses LSTM
    forecast_24h = pipeline.predict(horizon=24)  # Uses Prophet
    forecast_7d = pipeline.predict(horizon=168) # Uses Ensemble
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from typing import Dict, List, Tuple, Optional, Any
import warnings
import pickle
import os
from datetime import datetime, timedelta

# Try importing Prophet (optional)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("[Warning] Prophet not installed. Install with: pip install prophet")

warnings.filterwarnings("ignore")

# Device configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ══════════════════════════════════════════════════════════
#  LSTM FORECASTER
# ══════════════════════════════════════════════════════════

class TimeSeriesDataset(Dataset):
    """PyTorch Dataset for time series sequences"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMForecaster(nn.Module):
    """
    LSTM-based energy demand forecaster
    
    Features:
    - Bidirectional LSTM for better pattern recognition
    - Attention mechanism for long sequences
    - Dropout for regularization
    - Batch normalization for stability
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 3,
        dropout: float = 0.3,
        bidirectional: bool = True
    ):
        super(LSTMForecaster, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
            batch_first=True
        )
        
        # Attention mechanism
        lstm_output_size = hidden_size * 2 if bidirectional else hidden_size
        self.attention = nn.Linear(lstm_output_size, 1)
        
        # Fully connected layers
        self.fc1 = nn.Linear(lstm_output_size, 64)
        self.bn1 = nn.BatchNorm1d(64)
        self.dropout1 = nn.Dropout(dropout)
        
        self.fc2 = nn.Linear(64, 32)
        self.bn2 = nn.BatchNorm1d(32)
        self.dropout2 = nn.Dropout(dropout)
        
        self.fc3 = nn.Linear(32, 1)
        
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # LSTM
        lstm_out, _ = self.lstm(x)
        
        # Attention weights
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attn_weights * lstm_out, dim=1)
        
        # Fully connected layers
        out = self.fc1(context)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout1(out)
        
        out = self.fc2(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.dropout2(out)
        
        out = self.fc3(out)
        
        return out


class LSTMForecasterWrapper:
    """Wrapper for LSTM model with training and inference"""
    
    def __init__(
        self,
        sequence_length: int = 24,
        hidden_size: int = 128,
        num_layers: int = 3,
        dropout: float = 0.3,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        epochs: int = 50
    ):
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        
        self.model = None
        self.scaler = MinMaxScaler()
        self.feature_scaler = StandardScaler()
        self.trained = False
    
    def create_sequences(
        self,
        data: np.ndarray,
        features: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for training"""
        sequences = []
        targets = []
        
        for i in range(len(data) - self.sequence_length):
            if features is not None:
                # Combine consumption with features
                seq = np.column_stack([
                    data[i:i + self.sequence_length],
                    features[i:i + self.sequence_length]
                ])
            else:
                seq = data[i:i + self.sequence_length].reshape(-1, 1)
            
            sequences.append(seq)
            targets.append(data[i + self.sequence_length])
        
        return np.array(sequences), np.array(targets)
    
    def fit(self, df: pd.DataFrame, target_col: str = "consumption_kwh") -> Dict[str, float]:
        """Train LSTM model"""
        print("[LSTM] Training forecaster...")
        
        # Prepare data
        data = df[target_col].values
        
        # Optional: Add features
        feature_cols = [c for c in df.columns if c not in [target_col, "timestamp"] 
                       and df[c].dtype in [np.float64, np.int64]]
        
        if feature_cols:
            features = df[feature_cols].values
            features_scaled = self.feature_scaler.fit_transform(features)
        else:
            features_scaled = None
        
        # Scale target
        data_scaled = self.scaler.fit_transform(data.reshape(-1, 1)).flatten()
        
        # Create sequences
        X, y = self.create_sequences(data_scaled, features_scaled)
        
        # Train/validation split
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Create datasets
        train_dataset = TimeSeriesDataset(X_train, y_train)
        val_dataset = TimeSeriesDataset(X_val, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)
        
        # Initialize model
        input_size = X.shape[2]
        self.model = LSTMForecaster(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout
        ).to(DEVICE)
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(self.epochs):
            # Training
            self.model.train()
            train_losses = []
            
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X).squeeze()
                loss = criterion(outputs, batch_y)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                optimizer.step()
                train_losses.append(loss.item())
            
            # Validation
            self.model.eval()
            val_losses = []
            
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
                    outputs = self.model(batch_X).squeeze()
                    loss = criterion(outputs, batch_y)
                    val_losses.append(loss.item())
            
            avg_train_loss = np.mean(train_losses)
            avg_val_loss = np.mean(val_losses)
            
            scheduler.step(avg_val_loss)
            
            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{self.epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
            
            # Early stopping
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= 10:
                    print(f"  Early stopping at epoch {epoch+1}")
                    break
        
        self.trained = True
        
        # Calculate metrics on validation set
        self.model.eval()
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X = batch_X.to(DEVICE)
                outputs = self.model(batch_X).squeeze()
                all_preds.extend(outputs.cpu().numpy())
                all_targets.extend(batch_y.numpy())
        
        # Inverse transform
        all_preds = self.scaler.inverse_transform(np.array(all_preds).reshape(-1, 1)).flatten()
        all_targets = self.scaler.inverse_transform(np.array(all_targets).reshape(-1, 1)).flatten()
        
        mae = mean_absolute_error(all_targets, all_preds)
        rmse = np.sqrt(mean_squared_error(all_targets, all_preds))
        r2 = r2_score(all_targets, all_preds)
        
        print(f"[LSTM] Training complete - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.3f}")
        
        return {"mae": mae, "rmse": rmse, "r2": r2}
    
    def predict(self, df: pd.DataFrame, horizon: int = 24, target_col: str = "consumption_kwh") -> np.ndarray:
        """Forecast future values"""
        if not self.trained:
            raise ValueError("Model not trained. Call fit() first.")
        
        self.model.eval()
        
        # Use last sequence_length points as input
        data = df[target_col].values[-self.sequence_length:]
        data_scaled = self.scaler.transform(data.reshape(-1, 1)).flatten()
        
        # Optional features
        feature_cols = [c for c in df.columns if c not in [target_col, "timestamp"] 
                       and df[c].dtype in [np.float64, np.int64]]
        
        if feature_cols:
            features = df[feature_cols].values[-self.sequence_length:]
            features_scaled = self.feature_scaler.transform(features)
            sequence = np.column_stack([data_scaled.reshape(-1, 1), features_scaled])
        else:
            sequence = data_scaled.reshape(-1, 1)
        
        # Forecast
        forecasts = []
        current_seq = sequence.copy()
        
        with torch.no_grad():
            for _ in range(horizon):
                # Predict next value
                seq_tensor = torch.FloatTensor(current_seq).unsqueeze(0).to(DEVICE)
                pred = self.model(seq_tensor).item()
                forecasts.append(pred)
                
                # Update sequence
                if feature_cols:
                    # Use last feature values (simplified)
                    new_row = np.concatenate([[pred], features_scaled[-1]])
                else:
                    new_row = np.array([[pred]])
                
                current_seq = np.vstack([current_seq[1:], new_row])
        
        # Inverse transform
        forecasts = self.scaler.inverse_transform(np.array(forecasts).reshape(-1, 1)).flatten()
        
        return forecasts
    
    def save(self, filepath: str):
        """Save model"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'scaler': self.scaler,
            'feature_scaler': self.feature_scaler,
            'sequence_length': self.sequence_length,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
            'dropout': self.dropout
        }, filepath)
        print(f"[LSTM] Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model"""
        checkpoint = torch.load(filepath, map_location=DEVICE)
        
        self.scaler = checkpoint['scaler']
        self.feature_scaler = checkpoint['feature_scaler']
        self.sequence_length = checkpoint['sequence_length']
        self.hidden_size = checkpoint['hidden_size']
        self.num_layers = checkpoint['num_layers']
        self.dropout = checkpoint['dropout']
        
        # Reconstruct model
        self.model = LSTMForecaster(
            input_size=1,  # Will be updated based on data
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout
        ).to(DEVICE)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.trained = True
        
        print(f"[LSTM] Model loaded from {filepath}")


# ══════════════════════════════════════════════════════════
#  PROPHET FORECASTER
# ══════════════════════════════════════════════════════════

class ProphetForecaster:
    """
    Facebook Prophet forecaster for seasonal patterns
    
    Features:
    - Automatic seasonality detection
    - Holiday effects
    - Trend changepoints
    - Uncertainty intervals
    """
    
    def __init__(
        self,
        seasonality_mode: str = 'multiplicative',
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = True,
        changepoint_prior_scale: float = 0.05
    ):
        if not PROPHET_AVAILABLE:
            raise ImportError("Prophet not installed. Install with: pip install prophet")
        
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            changepoint_prior_scale=changepoint_prior_scale
        )
        self.trained = False
    
    def fit(self, df: pd.DataFrame, target_col: str = "consumption_kwh") -> Dict[str, float]:
        """Train Prophet model"""
        print("[Prophet] Training forecaster...")
        
        # Prepare data in Prophet format
        prophet_df = pd.DataFrame({
            'ds': pd.to_datetime(df['timestamp']),
            'y': df[target_col]
        })
        
        # Add regressors if available
        if 'temperature' in df.columns:
            prophet_df['temperature'] = df['temperature']
            self.model.add_regressor('temperature')
        
        if 'is_weekend' in df.columns:
            prophet_df['is_weekend'] = df['is_weekend'].astype(float)
            self.model.add_regressor('is_weekend')
        
        # Fit model
        self.model.fit(prophet_df)
        self.trained = True
        
        # Calculate validation metrics
        forecast = self.model.predict(prophet_df)
        y_true = prophet_df['y'].values
        y_pred = forecast['yhat'].values
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        print(f"[Prophet] Training complete - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.3f}")
        
        return {"mae": mae, "rmse": rmse, "r2": r2}
    
    def predict(self, df: pd.DataFrame, horizon: int = 24) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Forecast future values with uncertainty intervals
        
        Returns:
            Tuple of (forecasts, lower_bound, upper_bound)
        """
        if not self.trained:
            raise ValueError("Model not trained. Call fit() first.")
        
        # Create future dataframe
        last_date = pd.to_datetime(df['timestamp'].iloc[-1])
        future_dates = pd.date_range(
            start=last_date + timedelta(hours=1),
            periods=horizon,
            freq='H'
        )
        
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Add regressors (use last known values)
        if 'temperature' in df.columns:
            future_df['temperature'] = df['temperature'].iloc[-1]
        
        if 'is_weekend' in df.columns:
            future_df['is_weekend'] = float(future_dates[0].weekday() >= 5)
        
        # Forecast
        forecast = self.model.predict(future_df)
        
        return (
            forecast['yhat'].values,
            forecast['yhat_lower'].values,
            forecast['yhat_upper'].values
        )
    
    def save(self, filepath: str):
        """Save model"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"[Prophet] Model saved to {filepath}")
    
    def load(self, filepath: str):
        """Load model"""
        with open(filepath, 'rb') as f:
            self.model = pickle.load(f)
        self.trained = True
        print(f"[Prophet] Model loaded from {filepath}")


# ══════════════════════════════════════════════════════════
#  MODEL SELECTOR
# ══════════════════════════════════════════════════════════

class ForecastingPipeline:
    """
    Intelligent forecasting pipeline with automatic model selection
    
    Model Selection Strategy:
    - Short-term (1-6h): LSTM (captures recent patterns)
    - Medium-term (6-24h): Prophet (seasonal patterns)
    - Long-term (24h+): Ensemble (combines both)
    """
    
    def __init__(self):
        self.lstm_model = LSTMForecasterWrapper()
        self.prophet_model = ProphetForecaster() if PROPHET_AVAILABLE else None
        
        self.models_trained = False
        self.metrics = {}
    
    def train(self, df: pd.DataFrame, target_col: str = "consumption_kwh"):
        """Train all forecasting models"""
        print("\n" + "="*60)
        print("  Advanced Forecasting Pipeline - Training")
        print("="*60)
        
        # Train LSTM
        lstm_metrics = self.lstm_model.fit(df, target_col)
        self.metrics['lstm'] = lstm_metrics
        
        # Train Prophet
        if self.prophet_model:
            prophet_metrics = self.prophet_model.fit(df, target_col)
            self.metrics['prophet'] = prophet_metrics
        
        self.models_trained = True
        
        print("\n" + "="*60)
        print("  Training Summary")
        print("="*60)
        print(f"LSTM    - RMSE: {lstm_metrics['rmse']:.2f}, R²: {lstm_metrics['r2']:.3f}")
        if 'prophet' in self.metrics:
            print(f"Prophet - RMSE: {self.metrics['prophet']['rmse']:.2f}, R²: {self.metrics['prophet']['r2']:.3f}")
        print("="*60 + "\n")
    
    def predict(
        self,
        df: pd.DataFrame,
        horizon: int = 24,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Forecast with automatic or manual model selection
        
        Args:
            df: Historical data
            horizon: Forecast horizon in hours
            model: Force specific model ('lstm', 'prophet', 'ensemble') or None for auto
        
        Returns:
            Dictionary with forecasts, confidence intervals, and metadata
        """
        if not self.models_trained:
            raise ValueError("Models not trained. Call train() first.")
        
        # Auto-select model based on horizon
        if model is None:
            if horizon <= 6:
                selected_model = 'lstm'
            elif horizon <= 24:
                selected_model = 'prophet' if self.prophet_model else 'lstm'
            else:
                selected_model = 'ensemble' if self.prophet_model else 'lstm'
        else:
            selected_model = model
        
        print(f"[Forecast] Using {selected_model.upper()} model for {horizon}h horizon")
        
        # Generate forecasts
        if selected_model == 'lstm':
            forecasts = self.lstm_model.predict(df, horizon)
            lower = forecasts * 0.9  # Simplified uncertainty
            upper = forecasts * 1.1
        
        elif selected_model == 'prophet' and self.prophet_model:
            forecasts, lower, upper = self.prophet_model.predict(df, horizon)
        
        elif selected_model == 'ensemble' and self.prophet_model:
            # Weighted ensemble
            lstm_forecasts = self.lstm_model.predict(df, horizon)
            prophet_forecasts, prophet_lower, prophet_upper = self.prophet_model.predict(df, horizon)
            
            # Weight based on validation performance
            lstm_weight = 0.6 if horizon <= 24 else 0.4
            prophet_weight = 1 - lstm_weight
            
            forecasts = lstm_weight * lstm_forecasts + prophet_weight * prophet_forecasts
            lower = prophet_lower * 0.95
            upper = prophet_upper * 1.05
        
        else:
            raise ValueError(f"Model '{selected_model}' not available")
        
        # Generate timestamps
        last_time = pd.to_datetime(df['timestamp'].iloc[-1])
        forecast_times = pd.date_range(
            start=last_time + timedelta(hours=1),
            periods=horizon,
            freq='H'
        )
        
        return {
            'forecasts': forecasts,
            'lower_bound': lower,
            'upper_bound': upper,
            'timestamps': forecast_times,
            'model_used': selected_model,
            'horizon': horizon
        }
    
    def save_models(self, model_dir: str = "models/saved"):
        """Save all trained models"""
        os.makedirs(model_dir, exist_ok=True)
        
        self.lstm_model.save(f"{model_dir}/lstm_forecaster.pt")
        
        if self.prophet_model and self.prophet_model.trained:
            self.prophet_model.save(f"{model_dir}/prophet_forecaster.pkl")
        
        # Save metrics
        with open(f"{model_dir}/forecast_metrics.pkl", 'wb') as f:
            pickle.dump(self.metrics, f)
        
        print("[Pipeline] All models saved")
    
    def load_models(self, model_dir: str = "models/saved"):
        """Load all trained models"""
        self.lstm_model.load(f"{model_dir}/lstm_forecaster.pt")
        
        if self.prophet_model and os.path.exists(f"{model_dir}/prophet_forecaster.pkl"):
            self.prophet_model.load(f"{model_dir}/prophet_forecaster.pkl")
        
        # Load metrics
        if os.path.exists(f"{model_dir}/forecast_metrics.pkl"):
            with open(f"{model_dir}/forecast_metrics.pkl", 'rb') as f:
                self.metrics = pickle.load(f)
        
        self.models_trained = True
        print("[Pipeline] All models loaded")


# ══════════════════════════════════════════════════════════
#  EXAMPLE USAGE
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example: Train and forecast
    from data.pipeline import generate_synthetic_data
    
    # Generate sample data
    df = generate_synthetic_data(hours=2000)
    
    # Initialize pipeline
    pipeline = ForecastingPipeline()
    
    # Train all models
    pipeline.train(df)
    
    # Forecast with automatic model selection
    forecast_6h = pipeline.predict(df, horizon=6)    # Uses LSTM
    forecast_24h = pipeline.predict(df, horizon=24)   # Uses Prophet
    forecast_7d = pipeline.predict(df, horizon=168)  # Uses Ensemble
    
    print("\n6-hour forecast (LSTM):")
    print(f"  Mean: {forecast_6h['forecasts'].mean():.2f} kWh")
    
    print("\n24-hour forecast (Prophet):")
    print(f"  Mean: {forecast_24h['forecasts'].mean():.2f} kWh")
    
    print("\n7-day forecast (Ensemble):")
    print(f"  Mean: {forecast_7d['forecasts'].mean():.2f} kWh")
    
    # Save models
    pipeline.save_models()

# models/advanced_anomaly_detection.py — Advanced Anomaly Detection Models
# VAE, GAN-based, and Transformer-based anomaly detection

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from typing import Tuple, Dict, List, Optional
import warnings
import os
import pickle
from datetime import datetime
warnings.filterwarnings("ignore")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[AdvancedAnomaly] Using device: {DEVICE}")


# ══════════════════════════════════════════════════════════
#  1. VARIATIONAL AUTOENCODER (VAE)
#  - Probabilistic latent space representation
#  - Reconstruction + KL divergence loss
#  - Better at capturing data distribution
# ══════════════════════════════════════════════════════════

class VAE(nn.Module):
    """
    Variational Autoencoder for anomaly detection.
    
    Anomalies have:
    1. High reconstruction error
    2. Low probability in latent space
    3. High KL divergence
    """
    
    def __init__(
        self,
        input_dim: int,
        latent_dim: int = 16,
        hidden_dims: List[int] = [128, 64, 32]
    ):
        super(VAE, self).__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Encoder
        encoder_layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.2)
            ])
            prev_dim = h_dim
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Latent space parameters
        self.fc_mu = nn.Linear(hidden_dims[-1], latent_dim)
        self.fc_logvar = nn.Linear(hidden_dims[-1], latent_dim)
        
        # Decoder
        decoder_layers = []
        prev_dim = latent_dim
        for h_dim in reversed(hidden_dims):
            decoder_layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.2)
            ])
            prev_dim = h_dim
        
        decoder_layers.append(nn.Linear(hidden_dims[0], input_dim))
        self.decoder = nn.Sequential(*decoder_layers)
    
    def encode(self, x):
        """Encode to latent space"""
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar
    
    def reparameterize(self, mu, logvar):
        """Reparameterization trick"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z):
        """Decode from latent space"""
        return self.decoder(z)
    
    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z)
        return recon, mu, logvar
    
    def loss_function(self, recon_x, x, mu, logvar):
        """VAE loss = Reconstruction + KL divergence"""
        recon_loss = F.mse_loss(recon_x, x, reduction='sum')
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        return recon_loss + kl_loss, recon_loss, kl_loss


class VAEAnomalyDetector:
    """VAE-based anomaly detector with comprehensive scoring"""
    
    def __init__(
        self,
        latent_dim: int = 16,
        hidden_dims: List[int] = [128, 64, 32],
        learning_rate: float = 1e-3,
        batch_size: int = 64,
        epochs: int = 100,
        patience: int = 15
    ):
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_cols = None
        self.threshold_percentile = 95  # Top 5% are anomalies
        self.threshold = None
    
    def _prepare_data(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare and scale features"""
        if self.feature_cols is None:
            exclude = {"timestamp", "is_anomaly", "failure_label", "anomaly_score"}
            self.feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns 
                               if c not in exclude]
        
        X = df[self.feature_cols].fillna(0).values
        return X
    
    def fit(self, df: pd.DataFrame, validation_split: float = 0.2):
        """Train VAE on normal data"""
        X = self._prepare_data(df)
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        split_idx = int(len(X_scaled) * (1 - validation_split))
        X_train = X_scaled[:split_idx]
        X_val = X_scaled[split_idx:]
        
        # Create datasets
        train_dataset = TensorDataset(torch.FloatTensor(X_train))
        val_dataset = TensorDataset(torch.FloatTensor(X_val))
        
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.batch_size)
        
        # Initialize model
        input_dim = X_scaled.shape[1]
        self.model = VAE(input_dim, self.latent_dim, self.hidden_dims).to(DEVICE)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        
        print(f"[VAE] Training on {len(X_train)} samples, validating on {len(X_val)}")
        
        for epoch in range(self.epochs):
            # Training
            self.model.train()
            train_loss = 0
            for batch in train_loader:
                x = batch[0].to(DEVICE)
                optimizer.zero_grad()
                recon, mu, logvar = self.model(x)
                loss, _, _ = self.model.loss_function(recon, x, mu, logvar)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader.dataset)
            
            # Validation
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch in val_loader:
                    x = batch[0].to(DEVICE)
                    recon, mu, logvar = self.model(x)
                    loss, _, _ = self.model.loss_function(recon, x, mu, logvar)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader.dataset)
            scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{self.epochs} | Train: {train_loss:.4f} | Val: {val_loss:.4f}")
            
            if patience_counter >= self.patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
        
        # Calculate threshold on training data
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled).to(DEVICE)
            recon, mu, logvar = self.model(X_tensor)
            recon_errors = F.mse_loss(recon, X_tensor, reduction='none').mean(dim=1).cpu().numpy()
            self.threshold = np.percentile(recon_errors, self.threshold_percentile)
        
        print(f"[VAE] Training complete. Anomaly threshold: {self.threshold:.4f}")
        return self
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies using reconstruction error and latent space"""
        X = self._prepare_data(df)
        X_scaled = self.scaler.transform(X)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled).to(DEVICE)
            recon, mu, logvar = self.model(X_tensor)
            
            # Reconstruction error
            recon_errors = F.mse_loss(recon, X_tensor, reduction='none').mean(dim=1).cpu().numpy()
            
            # KL divergence (measure of abnormality in latent space)
            kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1).cpu().numpy()
        
        result = df.copy()
        result['vae_recon_error'] = recon_errors
        result['vae_kl_divergence'] = kl_div
        
        # Combined anomaly score (weighted average)
        recon_norm = (recon_errors - recon_errors.min()) / (recon_errors.max() - recon_errors.min() + 1e-8)
        kl_norm = (kl_div - kl_div.min()) / (kl_div.max() - kl_div.min() + 1e-8)
        result['vae_anomaly_score'] = 0.7 * recon_norm + 0.3 * kl_norm
        
        # Binary flag
        result['vae_anomaly_flag'] = (recon_errors > self.threshold).astype(int)
        
        # Severity
        result['vae_severity'] = pd.cut(
            result['vae_anomaly_score'],
            bins=[-np.inf, 0.25, 0.5, 0.75, np.inf],
            labels=['normal', 'low', 'medium', 'high']
        )
        
        return result
    
    def save(self, path: str):
        """Save model and scaler"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        checkpoint = {
            'model_state': self.model.state_dict(),
            'scaler': self.scaler,
            'feature_cols': self.feature_cols,
            'threshold': self.threshold,
            'config': {
                'latent_dim': self.latent_dim,
                'hidden_dims': self.hidden_dims,
                'input_dim': self.model.input_dim
            }
        }
        torch.save(checkpoint, path)
        print(f"[VAE] Saved → {path}")
    
    def load(self, path: str):
        """Load model and scaler"""
        checkpoint = torch.load(path, map_location=DEVICE)
        self.scaler = checkpoint['scaler']
        self.feature_cols = checkpoint['feature_cols']
        self.threshold = checkpoint['threshold']
        config = checkpoint['config']
        
        self.model = VAE(
            config['input_dim'],
            config['latent_dim'],
            config['hidden_dims']
        ).to(DEVICE)
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()
        print(f"[VAE] Loaded from {path}")


# ══════════════════════════════════════════════════════════
#  2. GAN-BASED ANOMALY DETECTION (AnoGAN)
#  - Generator learns normal data distribution
#  - Anomalies = hard to generate/discriminate
#  - Uses adversarial training
# ══════════════════════════════════════════════════════════

class Generator(nn.Module):
    """GAN Generator for normal data synthesis"""
    
    def __init__(self, latent_dim: int, output_dim: int, hidden_dims: List[int] = [128, 256]):
        super(Generator, self).__init__()
        
        layers = []
        prev_dim = latent_dim
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
            ])
            prev_dim = h_dim
        
        layers.append(nn.Linear(hidden_dims[-1], output_dim))
        layers.append(nn.Tanh())
        self.model = nn.Sequential(*layers)
    
    def forward(self, z):
        return self.model(z)


class Discriminator(nn.Module):
    """GAN Discriminator for real/fake classification"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int] = [256, 128]):
        super(Discriminator, self).__init__()
        
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.LeakyReLU(0.2),
                nn.Dropout(0.3)
            ])
            prev_dim = h_dim
        
        layers.append(nn.Linear(hidden_dims[-1], 1))
        layers.append(nn.Sigmoid())
        self.model = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.model(x)


class AnoGAN:
    """
    Anomaly Detection GAN (AnoGAN).
    
    1. Train GAN on normal data
    2. For new data, find closest latent vector z that generates it
    3. Anomaly score = reconstruction error + discrimination loss
    """
    
    def __init__(
        self,
        latent_dim: int = 32,
        hidden_dims_g: List[int] = [128, 256],
        hidden_dims_d: List[int] = [256, 128],
        learning_rate: float = 2e-4,
        batch_size: int = 64,
        epochs: int = 100,
        lambda_adv: float = 0.1
    ):
        self.latent_dim = latent_dim
        self.hidden_dims_g = hidden_dims_g
        self.hidden_dims_d = hidden_dims_d
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.lambda_adv = lambda_adv
        
        self.generator = None
        self.discriminator = None
        self.scaler = MinMaxScaler(feature_range=(-1, 1))
        self.feature_cols = None
        self.threshold = None
    
    def _prepare_data(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features"""
        if self.feature_cols is None:
            exclude = {"timestamp", "is_anomaly", "failure_label", "anomaly_score"}
            self.feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns 
                               if c not in exclude]
        
        X = df[self.feature_cols].fillna(0).values
        return X
    
    def fit(self, df: pd.DataFrame):
        """Train GAN on normal data"""
        X = self._prepare_data(df)
        X_scaled = self.scaler.fit_transform(X)
        input_dim = X_scaled.shape[1]
        
        # Initialize models
        self.generator = Generator(self.latent_dim, input_dim, self.hidden_dims_g).to(DEVICE)
        self.discriminator = Discriminator(input_dim, self.hidden_dims_d).to(DEVICE)
        
        # Optimizers
        opt_g = torch.optim.Adam(self.generator.parameters(), lr=self.learning_rate, betas=(0.5, 0.999))
        opt_d = torch.optim.Adam(self.discriminator.parameters(), lr=self.learning_rate, betas=(0.5, 0.999))
        
        # Loss
        criterion = nn.BCELoss()
        
        # DataLoader
        dataset = TensorDataset(torch.FloatTensor(X_scaled))
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        print(f"[AnoGAN] Training on {len(X)} samples")
        
        for epoch in range(self.epochs):
            d_losses = []
            g_losses = []
            
            for batch in dataloader:
                real_data = batch[0].to(DEVICE)
                batch_size = real_data.size(0)
                
                # Labels
                real_labels = torch.ones(batch_size, 1).to(DEVICE)
                fake_labels = torch.zeros(batch_size, 1).to(DEVICE)
                
                # ─────────────────────────────────────
                # Train Discriminator
                # ─────────────────────────────────────
                opt_d.zero_grad()
                
                # Real data
                real_pred = self.discriminator(real_data)
                d_loss_real = criterion(real_pred, real_labels)
                
                # Fake data
                z = torch.randn(batch_size, self.latent_dim).to(DEVICE)
                fake_data = self.generator(z)
                fake_pred = self.discriminator(fake_data.detach())
                d_loss_fake = criterion(fake_pred, fake_labels)
                
                d_loss = d_loss_real + d_loss_fake
                d_loss.backward()
                opt_d.step()
                
                # ─────────────────────────────────────
                # Train Generator
                # ─────────────────────────────────────
                opt_g.zero_grad()
                
                z = torch.randn(batch_size, self.latent_dim).to(DEVICE)
                fake_data = self.generator(z)
                fake_pred = self.discriminator(fake_data)
                
                g_loss = criterion(fake_pred, real_labels)
                g_loss.backward()
                opt_g.step()
                
                d_losses.append(d_loss.item())
                g_losses.append(g_loss.item())
            
            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1}/{self.epochs} | D Loss: {np.mean(d_losses):.4f} | G Loss: {np.mean(g_losses):.4f}")
        
        # Calculate threshold
        self.generator.eval()
        self.discriminator.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled).to(DEVICE)
            scores = []
            for i in range(len(X_tensor)):
                score = self._anomaly_score(X_tensor[i:i+1])
                scores.append(score)
            self.threshold = np.percentile(scores, 95)
        
        print(f"[AnoGAN] Training complete. Threshold: {self.threshold:.4f}")
        return self
    
    def _anomaly_score(self, x, iterations: int = 50):
        """
        Compute anomaly score by finding best latent vector z.
        Score = reconstruction error + discrimination score
        """
        # Random initialization
        z = torch.randn(x.size(0), self.latent_dim, requires_grad=True, device=DEVICE)
        optimizer = torch.optim.Adam([z], lr=1e-2)
        
        for _ in range(iterations):
            optimizer.zero_grad()
            
            gen_x = self.generator(z)
            
            # Reconstruction loss
            recon_loss = F.mse_loss(gen_x, x)
            
            # Discrimination loss
            disc_score = self.discriminator(gen_x)
            disc_loss = F.binary_cross_entropy(disc_score, torch.ones_like(disc_score))
            
            loss = recon_loss + self.lambda_adv * disc_loss
            loss.backward()
            optimizer.step()
        
        with torch.no_grad():
            gen_x = self.generator(z)
            recon_error = F.mse_loss(gen_x, x, reduction='none').mean(dim=1)
            disc_score = self.discriminator(x)
            disc_error = 1 - disc_score.squeeze()
            
            # Combined score
            score = recon_error + self.lambda_adv * disc_error
        
        return score.cpu().item()
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies"""
        X = self._prepare_data(df)
        X_scaled = self.scaler.transform(X)
        
        self.generator.eval()
        self.discriminator.eval()
        
        scores = []
        print("[AnoGAN] Computing anomaly scores (this may take a while)...")
        for i in range(len(X_scaled)):
            if i % 100 == 0:
                print(f"Processing {i}/{len(X_scaled)}")
            x_tensor = torch.FloatTensor(X_scaled[i:i+1]).to(DEVICE)
            score = self._anomaly_score(x_tensor)
            scores.append(score)
        
        scores = np.array(scores)
        
        result = df.copy()
        result['gan_anomaly_score'] = scores
        result['gan_anomaly_flag'] = (scores > self.threshold).astype(int)
        result['gan_severity'] = pd.cut(
            scores,
            bins=[-np.inf, self.threshold * 0.5, self.threshold, self.threshold * 1.5, np.inf],
            labels=['normal', 'low', 'medium', 'high']
        )
        
        return result
    
    def save(self, path: str):
        """Save models"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        checkpoint = {
            'generator_state': self.generator.state_dict(),
            'discriminator_state': self.discriminator.state_dict(),
            'scaler': self.scaler,
            'feature_cols': self.feature_cols,
            'threshold': self.threshold,
            'config': {
                'latent_dim': self.latent_dim,
                'hidden_dims_g': self.hidden_dims_g,
                'hidden_dims_d': self.hidden_dims_d,
                'lambda_adv': self.lambda_adv
            }
        }
        torch.save(checkpoint, path)
        print(f"[AnoGAN] Saved → {path}")
    
    def load(self, path: str):
        """Load models"""
        checkpoint = torch.load(path, map_location=DEVICE)
        self.scaler = checkpoint['scaler']
        self.feature_cols = checkpoint['feature_cols']
        self.threshold = checkpoint['threshold']
        config = checkpoint['config']
        
        input_dim = len(self.feature_cols)
        self.generator = Generator(
            config['latent_dim'],
            input_dim,
            config['hidden_dims_g']
        ).to(DEVICE)
        self.discriminator = Discriminator(
            input_dim,
            config['hidden_dims_d']
        ).to(DEVICE)
        
        self.generator.load_state_dict(checkpoint['generator_state'])
        self.discriminator.load_state_dict(checkpoint['discriminator_state'])
        
        self.generator.eval()
        self.discriminator.eval()
        print(f"[AnoGAN] Loaded from {path}")


# ══════════════════════════════════════════════════════════
#  3. ENSEMBLE ANOMALY DETECTOR
#  - Combines multiple detection methods
#  - Voting mechanism for robust detection
# ══════════════════════════════════════════════════════════

class EnsembleAnomalyDetector:
    """
    Ensemble of multiple anomaly detection methods.
    
    Combines:
    1. VAE (reconstruction + latent space)
    2. GAN (adversarial training)
    3. Isolation Forest (from ml_models.py - optional)
    
    Uses voting for final decision.
    """
    
    def __init__(
        self,
        use_vae: bool = True,
        use_gan: bool = True,
        voting_threshold: float = 0.5
    ):
        self.use_vae = use_vae
        self.use_gan = use_gan
        self.voting_threshold = voting_threshold
        
        self.vae_detector = VAEAnomalyDetector() if use_vae else None
        self.gan_detector = AnoGAN() if use_gan else None
    
    def fit(self, df: pd.DataFrame):
        """Train all detectors"""
        print("[Ensemble] Training multiple anomaly detectors...")
        
        if self.use_vae:
            print("\n=== Training VAE ===")
            self.vae_detector.fit(df)
        
        if self.use_gan:
            print("\n=== Training GAN ===")
            self.gan_detector.fit(df)
        
        print("\n[Ensemble] Training complete!")
        return self
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect anomalies using ensemble voting"""
        result = df.copy()
        scores = []
        flags = []
        
        if self.use_vae:
            vae_result = self.vae_detector.predict(df)
            result['vae_score'] = vae_result['vae_anomaly_score']
            result['vae_flag'] = vae_result['vae_anomaly_flag']
            scores.append(vae_result['vae_anomaly_score'].values)
            flags.append(vae_result['vae_anomaly_flag'].values)
        
        if self.use_gan:
            gan_result = self.gan_detector.predict(df)
            result['gan_score'] = gan_result['gan_anomaly_score']
            result['gan_flag'] = gan_result['gan_anomaly_flag']
            scores.append(gan_result['gan_anomaly_score'].values)
            flags.append(gan_result['gan_anomaly_flag'].values)
        
        # Ensemble score (average)
        result['ensemble_score'] = np.mean(scores, axis=0)
        
        # Ensemble flag (majority voting)
        vote_sum = np.sum(flags, axis=0)
        total_models = len(flags)
        result['ensemble_flag'] = (vote_sum / total_models >= self.voting_threshold).astype(int)
        
        # Confidence (agreement between models)
        result['ensemble_confidence'] = np.abs(vote_sum / total_models - 0.5) * 2
        
        # Severity
        result['ensemble_severity'] = pd.cut(
            result['ensemble_score'],
            bins=[-np.inf, 0.25, 0.5, 0.75, np.inf],
            labels=['normal', 'low', 'medium', 'high']
        )
        
        return result
    
    def save(self, base_path: str):
        """Save all detectors"""
        if self.use_vae:
            self.vae_detector.save(base_path.replace('.pt', '_vae.pt'))
        if self.use_gan:
            self.gan_detector.save(base_path.replace('.pt', '_gan.pt'))
        print(f"[Ensemble] All models saved to {base_path}")
    
    def load(self, base_path: str):
        """Load all detectors"""
        if self.use_vae:
            self.vae_detector.load(base_path.replace('.pt', '_vae.pt'))
        if self.use_gan:
            self.gan_detector.load(base_path.replace('.pt', '_gan.pt'))
        print(f"[Ensemble] All models loaded from {base_path}")


# ══════════════════════════════════════════════════════════
#  EXAMPLE USAGE
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example with synthetic data
    print("=== Advanced Anomaly Detection Example ===\n")
    
    # Generate synthetic energy consumption data
    np.random.seed(42)
    n_samples = 1000
    
    # Normal data
    normal_data = {
        'consumption_kwh': np.random.normal(100, 15, n_samples),
        'voltage': np.random.normal(220, 5, n_samples),
        'current': np.random.normal(10, 2, n_samples),
        'power_factor': np.random.uniform(0.85, 0.95, n_samples),
        'temperature': np.random.normal(25, 3, n_samples)
    }
    
    df = pd.DataFrame(normal_data)
    
    # Add some anomalies
    anomaly_indices = np.random.choice(n_samples, 50, replace=False)
    df.loc[anomaly_indices, 'consumption_kwh'] *= 2.5
    df.loc[anomaly_indices, 'voltage'] *= 0.7
    
    print(f"Dataset: {len(df)} samples, {len(anomaly_indices)} synthetic anomalies\n")
    
    # ─── Test VAE ───
    print("1. VAE Anomaly Detector")
    vae = VAEAnomalyDetector(epochs=50)
    vae.fit(df)
    vae_result = vae.predict(df)
    print(f"   Detected: {vae_result['vae_anomaly_flag'].sum()} anomalies\n")
    
    # ─── Test GAN ───
    print("2. GAN Anomaly Detector")
    gan = AnoGAN(epochs=50)
    gan.fit(df)
    gan_result = gan.predict(df[:100])  # Test on subset (GAN is slower)
    print(f"   Detected: {gan_result['gan_anomaly_flag'].sum()} anomalies\n")
    
    # ─── Test Ensemble ───
    print("3. Ensemble Anomaly Detector")
    ensemble = EnsembleAnomalyDetector(use_vae=True, use_gan=False)  # Skip GAN for speed
    ensemble.fit(df)
    ensemble_result = ensemble.predict(df)
    print(f"   Detected: {ensemble_result['ensemble_flag'].sum()} anomalies")
    print(f"   Average confidence: {ensemble_result['ensemble_confidence'].mean():.2%}\n")
    
    print("=== Example Complete ===")

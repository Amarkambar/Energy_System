# Real Sensor Data Integration Guide

## Overview

This guide explains how to replace synthetic training data with real industrial sensor data for production-ready ML models.

---

## Quick Start

### Step 1: Prepare Your CSV Data

Create a CSV file with your sensor readings. **Minimum required columns:**

```csv
timestamp,consumption_kwh,voltage
2026-01-01 00:00:00,450.5,230.2
2026-01-01 01:00:00,425.3,229.8
2026-01-01 02:00:00,380.2,231.1
...
```

### Step 2: Validate Your Data

```python
from data.real_data_ingestion import RealDataIngestor

ingestor = RealDataIngestor()

# Validate CSV before using
validation = ingestor.validate_csv("your_sensor_data.csv")

if validation["is_valid"]:
    print("✅ Data is valid!")
else:
    print("❌ Errors found:")
    for error in validation["errors"]:
        print(f"  - {error}")
```

### Step 3: Load and Process

```python
# Load real data (automatically cleans and validates)
df = ingestor.load_real_sensor_data(
    "your_sensor_data.csv",
    clean=True,              # Remove duplicates, fill missing values
    resample_freq="1H"       # Resample to hourly intervals
)

print(f"Loaded {len(df)} rows of real sensor data")
```

### Step 4: Train Models on Real Data

```python
from models.ml_models import train_all_models, run_all_predictions

# Train models on real data (instead of synthetic)
models = train_all_models(df)

# Run predictions
predictions = run_all_predictions(df, models)

print("✅ Models trained on real sensor data!")
```

---

## CSV Format Requirements

### Required Columns

| Column            | Type     | Description               | Example               |
| ----------------- | -------- | ------------------------- | --------------------- |
| `timestamp`       | datetime | Reading timestamp         | `2026-01-01 14:30:00` |
| `consumption_kwh` | float    | Energy consumption in kWh | `450.5`               |

### Optional Columns (Recommended)

| Column         | Type   | Description               |
| -------------- | ------ | ------------------------- |
| `voltage`      | float  | Voltage in V (e.g., 230V) |
| `current`      | float  | Current in A              |
| `power_factor` | float  | Power factor (0-1)        |
| `load_factor`  | float  | Load factor (0-1)         |
| `temperature`  | float  | Temperature in °C         |
| `humidity`     | float  | Humidity in %             |
| `pressure`     | float  | Pressure in hPa           |
| `equipment_id` | string | Equipment identifier      |
| `plant_id`     | string | Plant identifier          |
| `sensor_id`    | string | Sensor identifier         |

### Timestamp Formats Supported

```
2026-01-01 14:30:00
2026-01-01T14:30:00
2026-01-01 14:30:00.000
01/01/2026 14:30
2026-01-01T14:30:00Z
2026-01-01T14:30:00+05:30
```

---

## Data Quality Requirements

### ✅ Minimum Requirements

- **Duration:** At least 7 days (30+ days recommended for seasonal patterns)
- **Completeness:** <20% missing values per column
- **Frequency:** Consistent sampling (hourly, 15-min, etc.)
- **No negative values** in `consumption_kwh`, `voltage`, `power`

### ⚠️ Quality Checks

The validation system automatically checks for:

- Missing required columns
- Invalid timestamp format
- Time gaps in data
- Missing values >20%
- Negative values in energy/voltage
- Constant values (no variation)
- Duplicate rows
- Extreme outliers (Z-score > 5)

---

## Example: Complete Workflow

```python
from data.real_data_ingestion import RealDataIngestor
from models.ml_models import train_all_models, run_all_predictions
import pandas as pd

# Initialize ingestor
ingestor = RealDataIngestor()

# Step 1: Generate data quality report
report = ingestor.generate_data_quality_report("factory_sensors_jan2026.csv")
print(report)

# Save report to file
with open("data_quality_report.md", "w") as f:
    f.write(report)

# Step 2: Validate
validation = ingestor.validate_csv("factory_sensors_jan2026.csv")

if not validation["is_valid"]:
    print("❌ Fix these errors before proceeding:")
    for error in validation["errors"]:
        print(f"  - {error}")
    exit(1)

if validation["warnings"]:
    print("⚠️  Warnings (review but can proceed):")
    for warning in validation["warnings"]:
        print(f"  - {warning}")

# Step 3: Load and clean
df_real = ingestor.load_real_sensor_data(
    "factory_sensors_jan2026.csv",
    validate=True,
    clean=True,
    resample_freq="1H"  # Resample to hourly
)

print(f"\n✅ Loaded {len(df_real)} rows of real sensor data")
print(f"Date range: {df_real['timestamp'].min()} to {df_real['timestamp'].max()}")

# Step 4: Train models on real data
print("\nTraining ML models on real data...")
models = train_all_models(df_real)

# Step 5: Run predictions
print("Running predictions...")
predictions = run_all_predictions(df_real, models)

# Step 6: Compare with synthetic data
from data.pipeline import generate_synthetic_data

df_synthetic = generate_synthetic_data(hours=len(df_real))

comparison = ingestor.compare_with_synthetic(df_real, df_synthetic)
print("\nReal vs. Synthetic Data Comparison:")
for col, stats in comparison.items():
    print(f"\n{col}:")
    print(f"  Real:      mean={stats['real_mean']:.2f}, std={stats['real_std']:.2f}")
    print(f"  Synthetic: mean={stats['synthetic_mean']:.2f}, std={stats['synthetic_std']:.2f}")
    print(f"  Similarity: {stats['distribution_similarity']:.4f} (lower = more similar)")

# Step 7: Save processed data
df_real.to_parquet("data/real/processed_sensor_data.parquet", index=False)
print("\n✅ Real sensor data pipeline complete!")
```

---

## Data Collection Guide

### For Customers/Partners

When collecting sensor data from industrial facilities:

#### 1. **Identify Data Sources**

- Smart meters (energy consumption)
- SCADA systems (equipment monitoring)
- IoT sensors (temperature, pressure, flow)
- Building management systems (HVAC, lighting)

#### 2. **Export Format**

- **Format:** CSV (preferred) or Excel
- **Frequency:** Hourly or sub-hourly (15-min, 5-min)
- **Duration:** Minimum 1 month, ideally 6-12 months
- **Timezone:** Specify timezone or use UTC

#### 3. **Required Fields**

```csv
timestamp,consumption_kwh,voltage,temperature
2026-01-01 00:00:00,450.5,230.2,24.5
2026-01-01 01:00:00,425.3,229.8,24.3
...
```

#### 4. **Optional Metadata**

- Equipment ID / Plant ID
- Weather conditions (if available)
- Production schedule (if applicable)
- Maintenance events (downtime periods)

#### 5. **Data Privacy**

- Remove personally identifiable information (PII)
- Anonymize equipment/location names if needed
- Aggregate sensitive metrics if required

---

## Validation Report Example

After running `generate_data_quality_report()`:

```markdown
# Data Quality Report

**File:** `factory_sensors_jan2026.csv`  
**Generated:** 2026-04-02 14:30:00

---

## Validation Status

**Status:** ✅ PASS

### Errors

- None

### Warnings

- ⚠️ Column 'voltage' has 2.3% missing values
- ⚠️ Found outliers in consumption_kwh (15 outliers, 0.5%)

---

## Dataset Statistics

**Total Rows:** 2,976  
**Total Columns:** 5

**Date Range:**

- Start: 2026-01-01 00:00:00
- End: 2026-02-04 00:00:00
- Duration: 34 days

**Sampling Frequency:** 30min  
**Median Interval:** 0 days 00:30:00

### Column Statistics

**consumption_kwh:**

- Min: 180.50
- Max: 725.30
- Mean: 450.25
- Std Dev: 95.40
- Missing: 0.0%

**voltage:**

- Min: 225.10
- Max: 235.80
- Mean: 230.45
- Std Dev: 2.15
- Missing: 2.3%

### Outliers Detected

- **consumption_kwh:** 15 outliers (0.50%)

---

## Recommendations

✅ Dataset is ready for ML training

- ⚠️ Review outliers before training (may affect model accuracy)
```

---

## API Endpoints (Add to api.py)

```python
from data.real_data_ingestion import RealDataIngestor

@app.post("/api/data/upload-real-csv")
async def upload_real_sensor_data(file: UploadFile):
    """
    Upload and validate real sensor CSV data

    Returns:
        - validation_result: Quality checks
        - data_summary: Basic statistics
    """
    ingestor = RealDataIngestor()

    # Save uploaded file
    filepath = f"data/uploads/{file.filename}"
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # Validate
    validation = ingestor.validate_csv(filepath)

    if validation["is_valid"]:
        # Load and process
        df = ingestor.load_real_sensor_data(filepath, clean=True)

        return {
            "success": True,
            "validation": validation,
            "rows_loaded": len(df),
            "message": "Real sensor data loaded successfully"
        }
    else:
        return {
            "success": False,
            "validation": validation,
            "message": "Validation failed. Fix errors before proceeding."
        }


@app.get("/api/data/quality-report/{filename}")
def get_data_quality_report(filename: str):
    """Generate data quality report for uploaded CSV"""
    ingestor = RealDataIngestor()

    filepath = f"data/uploads/{filename}"
    report = ingestor.generate_data_quality_report(filepath)

    return {"report": report}
```

---

## Frontend Integration (React)

```typescript
// Upload real sensor CSV
const uploadRealData = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    "http://localhost:8000/api/data/upload-real-csv",
    {
      method: "POST",
      body: formData,
    },
  );

  const result = await response.json();

  if (result.success) {
    alert(`✅ Loaded ${result.rows_loaded} rows of real sensor data`);
  } else {
    alert(`❌ Validation failed: ${result.validation.errors.join(", ")}`);
  }
};

// Get quality report
const getQualityReport = async (filename: string) => {
  const response = await fetch(
    `http://localhost:8000/api/data/quality-report/${filename}`,
  );
  const { report } = await response.json();

  // Display markdown report
  console.log(report);
};
```

---

## Troubleshooting

### Error: "Missing required columns"

**Solution:** Ensure your CSV has `timestamp` and `consumption_kwh` columns.

```csv
timestamp,consumption_kwh
2026-01-01 00:00:00,450.5
```

### Error: "Invalid timestamp format"

**Solution:** Use standard datetime format. Supported:

- `2026-01-01 14:30:00`
- `2026-01-01T14:30:00`
- `01/01/2026 14:30`

### Warning: "Column has >20% missing values"

**Solution:** Either:

1. Fill missing values in source data
2. Set `clean=True` when loading (automatic forward-fill)

### Warning: "Found time gaps"

**Solution:** If data has intentional gaps (e.g., weekends), set `resample_freq` to fill:

```python
df = ingestor.load_real_sensor_data("data.csv", resample_freq="1H")
```

---

## Best Practices

✅ **DO:**

- Collect 30+ days of data for seasonal patterns
- Use consistent sampling frequency (hourly recommended)
- Include voltage/temperature if available
- Run validation before training
- Generate quality report for documentation

❌ **DON'T:**

- Use data with >20% missing values without cleaning
- Mix different sampling frequencies
- Include negative consumption/voltage values
- Skip validation step

---

## Next Steps

Once real data is validated and loaded:

1. **Retrain all models** on real data
2. **Compare performance** with synthetic data baseline
3. **A/B test** predictions on hold-out real data
4. **Monitor accuracy** in production
5. **Collect more data** for continuous improvement

---

**Estimated Setup Time:** 1-2 hours (including data collection)

**Documentation:** [data/real_data_ingestion.py](data/real_data_ingestion.py)

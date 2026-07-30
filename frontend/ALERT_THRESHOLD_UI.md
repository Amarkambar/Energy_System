# Alert Threshold Configuration UI ✅

## What's New

The Settings page now has a powerful, user-friendly interface for configuring alert thresholds with industry-specific presets, real-time sensitivity indicators, and import/export capabilities.

### New Features

✅ **Industry Presets** - One-click configuration for different industries  
✅ **Alert Sensitivity Indicator** - Real-time visualization of overall alert sensitivity  
✅ **Import/Export Settings** - Save and share configurations as JSON files  
✅ **Unsaved Changes Warning** - Visual indicator when changes haven't been saved  
✅ **Enhanced UI** - Better organization, tooltips, and responsive design  

---

## Industry Presets

### Available Presets

1. **Manufacturing Facility**
   - Consumption: 800 kWh
   - Anomaly Score: 0.75
   - Voltage Deviation: ±12V
   - Load Factor: 0.92
   - *Use case: High consumption environments with moderate voltage tolerance*

2. **Data Center**
   - Consumption: 1200 kWh
   - Anomaly Score: 0.65
   - Voltage Deviation: ±5V
   - Load Factor: 0.95
   - *Use case: Critical voltage stability, high baseline consumption*

3. **Hospital / Healthcare**
   - Consumption: 600 kWh
   - Anomaly Score: 0.60
   - Voltage Deviation: ±6V
   - Load Factor: 0.88
   - *Use case: Very strict voltage tolerance, 24/7 monitoring*

4. **Retail / Office**
   - Consumption: 350 kWh
   - Anomaly Score: 0.70
   - Voltage Deviation: ±15V
   - Load Factor: 0.85
   - *Use case: Lower consumption, business hours focus*

5. **Default / General**
   - Balanced thresholds for general use

---

## Alert Sensitivity Indicator

The sensitivity indicator provides a 0-100% score based on your current configuration:

- **70-100% (High)**: Sensitive alert configuration - more frequent alerts, catches subtle issues
- **40-70% (Medium)**: Balanced sensitivity - recommended for most use cases
- **0-40% (Low)**: Relaxed thresholds - only critical issues trigger alerts

**Formula:**
```
Sensitivity = Average of:
  - Consumption Score: (100 - consumption_threshold / 10)
  - Anomaly Score: (1 - anomaly_threshold) × 100
  - Voltage Score: (100 - voltage_deviation × 5)
  - Load Score: load_factor × 100
```

---

## Import / Export Settings

### Export Settings

1. Click **"💾 Export"** button
2. Settings are saved as JSON file with timestamp
3. File format: `energy-diagnostics-settings-2026-04-02.json`

**Example Export:**
```json
{
  "alert_consumption_threshold": 500,
  "alert_anomaly_score_threshold": 0.7,
  "alert_voltage_deviation": 10,
  "alert_load_factor_threshold": 0.9,
  "alert_email_recipients": ["admin@company.com", "ops@company.com"],
  "smtp_enabled": true
}
```

### Import Settings

1. Click **"📂 Import"** button
2. Select a previously exported JSON file
3. Settings are automatically loaded (not saved until you click "Save Settings")

**Use Cases:**
- Share configurations across multiple installations
- Backup settings before making changes
- Version control alert configurations
- Deploy consistent settings to production

---

## Threshold Configuration

### 1. Consumption Threshold (kWh)
- **Range**: 50 - 5000 kWh
- **Default**: 500 kWh
- **Purpose**: Trigger warning when hourly consumption exceeds this value
- **Recommendation**: Set to 1.5× your average peak consumption

### 2. Anomaly Score Threshold (0-1)
- **Range**: 0.1 - 1.0
- **Default**: 0.7
- **Purpose**: Flag readings with ML-detected anomaly confidence above this
- **Recommendation**: 
  - 0.6-0.7: Sensitive (more false positives)
  - 0.7-0.8: Balanced (recommended)
  - 0.8-0.9: Conservative (fewer false positives)

### 3. Voltage Deviation (V)
- **Range**: 1 - 50 V
- **Default**: ±10 V
- **Purpose**: Alert when voltage deviates from 230V nominal by more than this
- **Recommendation**:
  - Data centers: ±5V (strict)
  - Hospitals: ±6V (strict)
  - Manufacturing: ±12V (moderate)
  - Retail: ±15V (relaxed)

### 4. Peak Load Factor Threshold (0-1)
- **Range**: 0.5 - 1.0
- **Default**: 0.9
- **Purpose**: Alert when load factor exceeds this during peak hours (9am-9pm)
- **Recommendation**: Set to 0.85-0.92 to catch overload conditions early

---

## UI Components

### 1. Header Section
- Page title and description
- **Unsaved Changes Badge**: Yellow warning when changes aren't saved

### 2. Industry Presets
- Collapsible section with 5 preset configurations
- Click any preset to apply instantly
- Shows key metrics for each preset

### 3. Alert Sensitivity Indicator
- Real-time calculation based on current settings
- Gradient progress bar (green → yellow → red)
- Percentage score + text label (Low/Medium/High)

### 4. Alert Thresholds
- 4 configurable thresholds with sliders + number inputs
- Live preview of changes
- Descriptive tooltips for each setting

### 5. Email Notifications
- Toggle switch for SMTP enable/disable
- Comma-separated email recipient list
- SMTP configuration guide with code examples

### 6. System Info
- Cache type: Disk-persistent (restart-proof)
- Auth method: HMAC token (7-day expiry)
- Reset tokens: 15-minute one-time tokens

### 7. Action Buttons
- **Export**: Save settings to JSON file
- **Import**: Load settings from JSON file
- **Reset to Defaults**: Restore default values
- **Save Settings**: Apply changes to backend

---

## API Integration

The settings page uses the existing API endpoints:

```typescript
// GET current settings
GET /api/settings/thresholds
Authorization: Bearer <token>

// POST updated settings
POST /api/settings/thresholds
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_consumption_threshold": 500,
  "alert_anomaly_score_threshold": 0.7,
  "alert_voltage_deviation": 10,
  "alert_load_factor_threshold": 0.9,
  "alert_email_recipients": ["admin@company.com"],
  "smtp_enabled": true
}
```

---

## User Workflow

### Basic Configuration
1. Navigate to **Settings** page
2. Adjust sliders to desired values
3. Watch sensitivity indicator update in real-time
4. Click **"Save Settings"**
5. ✅ Changes applied immediately

### Using Industry Presets
1. Click **"Show Presets"**
2. Review available presets
3. Click on desired industry (e.g., "Manufacturing Facility")
4. Fine-tune values if needed
5. Click **"Save Settings"**

### Sharing Configurations
1. Configure optimal settings
2. Click **"💾 Export"**
3. Share JSON file with team/other installations
4. Others click **"📂 Import"** → select file
5. Review imported settings
6. Click **"Save Settings"**

---

## Best Practices

✅ **DO:**
- Start with an industry preset, then customize
- Monitor alert frequency after changes (too many alerts = reduce sensitivity)
- Export settings before major changes (easy rollback)
- Test with 24-48 hours of data before finalizing
- Document your reasoning for custom thresholds

❌ **DON'T:**
- Set consumption threshold < average consumption (too many false positives)
- Use voltage deviation < 3V (too strict for most facilities)
- Enable email alerts without configuring SMTP first
- Change multiple thresholds simultaneously (hard to debug)

---

## Troubleshooting

### Settings Not Saving
**Symptom**: Click "Save Settings" but changes don't persist  
**Solution**: 
- Check browser console for API errors
- Verify authentication token is valid
- Ensure backend is running (`docker compose ps`)

### Too Many Alerts
**Symptom**: Alert flood after changing thresholds  
**Solution**:
- Check sensitivity indicator (if >80%, reduce sensitivity)
- Increase consumption threshold
- Increase anomaly score threshold to 0.8+
- Use a more relaxed industry preset

### Settings Lost After Restart
**Symptom**: Settings reset to defaults after backend restart  
**Solution**:
- This is expected behavior (settings stored in `backend/data/settings.json`)
- Export settings regularly as backup
- Settings file persists across restarts unless deleted

### Import Fails
**Symptom**: "Invalid settings file" error when importing  
**Solution**:
- Ensure JSON file is properly formatted
- Check for missing required fields
- Try exporting fresh settings as reference

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/dashboard/SettingsPage.tsx` | Added presets, sensitivity indicator, import/export, unsaved changes warning |

---

## What's Next

Future enhancements could include:
- **A/B Testing**: Compare alert configurations side-by-side
- **Historical Analysis**: Show alert frequency over time for current settings
- **Smart Recommendations**: ML-based threshold suggestions based on historical data
- **Role-based Access**: Restrict threshold changes to Admin users only
- **Notification Channels**: Add Slack, Teams, SMS in addition to email

---

**Implementation Complete!** 🎉  
The Alert Threshold Configuration UI is now fully functional and production-ready.

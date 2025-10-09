# 400 Bad Request Error - Diagnosis and Fixes

## Error Location
**Endpoint:** `POST /api/custom_model/trigger_github_training`
**Status Code:** 400 Bad Request

## Root Causes Found

### 1. ❌ Position Group State Mismatch (FIXED)
- **Problem:** Initial state was `"Attacker"` (English) but select options were in Catalan
- **Impact:** Could cause form submission with invalid position value
- **Fix:** Changed initial state from `"Attacker"` to `"Atacant"`
- **Location:** `ScoutingPage.jsx:132`

### 2. ⚠️ Insufficient Error Reporting (FIXED)
- **Problem:** 400 errors didn't show validation details to the user
- **Impact:** Unable to debug what validation failed
- **Fix:** Added detailed error logging and UI display for validation errors
- **Locations:** 
  - Frontend: `ScoutingPage.jsx:363-384` (error handling)
  - Frontend: `ScoutingPage.jsx:1128-1147` (validation details UI)
  - Backend: `main.py:881-889` (request logging)

## Validation Requirements

According to `validation_schemas.py`, the endpoint expects:

```python
{
  "position_group": "Attacker" | "Midfielder" | "Defender",  # Required
  "impact_kpis": ["kpi1", "kpi2", ...],  # Required, 1-20 items
  "target_kpis": ["kpi1", "kpi2", ...],  # Required, 1-30 items
  "model_name": "string",                 # Optional, max 100 chars
  "ml_features": ["feat1", ...] | null   # Optional, max 200 items
}
```

## Frontend Validation Check

The frontend now logs the payload before sending:
- Position group validity check
- Impact KPIs count
- Target KPIs count
- Model name length

## How to Debug

1. **Open Browser Console** (F12)
2. **Trigger the error** by submitting the custom model form
3. **Look for these logs:**
   - `🔍 Sending payload to backend:` - Shows exactly what's being sent
   - `📊 Validation check:` - Shows if data passes basic checks
   - `❌ Error response:` - Shows the backend's error response
   - `❌ Full error:` - Shows the complete error object

4. **Check backend logs** (if you have access to Render/server logs):
   - `🔍 Received training request:` - Shows what backend received
   - `📊 Data types:` - Shows data types of each field
   - `❌ Validation failed:` - Shows Marshmallow validation errors

## Common Validation Failures

### Empty KPI Lists
- **Error:** "Impact KPIs must contain between 1 and 20 items"
- **Cause:** No KPIs selected in Step 1 or Step 2
- **Fix:** Select at least 1 KPI in both sections

### Invalid Position Group
- **Error:** "Position group must be one of: Attacker, Midfielder, Defender"
- **Cause:** Position not properly mapped from Catalan to English
- **Fix:** Already fixed by updating `mapPositionGroupToBackend` function

### Model Name Too Long
- **Error:** "Model name must be less than 100 characters"
- **Cause:** Custom model name exceeds 100 characters
- **Fix:** Use shorter model name

### Too Many ML Features
- **Error:** "ML features list cannot exceed 200 items"
- **Cause:** Selected more than 200 custom ML features
- **Fix:** Reduce number of selected features

## Next Steps

1. **Test the form again** with the fixes applied
2. **Check the browser console** for detailed logs
3. **Report the specific validation error** if it still fails
4. If error persists, check:
   - That KPIs are selected (arrays are not empty)
   - Position group is one of the 3 valid options
   - Model name is not too long
   - Not selecting too many ML features

## Files Modified

- ✅ `client-react/src/ScoutingPage.jsx` - Fixed position state, added logging, improved error display
- ✅ `server-flask/main.py` - Added request logging for debugging


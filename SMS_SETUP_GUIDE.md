# PoultryGuard — SMS Alerts & Notification Setup Guide

PoultryGuard includes an enterprise-grade notification dispatcher engineered to deliver critical early-warning alerts directly to farm managers and field operators via SMS.

---

## 1. When Are SMS Notifications Sent?

SMS alerts are triggered for high-priority operational screening events:
1. **Urgent Farmer-Reported Health Events:** Mortality spikes, breathing difficulty, or sudden flock collapse.
2. **Persistent Spatial High-Density Events:** Flocks crowding in a specific zone exceeding threshold for multiple consecutive frames.
3. **Severe Behavioral Lethargy Drift:** Sudden flock-wide drops in activity relative to baseline.

> **Cooldown Protection:** To prevent duplicate spam during continuous conditions, alerts in the same category are rate-limited to at most one SMS every 300 seconds (configurable via `SMS_COOLDOWN_SEC`).

---

## 2. Phone Number Format & Indian Mobile Normalization

The initial target mobile recipient is configured as:
```ini
SMS_RECIPIENT=7530088644
```
PoultryGuard automatically cleans and normalizes Indian mobile numbers into the international E.164 standard:
- Input: `7530088644` or `07530088644` or `917530088644`
- Normalized E.164 Output: `+917530088644`
- Frontend & Audit Display: Safely masked as `+91 75300 ****44` to protect farmer privacy.

---

## 3. Provider Configuration Options

Open `C:\Dev\12hr\PoultryGuard_Full\.env` to configure your chosen provider.

### Option A: Indian SMS Gateway (Fast2SMS) — Recommended for India
Fast2SMS offers direct transactional SMS delivery across Indian telecom operators.

1. Create a free account at [Fast2SMS](https://www.fast2sms.com/).
2. Retrieve your API Authorization Key from the Fast2SMS Developer Dashboard.
3. Update `.env`:
   ```ini
   SMS_ENABLED=true
   SMS_PROVIDER=indian_gateway
   SMS_RECIPIENT=7530088644
   SMS_DRY_RUN=false
   FAST2SMS_API_KEY=your_fast2sms_api_key_here
   FAST2SMS_SENDER_ID=TXTIND
   ```

### Option B: Twilio SMS Gateway — Global Telecommunications
Twilio provides programmatic SMS delivery worldwide.

1. Sign up at [Twilio](https://www.twilio.com/) and obtain an active SMS-enabled virtual phone number.
2. Retrieve your **Account SID** and **Auth Token** from the Twilio Console.
3. Update `.env`:
   ```ini
   SMS_ENABLED=true
   SMS_PROVIDER=twilio
   SMS_RECIPIENT=+917530088644
   SMS_DRY_RUN=false
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_FROM_NUMBER=+1234567890
   ```

### Option C: Mock / Dry-Run Mode — Zero-Cost Local Testing (Default)
Enables full end-to-end verification and UI testing without sending carrier SMS or incurring costs.

1. In `.env`:
   ```ini
   SMS_ENABLED=false
   SMS_PROVIDER=disabled
   SMS_RECIPIENT=7530088644
   SMS_DRY_RUN=true
   ```
2. When dry-run mode is active, the dispatcher formats the message, checks rate limits, validates recipient numbers, and logs the notification in SQLite with status `dry_run`.

---

## 4. Testing Your SMS Dispatcher

### Via the Web Dashboard
1. Open the **Settings & Model** tab in the PoultryGuard dashboard (`http://127.0.0.1:8000/`).
2. Scroll to the **SMS Notification Dispatcher** card.
3. Select **Dispatch Mode** (Dry Run or Real Dispatch) and click **Dispatch Notification**.
4. Observe the instant delivery status and check the **Notification Audit Log** table below.

### Via the REST API
Send a POST request to `/api/v1/sms/test`:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/sms/test" \
     -H "Content-Type: application/json" \
     -d '{"dry_run": true, "message": "PoultryGuard operational test"}'
```

### Inspecting the Audit Trail
All notification attempts are logged in the SQLite `notifications` table:
```sql
SELECT id, event_type, recipient, provider, status, created_at FROM notifications ORDER BY id DESC LIMIT 10;
```
You can also download the complete audit trail directly via:
- GET `/api/v1/reports/notifications.csv`
- Button in the **Reports & CSV** tab: **Export SMS Notifications CSV**.

# Deployment Guide

## Avoiding CAPTCHA Issues

School websites may trigger CAPTCHA challenges if they detect automated requests. This guide shows you how to minimize and handle these situations.

### 1. Configure Request Delays

Edit your `.env` file to add delays between requests:

```bash
# Minimum delay between requests (seconds)
MIN_REQUEST_DELAY=3.0

# Maximum delay between requests (seconds)
MAX_REQUEST_DELAY=7.0

# HTTP request timeout (seconds)
REQUEST_TIMEOUT=30
```

**Recommended settings for production:**
- `MIN_REQUEST_DELAY=3.0` - At least 3 seconds between requests
- `MAX_REQUEST_DELAY=7.0` - Random delays up to 7 seconds
- Increase these values if you still see CAPTCHAs

### 2. Use Headful Mode for Manual CAPTCHA Solving

When running the fetcher, you can enable headful mode to manually solve CAPTCHAs when they appear:

```bash
# In .env file
PLAYWRIGHT_HEADFUL=true
```

This will open a browser window when a CAPTCHA is detected. Simply solve it manually and press Enter to continue.

### 3. Scheduled Fetching

Instead of fetching frequently, schedule fetches at longer intervals:

```bash
# Using cron (Linux/Mac)
# Run fetcher once per day at 2 AM
0 2 * * * cd /path/to/alliance/backend && python fetch.py

# Using Windows Task Scheduler
# Create a task that runs daily at 2 AM
```

### 4. Browser Profile Persistence

The scraper automatically saves browser cookies and session data in `.playwright-profile/` directory. This helps websites recognize the "browser" as a returning visitor, reducing CAPTCHA triggers.

**Important:** Don't delete the `.playwright-profile/` directory between runs.

### 5. Production Deployment Best Practices

#### Option A: Manual CAPTCHA Solving (Recommended for small deployments)

1. Set `PLAYWRIGHT_HEADFUL=true` in `.env`
2. Run fetcher manually when needed
3. Solve any CAPTCHAs that appear
4. Browser profile will be saved for future use

```bash
cd backend
python fetch.py
```

#### Option B: Automated with Delays (For larger deployments)

1. Configure longer delays:
   ```bash
   MIN_REQUEST_DELAY=5.0
   MAX_REQUEST_DELAY=10.0
   ```

2. Limit announcements per school:
   ```python
   # In announcement_service.py line 395
   for href in links[:5]:  # Fetch only 5 per school instead of 10
   ```

3. Run less frequently (once per day or week)

4. Monitor logs for CAPTCHA warnings

#### Option C: Use API Endpoints with Manual Trigger

Instead of automatic scheduling, create a protected admin endpoint:

```bash
# Only fetch when manually triggered via API
curl -X POST http://your-domain/api/fetch \
  -H "Authorization: Bearer YOUR_SECRET_TOKEN"
```

### 6. Docker Deployment

When deploying with Docker, make sure to:

1. Mount the Playwright profile directory:
   ```yaml
   volumes:
     - ./.playwright-profile:/app/.playwright-profile
   ```

2. Install Playwright browsers in Dockerfile:
   ```dockerfile
   RUN playwright install chromium
   RUN playwright install-deps
   ```

3. Set environment variables in `docker-compose.yml`:
   ```yaml
   environment:
     - MIN_REQUEST_DELAY=3.0
     - MAX_REQUEST_DELAY=7.0
     - PLAYWRIGHT_HEADFUL=false
   ```

### 7. Monitoring and Logs

Check logs to see if CAPTCHAs are being triggered:

```bash
# Check backend logs
docker-compose logs -f backend

# Look for warnings like:
# "Listing request failed... Trying Playwright fallback"
# "Detail request failed... Trying Playwright fallback"
```

If you see many Playwright fallbacks, increase your delays.

### 8. Testing Configuration

Test your anti-CAPTCHA settings:

```bash
cd backend
python fetch.py --verbose
```

Watch the logs to see:
- Delay times between requests
- Whether Playwright is being triggered
- If CAPTCHAs are appearing

### Summary: Recommended Settings

**For Development:**
```bash
MIN_REQUEST_DELAY=2.0
MAX_REQUEST_DELAY=5.0
PLAYWRIGHT_HEADFUL=true  # Manual solving
```

**For Production (Automated):**
```bash
MIN_REQUEST_DELAY=5.0
MAX_REQUEST_DELAY=10.0
PLAYWRIGHT_HEADFUL=false  # Background
# + Schedule: Run once per day
```

**For Production (Manual):**
```bash
MIN_REQUEST_DELAY=3.0
MAX_REQUEST_DELAY=7.0
PLAYWRIGHT_HEADFUL=true  # Manual solving when needed
# + Trigger: Manual API calls only
```

## Troubleshooting

### Still Getting CAPTCHAs?

1. **Increase delays:** Double your `MIN_REQUEST_DELAY` and `MAX_REQUEST_DELAY`
2. **Fetch less data:** Reduce `links[:10]` to `links[:5]` in the code
3. **Run less often:** Change from hourly to daily fetching
4. **Use headful mode:** Enable manual solving
5. **Check IP reputation:** Some IPs may be blocked/flagged
6. **Rotate user agents:** The code already does this, but you can add more variants

### CAPTCHA Appears Even with Delays?

Some websites are very aggressive. Options:

1. **Whitelist IP:** Contact school IT departments to whitelist your server IP
2. **Manual mode:** Always use `PLAYWRIGHT_HEADFUL=true` and solve manually
3. **Reduce scope:** Fetch from fewer schools at a time
4. **API approach:** Check if schools offer official APIs instead of scraping

### Browser Won't Open in Headful Mode?

On headless servers (no display):

```bash
# Option 1: Use X virtual framebuffer
xvfb-run python fetch.py

# Option 2: Use VNC to connect and view browser
# Install and configure VNC server
```

Or stick to `PLAYWRIGHT_HEADFUL=false` and handle CAPTCHAs via other methods.

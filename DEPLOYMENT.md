# Deploying Parser on Railway

This guide will help you deploy the dork scraper on Railway.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. Git installed on your computer
3. The following files in your project:
   - `parser_railway.py` (non-interactive version)
   - `requirements.txt`
   - `railway.json`
   - `Procfile`
   - `cc_dorks.txt`
   - `user_agents.txt`

## Deployment Steps

### Method 1: Deploy from GitHub (Recommended)

1. **Create a GitHub repository**
   ```bash
   cd C:\Users\Nikish\Documents\ra
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Select your repository
   - Railway will automatically detect and deploy

3. **Configure Environment Variables**
   
   In Railway dashboard → Your Project → Variables, add:
   ```
   PROXY_CHOICE=1
   SEARCH_ENGINE=1
   MODE=1
   DORKS_FILE=cc_dorks.txt
   ```

   Optional (if using proxy):
   ```
   PROXY_CHOICE=2
   PROXY_STRING=host:port:user:pass
   ```

### Method 2: Deploy via Railway CLI

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize and Deploy**
   ```bash
   cd C:\Users\Nikish\Documents\ra
   railway init
   railway up
   ```

4. **Set Environment Variables**
   ```bash
   railway variables set PROXY_CHOICE=1
   railway variables set SEARCH_ENGINE=1
   railway variables set MODE=1
   railway variables set DORKS_FILE=cc_dorks.txt
   ```

## Configuration Options

### PROXY_CHOICE
- `1` = No proxy (default)
- `2` = Use proxy (requires PROXY_STRING)

### SEARCH_ENGINE
- `1` = Google only
- `2` = Bing only
- `3` = Mix (alternates between Google and Bing)

### MODE
- `1` = Single-threaded (slower, fewer rate limits)
- `2` = Multi-threaded (faster, more rate limits)

### PROXY_STRING (only if PROXY_CHOICE=2)
Format: `host:port:username:password`

Example: `43.159.29.246:9999:user123:pass456`

## Important Notes

⚠️ **Important Considerations:**

1. **Railway has a monthly usage limit** on the free tier ($5 of usage)
2. **This script makes many HTTP requests** which may consume credits quickly
3. **Rate limiting** - Search engines will rate limit you, especially Google
4. **Ephemeral storage** - Files like `jphq.txt` and `progress.json` will be lost when the service restarts
5. **Consider using a database** or external storage for persistent data

## Accessing Output Files

Since Railway has ephemeral storage, you have two options:

### Option 1: Add Cloud Storage
Modify the script to save to AWS S3, Google Cloud Storage, or similar.

### Option 2: Use Railway Volumes
Add a volume in Railway dashboard:
- Go to your project → Settings → Volumes
- Create a new volume mounted at `/data`
- Modify the script to save files to `/data/jphq.txt`

## Viewing Logs

- In Railway dashboard → Your Project → Deployments
- Click on the latest deployment to see real-time logs
- This shows all print statements from your script

## Stopping/Restarting

- In Railway dashboard → Your Project
- Click "Settings" → "Restart" to restart the service
- Click "Settings" → "Remove Service" to stop completely

## Troubleshooting

### Script keeps restarting
- Check logs for errors
- Ensure all required files are present
- Verify environment variables are set correctly

### No output
- Check that `cc_dorks.txt` and `user_agents.txt` are in the repository
- View logs to see what's happening

### Rate limiting issues
- Switch to `SEARCH_ENGINE=3` (Mix mode)
- Use `MODE=1` (Single-threaded)
- Consider adding proxy support

## Cost Optimization

1. Use single-threaded mode (`MODE=1`)
2. Limit the number of dorks in your file
3. Monitor usage in Railway dashboard
4. Consider deploying only when needed, not 24/7

## Alternative: Use Cron Job

Instead of running continuously, you can set up a cron job:

1. Modify `railway.json` to add a cron schedule
2. Script runs at scheduled times instead of continuously
3. More cost-effective for periodic scraping

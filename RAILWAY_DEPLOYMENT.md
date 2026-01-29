# Railway Deployment Guide

This guide will help you deploy Agent OS on Railway.

## Prerequisites

- Railway account ([signup here](https://railway.app))
- GitHub repository for this project
- Anthropic API key

## Deployment Steps

### 1. Push to GitHub

Make sure your code is pushed to a GitHub repository.

```bash
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 2. Deploy on Railway

1. Go to [Railway](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose this repository
5. Railway will automatically detect the configuration files

### 3. Set Environment Variables

In your Railway project dashboard, go to **Variables** and add:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OS_SECURITY_KEY=omnigpt
```

**Important:** Replace `your_anthropic_api_key_here` with your actual Anthropic API key.

### 4. Deploy

Railway will automatically:
- Install dependencies from `requirements.txt`
- Start the server using the `Procfile` configuration
- Expose the app on a public URL

## Configuration Files

- **Procfile**: Tells Railway how to run the app
- **railway.toml**: Railway-specific configuration
- **railway.json**: Alternative Railway configuration format
- **requirements.txt**: Python dependencies

## Running Locally

To test the configuration locally:

```bash
export ANTHROPIC_API_KEY='your_api_key_here'
export OS_SECURITY_KEY='omnigpt'
export PORT=8000

uvicorn agno_agent:app --host 0.0.0.0 --port 8000
```

Or use the Python script directly:

```bash
ANTHROPIC_API_KEY='your_api_key_here' OS_SECURITY_KEY='omnigpt' python agno_agent.py
```

## Access Your Deployment

After deployment, Railway will provide a URL like:
```
https://your-app-name.up.railway.app
```

You can access:
- API Documentation: `https://your-app-name.up.railway.app/docs`
- Health Check: `https://your-app-name.up.railway.app/health` (if configured)

## Monitoring

Check your deployment logs in the Railway dashboard:
- Click on your service
- Go to the "Deployments" tab
- Click on the latest deployment to view logs

## Troubleshooting

### Build Fails
- Check that `requirements.txt` has all necessary dependencies
- Review build logs in Railway dashboard

### Runtime Errors
- Verify environment variables are set correctly
- Check deployment logs for error messages
- Ensure ANTHROPIC_API_KEY is valid

### Port Issues
- Railway automatically sets the PORT environment variable
- The app will use PORT 8000 locally and Railway's PORT in production

## Support

For issues with:
- Agent OS: Check the main repository
- Railway: Visit [Railway Documentation](https://docs.railway.app)

# Initialize Git and push to GitHub
# Edit the repository URL before running!

# Configuration - EDIT THESE
$GITHUB_USERNAME = "your-github-username"  # Change this!
$REPO_NAME = "math-problem-generator"
$GITHUB_TOKEN = ""  # Optional: for private repos, set your token

# Derived URLs
$HTTPS_URL = "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
$SSH_URL = "git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Git Repository Initialization" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if already a git repo
if (Test-Path .\.git) {
    Write-Host "✓ Already a Git repository" -ForegroundColor Green
} else {
    Write-Host "🔄 Initializing Git repository..." -ForegroundColor Yellow
    git init
}

# Add all files
Write-Host "📦 Adding all files..." -ForegroundColor Yellow
git add .

# Create commit
Write-Host "📝 Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Full-stack math problem generator with 402 passing tests" -m "Backend: FastAPI with 402 tests, authentication, assignments, LLM integration`nFrontend: React + TypeScript ready for design`nFeatures: Student dashboard, teacher analytics, adaptive difficulty"

# Ensure main branch
Write-Host "🌿 Setting up main branch..." -ForegroundColor Yellow
git branch -M main

# Add remote
Write-Host "🔗 Adding GitHub remote: $HTTPS_URL" -ForegroundColor Yellow
if (git remote | Select-String -Pattern "origin" -Quiet) {
    Write-Host "   Removing existing remote..." -ForegroundColor Gray
    git remote remove origin
}
git remote add origin $HTTPS_URL

# Show status
Write-Host ""
Write-Host "📊 Repository Status:" -ForegroundColor Cyan
git log --oneline -3
Write-Host ""
git remote -v
Write-Host ""

# Instructions
Write-Host "✅ Git repository initialized!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://github.com/new"
Write-Host "2. Create repository: $REPO_NAME"
Write-Host "3. Return here and run:" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor Cyan
Write-Host ""
Write-Host "After pushing:" -ForegroundColor Yellow
Write-Host "• Visit: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
Write-Host "• Use Lovable AI at https://lovable.ai to generate frontend design"
Write-Host "• Share on Twitter, Reddit, Dev.to, and LinkedIn!"
Write-Host ""

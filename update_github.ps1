$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot

try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is not installed. Install Git for Windows, then run this helper again."
    }

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".git"))) {
        Write-Host "Preparing this folder as a Git repository..." -ForegroundColor Cyan
        & git init --initial-branch=main
        if ($LASTEXITCODE -ne 0) { throw "Git could not initialize the project folder." }
    }

    $remoteUrl = & git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($remoteUrl -join ""))) {
        Write-Host "Create an empty repository on GitHub first, then paste its HTTPS or SSH URL here." -ForegroundColor Yellow
        $remoteUrl = Read-Host "GitHub repository URL"
        if ([string]::IsNullOrWhiteSpace($remoteUrl)) { throw "No GitHub URL entered. Nothing was uploaded." }
        & git remote add origin $remoteUrl
        if ($LASTEXITCODE -ne 0) { throw "Git could not save that GitHub URL." }
    }

    $gitName = & git config user.name
    if ([string]::IsNullOrWhiteSpace(($gitName -join ""))) {
        $gitName = Read-Host "Name to show on your GitHub commits"
        if ([string]::IsNullOrWhiteSpace($gitName)) { throw "A commit name is required." }
        & git config user.name $gitName
    }
    $gitEmail = & git config user.email
    if ([string]::IsNullOrWhiteSpace(($gitEmail -join ""))) {
        $gitEmail = Read-Host "Email for your GitHub commits"
        if ([string]::IsNullOrWhiteSpace($gitEmail)) { throw "A commit email is required." }
        & git config user.email $gitEmail
    }

    $changes = & git status --porcelain
    if ($changes) {
        Write-Host "Adding the project files..." -ForegroundColor Cyan
        & git add -A
        if ($LASTEXITCODE -ne 0) { throw "Git could not add the project files." }

        $message = Read-Host "Update summary (press Enter for 'Update A6 project')"
        if ([string]::IsNullOrWhiteSpace($message)) { $message = "Update A6 project" }
        & git commit -m $message
        if ($LASTEXITCODE -ne 0) { throw "Git could not create the update. Check the message above." }
    } else {
        Write-Host "No new file changes to commit. Checking GitHub for any local commits to upload..." -ForegroundColor Cyan
    }

    $branch = & git branch --show-current
    if ([string]::IsNullOrWhiteSpace(($branch -join ""))) { $branch = "main" }
    & git push --set-upstream origin $branch
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub did not accept the upload. Confirm the repository URL and sign-in, and make sure the GitHub repository was created empty."
    }

    Write-Host "Project updated on GitHub successfully." -ForegroundColor Green
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}


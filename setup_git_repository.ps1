# PowerShell script to set up Git repository for cryptobot project

# Function to display colored output
function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$Color = "White"
    )
    
    Write-Host $Message -ForegroundColor $Color
}

# Display header
Write-ColorOutput "===== Cryptobot Git Repository Setup =====" "Cyan"
Write-ColorOutput "This script will help you set up the Git repository for the cryptobot project." "Cyan"
Write-ColorOutput "It will fix the following issues:" "Cyan"
Write-ColorOutput "1. Configure Git identity" "Cyan"
Write-ColorOutput "2. Reset staged files" "Cyan"
Write-ColorOutput "3. Apply .gitignore" "Cyan"
Write-ColorOutput "4. Create initial commit" "Cyan"
Write-ColorOutput "5. Set up GitHub remote" "Cyan"
Write-ColorOutput "=======================================" "Cyan"
Write-ColorOutput ""

# Step 1: Configure Git identity
Write-ColorOutput "Step 1: Configure Git identity" "Green"
$name = Read-Host "Enter your name for Git configuration"
$email = Read-Host "Enter your email for Git configuration"

if ($name -and $email) {
    git config --global user.name "$name"
    git config --global user.email "$email"
    Write-ColorOutput "Git identity configured successfully!" "Green"
} else {
    Write-ColorOutput "Error: Name and email are required for Git configuration." "Red"
    exit 1
}

# Step 2: Reset staged files
Write-ColorOutput "`nStep 2: Resetting staged files" "Green"
git reset
Write-ColorOutput "All staged files have been reset." "Green"

# Step 3: Verify .gitignore exists
Write-ColorOutput "`nStep 3: Verifying .gitignore" "Green"
if (Test-Path ".gitignore") {
    Write-ColorOutput ".gitignore file found." "Green"
} else {
    Write-ColorOutput "Error: .gitignore file not found. Please create it first." "Red"
    exit 1
}

# Step 4: Stage and commit files
Write-ColorOutput "`nStep 4: Staging and committing files" "Green"
git add .
Write-ColorOutput "Files staged for commit. Here's the current status:" "Green"
git status

$commitMessage = Read-Host "Enter a commit message (default: 'Initial commit')"
if (-not $commitMessage) {
    $commitMessage = "Initial commit"
}

git commit -m "$commitMessage"
Write-ColorOutput "Initial commit created!" "Green"

# Step 5: Set up GitHub remote
Write-ColorOutput "`nStep 5: Setting up GitHub remote" "Green"
Write-ColorOutput "To push to GitHub, you need to create a repository on GitHub first." "Yellow"
Write-ColorOutput "Go to https://github.com/new to create a new repository." "Yellow"
Write-ColorOutput "Do NOT initialize it with README, .gitignore, or license." "Yellow"
$setupRemote = Read-Host "Have you created the GitHub repository? (y/n)"

if ($setupRemote -eq "y") {
    $username = Read-Host "Enter your GitHub username"
    $repoName = Read-Host "Enter the repository name (default: cryptobot)"
    
    if (-not $repoName) {
        $repoName = "cryptobot"
    }
    
    # Check if remote origin already exists
    $remoteExists = git remote | Select-String -Pattern "^origin$"
    
    if ($remoteExists) {
        Write-ColorOutput "Remote 'origin' already exists." "Yellow"
        $action = Read-Host "Do you want to (r)emove it, use a (d)ifferent name, or (s)kip? (r/d/s)"
        
        if ($action -eq "r") {
            git remote remove origin
            git remote add origin "https://github.com/$username/$repoName.git"
            Write-ColorOutput "Remote 'origin' removed and re-added." "Green"
        }
        elseif ($action -eq "d") {
            $remoteName = Read-Host "Enter a new remote name"
            git remote add $remoteName "https://github.com/$username/$repoName.git"
            Write-ColorOutput "Remote '$remoteName' added." "Green"
        }
        else {
            Write-ColorOutput "Skipped adding remote." "Yellow"
        }
    }
    else {
        git remote add origin "https://github.com/$username/$repoName.git"
        Write-ColorOutput "Remote 'origin' added." "Green"
    }
    
    $pushNow = Read-Host "Do you want to push to GitHub now? (y/n)"
    if ($pushNow -eq "y") {
        # Rename branch from master to main if needed
        $currentBranch = git branch --show-current
        if ($currentBranch -eq "master") {
            Write-ColorOutput "Renaming branch from 'master' to 'main'..." "Yellow"
            git branch -M main
            Write-ColorOutput "Branch renamed to 'main'." "Green"
            git push -u origin main
        } else {
            git push -u origin $currentBranch
        }
        Write-ColorOutput "Repository pushed to GitHub successfully!" "Green"
    } else {
        Write-ColorOutput "You can push to GitHub later with:" "Yellow"
        Write-ColorOutput "git branch -M main  # Rename branch from master to main" "Yellow"
        Write-ColorOutput "git push -u origin main" "Yellow"
    }
} else {
    Write-ColorOutput "You can set up the GitHub remote later with:" "Yellow"
    Write-ColorOutput "git remote add origin https://github.com/yourusername/cryptobot.git" "Yellow"
    Write-ColorOutput "git branch -M main  # Rename branch from master to main" "Yellow"
    Write-ColorOutput "git push -u origin main" "Yellow"
}

# Final status
Write-ColorOutput "`nGit repository setup complete!" "Green"
Write-ColorOutput "Current Git status:" "Green"
git status

Write-ColorOutput "`nGit configuration:" "Green"
Write-ColorOutput "User name: $(git config --get user.name)" "Green"
Write-ColorOutput "User email: $(git config --get user.email)" "Green"

Write-ColorOutput "`nRemote repositories:" "Green"
git remote -v

Write-ColorOutput "`nFor more detailed instructions, see GIT_SETUP_INSTRUCTIONS.md" "Cyan"
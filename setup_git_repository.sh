#!/bin/bash

# Bash script to set up Git repository for cryptobot project

# Function to display colored output
print_color() {
    COLOR=$2
    NC='\033[0m' # No Color
    
    case $COLOR in
        "red")
            COLOR_CODE='\033[0;31m'
            ;;
        "green")
            COLOR_CODE='\033[0;32m'
            ;;
        "yellow")
            COLOR_CODE='\033[0;33m'
            ;;
        "blue")
            COLOR_CODE='\033[0;34m'
            ;;
        "cyan")
            COLOR_CODE='\033[0;36m'
            ;;
        *)
            COLOR_CODE='\033[0m' # Default to no color
            ;;
    esac
    
    echo -e "${COLOR_CODE}$1${NC}"
}

# Display header
print_color "===== Cryptobot Git Repository Setup =====" "cyan"
print_color "This script will help you set up the Git repository for the cryptobot project." "cyan"
print_color "It will fix the following issues:" "cyan"
print_color "1. Configure Git identity" "cyan"
print_color "2. Reset staged files" "cyan"
print_color "3. Apply .gitignore" "cyan"
print_color "4. Create initial commit" "cyan"
print_color "5. Set up GitHub remote" "cyan"
print_color "=======================================" "cyan"
echo ""

# Step 1: Configure Git identity
print_color "Step 1: Configure Git identity" "green"
read -p "Enter your name for Git configuration: " name
read -p "Enter your email for Git configuration: " email

if [ -n "$name" ] && [ -n "$email" ]; then
    git config --global user.name "$name"
    git config --global user.email "$email"
    print_color "Git identity configured successfully!" "green"
else
    print_color "Error: Name and email are required for Git configuration." "red"
    exit 1
fi

# Step 2: Reset staged files
print_color "Step 2: Resetting staged files" "green"
git reset
print_color "All staged files have been reset." "green"

# Step 3: Verify .gitignore exists
print_color "Step 3: Verifying .gitignore" "green"
if [ -f ".gitignore" ]; then
    print_color ".gitignore file found." "green"
else
    print_color "Error: .gitignore file not found. Please create it first." "red"
    exit 1
fi

# Step 4: Stage and commit files
print_color "Step 4: Staging and committing files" "green"
git add .
print_color "Files staged for commit. Here's the current status:" "green"
git status

read -p "Enter a commit message (default: 'Initial commit'): " commit_message
if [ -z "$commit_message" ]; then
    commit_message="Initial commit"
fi

git commit -m "$commit_message"
print_color "Initial commit created!" "green"

# Step 5: Set up GitHub remote
print_color "Step 5: Setting up GitHub remote" "green"
print_color "To push to GitHub, you need to create a repository on GitHub first." "yellow"
print_color "Go to https://github.com/new to create a new repository." "yellow"
print_color "Do NOT initialize it with README, .gitignore, or license." "yellow"
read -p "Have you created the GitHub repository? (y/n): " setup_remote

if [ "$setup_remote" = "y" ]; then
    read -p "Enter your GitHub username: " username
    read -p "Enter the repository name (default: cryptobot): " repo_name
    
    if [ -z "$repo_name" ]; then
        repo_name="cryptobot"
    fi
    
    git remote add origin "https://github.com/$username/$repo_name.git"
    print_color "Remote 'origin' added." "green"
    
    read -p "Do you want to push to GitHub now? (y/n): " push_now
    if [ "$push_now" = "y" ]; then
        git push -u origin master
        print_color "Repository pushed to GitHub successfully!" "green"
    else
        print_color "You can push to GitHub later with: git push -u origin master" "yellow"
    fi
else
    print_color "You can set up the GitHub remote later with:" "yellow"
    print_color "git remote add origin https://github.com/yourusername/cryptobot.git" "yellow"
    print_color "git push -u origin master" "yellow"
fi

# Final status
print_color "Git repository setup complete!" "green"
print_color "Current Git status:" "green"
git status

print_color "Git configuration:" "green"
echo "User name: $(git config --get user.name)"
echo "User email: $(git config --get user.email)"

print_color "Remote repositories:" "green"
git remote -v

print_color "For more detailed instructions, see GIT_SETUP_INSTRUCTIONS.md" "cyan"
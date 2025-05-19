# GitHub Personal Access Token (PAT) Authentication Guide

This guide will help you set up and use a GitHub Personal Access Token for Git authentication, which is now required instead of password authentication.

## 1. Creating a Personal Access Token (PAT)

### Step-by-Step Instructions

1. **Log in to your GitHub account** at [github.com](https://github.com)

2. **Access Settings**:
   - Click on your profile photo in the top-right corner
   - Select "Settings" from the dropdown menu

3. **Navigate to Developer Settings**:
   - Scroll down to the bottom of the left sidebar
   - Click on "Developer settings"

4. **Access Personal Access Tokens**:
   - In the left sidebar, click on "Personal access tokens"
   - Select "Tokens (classic)" or "Fine-grained tokens" (Fine-grained tokens offer more granular permissions)

5. **Generate a New Token**:
   - Click "Generate new token" or "Generate new token (classic)"
   - You may be prompted to confirm your password

6. **Configure Token Settings**:
   - **Name**: Give your token a descriptive name (e.g., "Cryptobot Repository Access")
   - **Expiration**: Choose an expiration date (30 days, 60 days, 90 days, custom, or no expiration)
     - For security, it's recommended to set an expiration date
     - For long-term projects, you can set a longer expiration or create a reminder to update it

7. **Select Scopes/Permissions**:
   - For basic Git operations (push, pull), select:
     - `repo` (Full control of private repositories)
   - For GitHub Actions workflows, also select:
     - `workflow` (Update GitHub Action workflows)
   - For packages or other features, select additional permissions as needed

8. **Generate Token**:
   - Scroll to the bottom and click "Generate token"

9. **Copy and Save Your Token**:
   - **IMPORTANT**: Copy your token immediately and store it securely
   - GitHub will only show the token once
   - Consider saving it in a password manager

## 2. Using Your Personal Access Token with Git

### Basic Usage

When pushing to GitHub for the first time, you'll be prompted for your username and password. Use your GitHub username and your PAT as the password.

```bash
git push -u origin main
```

### Storing Credentials

#### Windows

1. **Git Credential Manager** (Recommended, usually installed with Git for Windows):
   ```bash
   git config --global credential.helper manager
   ```

2. **Store credentials in memory temporarily** (cached for 15 minutes):
   ```bash
   git config --global credential.helper cache
   ```

3. **Store credentials on disk** (less secure but convenient):
   ```bash
   git config --global credential.helper store
   ```

#### macOS

1. **Use macOS Keychain** (Recommended):
   ```bash
   git config --global credential.helper osxkeychain
   ```

#### Linux

1. **Cache credentials temporarily**:
   ```bash
   git config --global credential.helper cache
   ```

2. **Extend cache timeout** (e.g., to 1 hour = 3600 seconds):
   ```bash
   git config --global credential.helper 'cache --timeout=3600'
   ```

3. **Store credentials on disk**:
   ```bash
   git config --global credential.helper store
   ```

### Using HTTPS with Credentials in the URL

You can include your token in the remote URL (not recommended for shared repositories):

```bash
git remote set-url origin https://USERNAME:TOKEN@github.com/robm7/cryptobot.git
```

Replace `USERNAME` with your GitHub username and `TOKEN` with your PAT.

## 3. Troubleshooting Common Issues

### Authentication Failures

1. **Token Expired**:
   - If your token has expired, generate a new one following the steps in Section 1
   - Update your stored credentials

2. **Incorrect Token**:
   - Verify you're using the correct token
   - Ensure there are no extra spaces when copying/pasting

3. **Insufficient Permissions**:
   - Check if your token has the necessary scopes (e.g., `repo` for repository access)
   - Generate a new token with the correct permissions if needed

4. **Clearing Stored Credentials**:
   - Windows:
     ```bash
     git credential-manager uninstall   # For older Git versions
     git credential-manager reject https://github.com   # For newer versions
     ```
   - macOS:
     ```bash
     git credential-osxkeychain erase host=github.com protocol=https
     ```
   - Linux:
     ```bash
     git config --global --unset credential.helper
     ```

### Updating or Regenerating Tokens

1. **To update a token**:
   - Follow the same steps as creating a new token
   - Revoke the old token after setting up the new one

2. **If you lost your token**:
   - You cannot recover a lost token
   - Generate a new token and update your stored credentials

### Revoking Tokens

1. **Access your tokens**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   
2. **Delete the token**:
   - Find the token you want to revoke
   - Click "Delete" and confirm

## 4. Best Practices for Token Security

1. **Use the Principle of Least Privilege**:
   - Only grant the permissions (scopes) that are absolutely necessary
   - Use fine-grained tokens when possible for more granular control

2. **Set Expiration Dates**:
   - Always set an expiration date for your tokens
   - Regularly rotate tokens, especially for sensitive repositories

3. **Use Credential Helpers**:
   - Use secure credential storage like Git Credential Manager or macOS Keychain
   - Avoid storing tokens in plain text or hardcoding them in scripts

4. **Never Share Your Tokens**:
   - Do not share tokens with others
   - Do not commit tokens to repositories
   - Do not include tokens in public documentation

5. **Monitor Token Usage**:
   - Periodically review your tokens and remove unused ones
   - Check the "Recently used" information to detect potential unauthorized use

6. **Use Different Tokens for Different Purposes**:
   - Create separate tokens for different projects or services
   - This limits the impact if one token is compromised

7. **Consider SSH Keys for Personal Use**:
   - For personal machines, SSH keys can be more convenient and secure
   - See [GitHub's SSH documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

## Specific Instructions for Your Cryptobot Project

You've already set up your remote and renamed your branch:

```bash
git remote add origin https://github.com/robm7/cryptobot.git
git branch -M main
```

To complete the push with authentication:

1. Generate a PAT following Section 1 above
2. Configure credential storage using one of the methods in Section 2
3. Push your code:
   ```bash
   git push -u origin main
   ```
4. When prompted, enter your GitHub username and use your PAT as the password

If you're still experiencing issues, try the troubleshooting steps in Section 3.
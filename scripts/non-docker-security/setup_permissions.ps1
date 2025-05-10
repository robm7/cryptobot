# Cryptobot User Permissions Configuration Script for Windows
# This script sets up proper user permissions for the Cryptobot application

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Log "Error: This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    exit 1
}

# Get current user
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Log "Starting user permissions configuration for Cryptobot..."
Log "Current user: $currentUser"

# Create a dedicated group for Cryptobot if it doesn't exist
$cryptobotGroup = "CryptobotUsers"
Log "Checking if Cryptobot group exists..."

try {
    $group = Get-LocalGroup -Name $cryptobotGroup -ErrorAction Stop
    Log "Cryptobot group already exists"
} catch {
    Log "Creating Cryptobot group..."
    New-LocalGroup -Name $cryptobotGroup -Description "Cryptobot application users"
}

# Add current user to Cryptobot group if not already a member
Log "Adding current user to Cryptobot group..."
$currentUserName = $currentUser.Split('\')[-1]
try {
    $groupMembers = Get-LocalGroupMember -Group $cryptobotGroup -ErrorAction Stop
    $isMember = $groupMembers | Where-Object { $_.Name -eq $currentUser }
    if (-not $isMember) {
        Add-LocalGroupMember -Group $cryptobotGroup -Member $currentUser
        Log "Added current user to Cryptobot group"
    } else {
        Log "Current user is already a member of Cryptobot group"
    }
} catch {
    Add-LocalGroupMember -Group $cryptobotGroup -Member $currentUser
    Log "Added current user to Cryptobot group"
}

# Create necessary directories if they don't exist
Log "Creating necessary directories..."
$directories = @(
    "logs",
    "data",
    "config",
    "config\security",
    "config\ssl"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Log "Created directory: $dir"
    }
}

# Set permissions for directories
Log "Setting permissions for directories..."

# Function to set permissions
function Set-SecurePermissions {
    param (
        [string]$Path,
        [string]$PermissionLevel,
        [bool]$Recurse = $true
    )
    
    $acl = Get-Acl $Path
    $acl.SetAccessRuleProtection($true, $false)
    
    # Add Administrators with Full Control
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", 
        "FullControl", 
        "ContainerInherit,ObjectInherit", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($adminRule)
    
    # Add SYSTEM with Full Control
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", 
        "FullControl", 
        "ContainerInherit,ObjectInherit", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($systemRule)
    
    # Add current user with Full Control
    $userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser, 
        "FullControl", 
        "ContainerInherit,ObjectInherit", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($userRule)
    
    # Add Cryptobot group with specified permissions
    $groupPermission = switch ($PermissionLevel) {
        "ReadOnly" { "ReadAndExecute" }
        "ReadWrite" { "Modify" }
        "FullControl" { "FullControl" }
        default { "ReadAndExecute" }
    }
    
    $groupRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $cryptobotGroup, 
        $groupPermission, 
        "ContainerInherit,ObjectInherit", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($groupRule)
    
    # Apply the ACL
    Set-Acl -Path $Path -AclObject $acl
    
    # If recursive, apply to all subdirectories and files
    if ($Recurse) {
        Get-ChildItem -Path $Path -Recurse -Force | ForEach-Object {
            Set-Acl -Path $_.FullName -AclObject $acl
        }
    }
}

# Set base directory permissions
Set-SecurePermissions -Path "." -PermissionLevel "ReadOnly" -Recurse $false

# Set permissions for specific directories
Set-SecurePermissions -Path "logs" -PermissionLevel "ReadWrite"
Set-SecurePermissions -Path "data" -PermissionLevel "ReadWrite"
Set-SecurePermissions -Path "config" -PermissionLevel "ReadOnly"
Set-SecurePermissions -Path "config\security" -PermissionLevel "ReadOnly"
Set-SecurePermissions -Path "config\ssl" -PermissionLevel "ReadOnly"
Set-SecurePermissions -Path "scripts" -PermissionLevel "ReadOnly"

# Set special permissions for sensitive files
Log "Setting special permissions for sensitive files..."

# .env file
if (Test-Path ".env") {
    $acl = Get-Acl ".env"
    $acl.SetAccessRuleProtection($true, $false)
    
    # Add Administrators with Full Control
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($adminRule)
    
    # Add SYSTEM with Full Control
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($systemRule)
    
    # Add current user with Full Control
    $userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser, 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($userRule)
    
    # Apply the ACL
    Set-Acl -Path ".env" -AclObject $acl
    Log "Set restricted permissions for .env file"
}

# Security config file
if (Test-Path "config\security\security_config.json") {
    $acl = Get-Acl "config\security\security_config.json"
    $acl.SetAccessRuleProtection($true, $false)
    
    # Add Administrators with Full Control
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($adminRule)
    
    # Add SYSTEM with Full Control
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($systemRule)
    
    # Add current user with Full Control
    $userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser, 
        "FullControl", 
        "None", 
        "None", 
        "Allow"
    )
    $acl.AddAccessRule($userRule)
    
    # Apply the ACL
    Set-Acl -Path "config\security\security_config.json" -AclObject $acl
    Log "Set restricted permissions for security_config.json file"
}

# SSL certificates
if (Test-Path "config\ssl") {
    Get-ChildItem -Path "config\ssl" -Filter "*.key" -Recurse | ForEach-Object {
        $acl = Get-Acl $_.FullName
        $acl.SetAccessRuleProtection($true, $false)
        
        # Add Administrators with Full Control
        $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Administrators", 
            "FullControl", 
            "None", 
            "None", 
            "Allow"
        )
        $acl.AddAccessRule($adminRule)
        
        # Add SYSTEM with Full Control
        $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "SYSTEM", 
            "FullControl", 
            "None", 
            "None", 
            "Allow"
        )
        $acl.AddAccessRule($systemRule)
        
        # Add current user with Full Control
        $userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $currentUser, 
            "FullControl", 
            "None", 
            "None", 
            "Allow"
        )
        $acl.AddAccessRule($userRule)
        
        # Apply the ACL
        Set-Acl -Path $_.FullName -AclObject $acl
    }
    Log "Set restricted permissions for SSL key files"
}

# Create Windows service with proper permissions
Log "Creating Windows service configuration..."

# Create a service configuration file
$serviceConfigPath = "config\security\service_config.json"
$serviceConfig = @{
    services = @(
        @{
            name = "CryptobotAuth"
            display_name = "Cryptobot Auth Service"
            description = "Authentication service for Cryptobot"
            executable = "python.exe"
            arguments = "auth/main.py"
            working_directory = (Get-Location).Path
            start_type = "Automatic"
            dependencies = @("postgresql-x64-14", "redis")
            account = "LocalSystem"
            restart_on_failure = $true
        },
        @{
            name = "CryptobotStrategy"
            display_name = "Cryptobot Strategy Service"
            description = "Strategy service for Cryptobot"
            executable = "python.exe"
            arguments = "strategy/main.py"
            working_directory = (Get-Location).Path
            start_type = "Automatic"
            dependencies = @("postgresql-x64-14", "redis", "CryptobotAuth")
            account = "LocalSystem"
            restart_on_failure = $true
        }
    )
}

$serviceConfigJson = $serviceConfig | ConvertTo-Json -Depth 5
Set-Content -Path $serviceConfigPath -Value $serviceConfigJson

# Set permissions for service configuration file
$acl = Get-Acl $serviceConfigPath
$acl.SetAccessRuleProtection($true, $false)

# Add Administrators with Full Control
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "Administrators", 
    "FullControl", 
    "None", 
    "None", 
    "Allow"
)
$acl.AddAccessRule($adminRule)

# Add SYSTEM with Full Control
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "SYSTEM", 
    "FullControl", 
    "None", 
    "None", 
    "Allow"
)
$acl.AddAccessRule($systemRule)

# Add current user with Full Control
$userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $currentUser, 
    "FullControl", 
    "None", 
    "None", 
    "Allow"
)
$acl.AddAccessRule($userRule)

# Apply the ACL
Set-Acl -Path $serviceConfigPath -AclObject $acl
Log "Set restricted permissions for service configuration file"

Log "User permissions configuration completed successfully!"
Log "Note: You may need to log out and log back in for group membership changes to take effect."
exit 0
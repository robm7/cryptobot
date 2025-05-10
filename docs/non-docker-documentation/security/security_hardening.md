# Cryptobot Security Hardening Guide

This guide provides detailed instructions for hardening the security of your Cryptobot non-Docker installation. Following these steps will help protect your system, data, and trading operations from various security threats.

## Table of Contents

1. [Introduction](#introduction)
2. [Security Configuration](#security-configuration)
3. [Network Security](#network-security)
4. [Database Security](#database-security)
5. [API Security](#api-security)
6. [Authentication and Authorization](#authentication-and-authorization)
7. [Data Encryption](#data-encryption)
8. [Secure Configuration](#secure-configuration)
9. [Logging and Monitoring](#logging-and-monitoring)
10. [Vulnerability Management](#vulnerability-management)
11. [Regular Security Maintenance](#regular-security-maintenance)

## Introduction

Cryptobot handles sensitive financial data and API keys for cryptocurrency exchanges. Proper security measures are essential to protect your assets and data from unauthorized access, data breaches, and other security threats.

This guide is intended for non-Docker installations of Cryptobot. For Docker-based deployments, please refer to the Docker-specific security documentation.

## Security Configuration

The Cryptobot security scripts provide automated security hardening for your installation. These scripts are located in the `scripts/non-docker-security/` directory.

### Running Security Configuration Scripts

1. **Secure Configuration Script**:
   ```bash
   # For Linux/macOS
   sudo bash scripts/non-docker-security/secure_config.sh
   
   # For Windows (Run as Administrator)
   .\scripts\non-docker-security\secure_config.ps1
   ```

   This script:
   - Generates secure random keys for JWT tokens and password reset tokens
   - Configures secure Redis settings
   - Sets up secure database passwords
   - Configures secure session settings
   - Sets up rate limiting
   - Configures secure CORS settings
   - Creates a security configuration file

2. **Firewall Configuration Script**:
   ```bash
   # For Linux/macOS
   sudo bash scripts/non-docker-security/setup_firewall.sh
   
   # For Windows (Run as Administrator)
   .\scripts\non-docker-security\setup_firewall.ps1
   ```

   This script:
   - Configures the system firewall to protect Cryptobot services
   - Allows necessary service ports
   - Restricts database and Redis access to localhost only
   - Blocks suspicious outbound connections

3. **User Permissions Script**:
   ```bash
   # For Linux/macOS
   sudo bash scripts/non-docker-security/setup_permissions.sh
   
   # For Windows (Run as Administrator)
   .\scripts\non-docker-security\setup_permissions.ps1
   ```

   This script:
   - Creates a dedicated group for Cryptobot
   - Sets proper ownership and permissions for files and directories
   - Secures sensitive files like configuration and SSL certificates
   - Sets up secure service configurations

4. **SSL/TLS Configuration Script**:
   ```bash
   # For Linux/macOS
   sudo bash scripts/non-docker-security/setup_ssl.sh
   
   # For Windows (Run as Administrator)
   .\scripts\non-docker-security\setup_ssl.ps1
   ```

   This script:
   - Generates SSL/TLS certificates
   - Configures HTTPS for Cryptobot services
   - Sets up secure SSL/TLS protocols and ciphers
   - Configures security headers

## Network Security

### Firewall Configuration

The firewall configuration script sets up basic firewall rules, but you should consider additional network security measures:

1. **Network Segmentation**:
   - Place Cryptobot on a separate network segment or VLAN
   - Use network ACLs to restrict traffic between segments

2. **Intrusion Detection/Prevention**:
   - Consider installing an IDS/IPS system like Snort or Suricata
   - Monitor for suspicious network activity

3. **VPN Access**:
   - If remote access is required, use a VPN
   - Avoid exposing Cryptobot services directly to the internet

4. **Port Scanning Protection**:
   - Install and configure tools like fail2ban to block port scanning attempts
   - Example fail2ban configuration:
     ```
     [cryptobot-portscan]
     enabled = true
     filter = cryptobot-portscan
     action = iptables-allports[name=cryptobot-portscan]
     logpath = /var/log/auth.log
     maxretry = 5
     findtime = 300
     bantime = 3600
     ```

## Database Security

### PostgreSQL Hardening

1. **Authentication**:
   - Use strong passwords for database users
   - Consider using client certificate authentication for additional security

2. **Access Control**:
   - Restrict database access to localhost only
   - Use pg_hba.conf to control client authentication:
     ```
     # TYPE  DATABASE        USER            ADDRESS                 METHOD
     local   all             postgres                                peer
     local   cryptobot       cryptobot                               md5
     host    cryptobot       cryptobot       127.0.0.1/32            md5
     host    cryptobot       cryptobot       ::1/128                 md5
     ```

3. **Encryption**:
   - Enable SSL for database connections
   - Add to postgresql.conf:
     ```
     ssl = on
     ssl_cert_file = '/path/to/server.crt'
     ssl_key_file = '/path/to/server.key'
     ```

4. **Regular Backups**:
   - Implement regular database backups
   - Test backup restoration procedures
   - Store backups securely, preferably encrypted

## API Security

### Exchange API Security

1. **API Key Management**:
   - Use the built-in API key rotation feature
   - Limit API key permissions to only what's necessary
   - Use read-only API keys when possible

2. **IP Restrictions**:
   - When supported by exchanges, restrict API keys to specific IP addresses
   - Consider using a static IP address for your Cryptobot server

3. **Monitoring**:
   - Monitor API usage for unusual patterns
   - Set up alerts for unexpected API calls

### Cryptobot API Security

1. **Authentication**:
   - Use JWT tokens with short expiration times
   - Implement proper token validation
   - Consider implementing API key authentication for service-to-service communication

2. **Rate Limiting**:
   - Configure rate limiting to prevent abuse
   - Implement progressive delays for repeated failed authentication attempts

3. **Input Validation**:
   - Validate all API inputs
   - Use schema validation for request payloads

## Authentication and Authorization

### User Authentication

1. **Password Policies**:
   - Enforce strong password requirements
   - Implement account lockout after failed attempts
   - Consider password expiration policies

2. **Multi-Factor Authentication**:
   - Enable MFA for all users, especially administrators
   - Use TOTP-based authentication
   - Provide secure backup codes for recovery

3. **Session Management**:
   - Set reasonable session timeouts
   - Implement secure cookie handling
   - Invalidate sessions on password change

### Authorization

1. **Role-Based Access Control**:
   - Implement principle of least privilege
   - Regularly review user roles and permissions
   - Separate duties for administrative functions

2. **API Authorization**:
   - Validate permissions for each API request
   - Implement proper scope checking for tokens
   - Log authorization failures

## Data Encryption

### Data at Rest

1. **Database Encryption**:
   - Consider using encrypted file systems for database storage
   - Use column-level encryption for sensitive data

2. **Configuration Encryption**:
   - Encrypt sensitive configuration files
   - Use environment variables for secrets

3. **API Key Storage**:
   - Store API keys encrypted in the database
   - Consider using a dedicated secrets management solution

### Data in Transit

1. **HTTPS**:
   - Use TLS 1.2 or higher for all connections
   - Configure secure cipher suites
   - Implement HSTS headers

2. **Certificate Management**:
   - Regularly rotate SSL/TLS certificates
   - Use certificates from trusted CAs for production
   - Implement certificate pinning for critical connections

## Secure Configuration

### Service Hardening

1. **Principle of Least Privilege**:
   - Run services with minimal required permissions
   - Use dedicated service accounts

2. **Remove Unnecessary Features**:
   - Disable unused services and features
   - Remove development/debug features in production

3. **Secure Defaults**:
   - Ensure all services have secure default configurations
   - Disable insecure protocols and ciphers

### Environment Configuration

1. **Environment Variables**:
   - Use environment variables for sensitive configuration
   - Restrict access to environment files

2. **Configuration Validation**:
   - Validate configuration at startup
   - Fail securely if configuration is invalid

## Logging and Monitoring

### Logging

1. **Comprehensive Logging**:
   - Log all security-relevant events
   - Include sufficient context in log entries
   - Implement structured logging

2. **Log Protection**:
   - Secure log files with proper permissions
   - Consider using a centralized logging system
   - Implement log rotation and archiving

### Monitoring

1. **Security Monitoring**:
   - Monitor for suspicious activities
   - Set up alerts for security events
   - Regularly review security logs

2. **Performance Monitoring**:
   - Monitor system resource usage
   - Watch for unusual performance patterns
   - Set up alerts for resource exhaustion

## Vulnerability Management

### Vulnerability Assessment

1. **Regular Scanning**:
   ```bash
   # For Linux/macOS
   bash scripts/non-docker-security/assess_vulnerabilities.sh
   
   # For Windows
   .\scripts\non-docker-security\assess_vulnerabilities.ps1
   ```

2. **Dependency Scanning**:
   - Regularly scan dependencies for vulnerabilities
   - Use tools like pip-audit or safety
   - Keep dependencies up-to-date

3. **Code Review**:
   - Conduct security-focused code reviews
   - Use static analysis tools
   - Follow secure coding practices

### Patch Management

1. **Regular Updates**:
   - Keep the operating system updated
   - Update application dependencies
   - Apply security patches promptly

2. **Testing Updates**:
   - Test updates in a non-production environment
   - Have a rollback plan for failed updates

## Regular Security Maintenance

### Security Checklist

1. **Daily Tasks**:
   - Review security logs
   - Check system status
   - Verify backups

2. **Weekly Tasks**:
   - Update dependencies
   - Run vulnerability scans
   - Review user access

3. **Monthly Tasks**:
   - Conduct full security review
   - Test backup restoration
   - Review and update security policies

### Incident Response

1. **Preparation**:
   - Develop an incident response plan
   - Define roles and responsibilities
   - Document contact information

2. **Detection and Analysis**:
   - Implement monitoring to detect incidents
   - Have procedures for analyzing potential incidents

3. **Containment and Eradication**:
   - Procedures for containing security breaches
   - Steps for removing threats

4. **Recovery**:
   - Restore systems to normal operation
   - Verify system integrity

5. **Post-Incident Activities**:
   - Document lessons learned
   - Update security measures
   - Improve incident response procedures

## Conclusion

Security is an ongoing process, not a one-time task. Regularly review and update your security measures to address new threats and vulnerabilities. By following this guide, you can significantly improve the security posture of your Cryptobot installation.

For additional assistance or to report security issues, please contact the Cryptobot security team.
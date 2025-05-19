## 7. Account Management & API Keys

To interact with CryptoBot's services programmatically (e.g., via its API for trading or strategy management), you will typically use API keys for authentication. This section explains how to manage these keys.

*(This guide assumes interaction via an API client or a UI that consumes the key management API, likely provided by an authentication service.)*

### Understanding API Keys

*   **Purpose**: API keys are unique identifiers used to authenticate your requests to the CryptoBot API, ensuring that only authorized users or applications can access your account and perform actions.
*   **Security**: Treat your API keys like passwords. Keep them confidential and secure. Do not share them publicly or embed them directly in client-side code that might be exposed.
*   **Permissions**: API keys can be associated with specific permissions (e.g., read-only access, trading access, account management). Ensure your keys have only the necessary permissions for their intended use. *(The current system's permission granularity might vary).*

### Managing Your API Keys

The following operations are typically available for managing your API keys. These would be accessed via specific API endpoints (e.g., under `/api/keys/...` from the `auth-service`) or a dedicated section in the user interface.

**1. Viewing Your Current Active Key**
   *   You can usually retrieve details about your currently active API key.
   *   **How**: Typically a `GET` request to an endpoint like `/api/keys/current`.
   *   **Information**: This might show the key's creation date, expiration date, associated permissions, and its active status. The actual key secret is usually not displayed again after creation for security reasons.

**2. Rotating API Keys**
   *   Rotating API keys means deactivating an old key and generating a new one. This is a good security practice to do periodically or if you suspect a key might have been compromised.
   *   **How**: Usually a `POST` request to an endpoint like `/api/keys/rotate`.
   *   **Process**:
        *   A new API key is generated.
        *   The old key is often kept active for a short "grace period" to allow you to update your applications with the new key without immediate disruption. After the grace period, the old key is deactivated.
   *   **Outcome**: The new API key value is returned. You should immediately update your applications and scripts to use this new key.

**3. Revoking API Keys**
   *   If an API key is no longer needed or is suspected to be compromised, you should revoke it immediately.
   *   **Revoking Current Active Key**:
        *   **How**: Typically a `POST` request to an endpoint like `/api/keys/revoke-current`.
        *   **Outcome**: Your current active key is deactivated. You will need to generate a new key if you need API access.
   *   **Revoking All Keys (User-initiated)**:
        *   **How**: A `POST` request to an endpoint like `/api/keys/revoke-all`.
        *   **Outcome**: All API keys associated with your user account are deactivated.
   *   **Emergency Revocation (Admin-initiated)**:
        *   In critical situations, an administrator might perform an emergency revocation of all keys for a user.
        *   **How**: Typically a `POST` request to an endpoint like `/api/keys/emergency-revoke` (requires admin privileges and specifies the target user).
        *   **Outcome**: All keys for the specified user are immediately deactivated.

**4. Viewing Key History**
   *   You can often view a history of your API keys, including their creation dates, versions, and status (active, rotated, revoked).
   *   **How**: Typically a `GET` request to an endpoint like `/api/keys/history`.
   *   **Information**: This helps track key lifecycle and audit key-related events. Each key entry usually includes an audit log of actions performed on it (created, rotated, revoked).

**5. Key Rotation Settings (If available)**
   *   Some systems allow configuring automatic key rotation policies or notification preferences for expiring keys.
   *   **How**: Usually a `POST` request to an endpoint like `/api/keys/settings`.

### Best Practices for API Key Security

*   **Store Securely**: Store your API keys in a secure location, such as a password manager or encrypted configuration file. Do not commit them to version control.
*   **Principle of Least Privilege**: When creating keys, assign them only the permissions necessary for their intended task.
*   **Regular Rotation**: Rotate your API keys periodically, even if they haven't been compromised.
*   **Monitor Usage**: If the system provides API usage logs, monitor them for any suspicious activity.
*   **Revoke Immediately**: If you suspect a key has been compromised, revoke it without delay.
*   **Use Environment Variables**: For applications or scripts, store API keys in environment variables rather than hardcoding them.

By following these guidelines, you can help ensure the security of your account and your interactions with the CryptoBot platform.
# Security Configuration Guide

This document explains the security features and considerations when using Serena locally.

## Network Access Overview

Serena may attempt to access external networks for various purposes:

### 1. Token Counting APIs
**Risk Level: HIGH** 🔴

- **What**: Sends your source code to external APIs (like Anthropic) for precise token counting
- **Data Exposure**: Your actual source code content is transmitted to external servers
- **Controlled by**: `allow_network_token_counting` configuration option
- **Default**: `false` (blocked for security)
- **Recommendation**: Only enable for non-sensitive code that you're comfortable sharing with external services

### 2. Language Server Downloads  
**Risk Level: MEDIUM** 🟡

- **What**: Downloads language server binaries and dependencies from external sources
- **Data Exposure**: No source code sent, but downloads executable files from internet
- **Sources**: GitHub releases, Visual Studio Marketplace, JetBrains, Gradle, etc.
- **Controlled by**: `allow_language_server_downloads` configuration option  
- **Default**: `false` (blocked for security)
- **Recommendation**: Enable only on trusted networks and when you need language server features

### 3. Model Downloads (TikToken)
**Risk Level: LOW** 🟢

- **What**: Downloads tokenizer models for offline token counting
- **Data Exposure**: No source code sent, one-time model downloads
- **Controlled by**: Enabled by default when using TikToken estimator
- **Recommendation**: Generally safe, but can be disabled in strict environments

## Security Modes

Serena provides three security modes:

### Strict Mode (Default)
```yaml
# All external network access disabled
allow_network_token_counting: false
allow_language_server_downloads: false
```

### Selective Mode
```yaml  
# Allow specific features as needed
allow_network_token_counting: false  # Still requires explicit opt-in
allow_language_server_downloads: true
```

### Permissive Mode
```yaml
# Allow all external access (least secure)
allow_network_token_counting: true
allow_language_server_downloads: true
```

## Recommended Configurations

### For Production/Enterprise Use
```yaml
# Serena config
allow_network_token_counting: false
allow_language_server_downloads: false
token_count_estimator: "TIKTOKEN_GPT4O"  # Offline token counting
record_tool_usage_stats: false
```

### For Development/Personal Use
```yaml
# Serena config
allow_network_token_counting: false  # Still disabled by default
allow_language_server_downloads: true  # Enable language features
token_count_estimator: "TIKTOKEN_GPT4O"
record_tool_usage_stats: true
```

### For Non-Sensitive Projects Only
```yaml
# Only if you're comfortable with external API access
allow_network_token_counting: true
allow_language_server_downloads: true
token_count_estimator: "ANTHROPIC_CLAUDE_SONNET_4"
record_tool_usage_stats: true
```

## Implementation Details

### Blocked Downloads Will Show Clear Errors
When external downloads are blocked, you'll see clear error messages like:

```
SECURITY: Attempted to download file from external URL: https://github.com/...
This has been blocked for security. Set allow_external_downloads=True to enable external downloads.
```

### Language Servers That Require Downloads
These language servers may need external downloads to function:
- **Java** (Eclipse JDT-LS): Downloads JRE, Gradle, VS Code Java extension
- **Kotlin**: Downloads Kotlin language server
- **C#**: Downloads .NET runtime components
- And others...

### Offline Alternatives
- Use TikToken instead of Anthropic for token counting
- Pre-install language servers manually if needed
- Use IDE-based language servers instead of downloaded ones

## Monitoring and Logging

Serena logs all network access attempts, so you can monitor what's being accessed:

```
INFO: Loading tiktoken encoding for model gpt-4o, this may take a while on the first run.
INFO: Note: This will download tokenizer models from OpenAI but does not send your code to external servers.
WARNING: SECURITY: Attempted to download file from external URL: https://github.com/...
```

## Best Practices

1. **Start with strict mode** - Enable features as needed
2. **Review configuration regularly** - Ensure settings match your security requirements  
3. **Use offline alternatives** when possible
4. **Monitor logs** for unexpected network access attempts
5. **Separate sensitive and non-sensitive projects** - Use different configurations
6. **Update security settings** when switching between projects of different sensitivity levels

## Questions?

If you're unsure about a security setting:

1. **When in doubt, keep it disabled**
2. **Check the logs** to see what's being blocked
3. **Enable selectively** only the features you actually need
4. **Consider your organization's policies** about external service usage
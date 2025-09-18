# Gmail MCP Server - User Guide

This guide provides setup instructions, configuration examples, and LLM prompts to help you effectively use the Gmail MCP Server's multi-mailbox functionality.

## Quick Setup

### 1. Server Setup

The Gmail MCP Server uses a clean subcommand structure with configuration file support.

#### Create Configuration File

```bash
# Copy sample configuration
cp hack/config.yaml config.yaml

# Edit with your paths
vim config.yaml
```

**config.yaml example:**

```yaml
# Gmail MCP Server Configuration

# Required: Path to OAuth 2.0 credentials file
creds_file: ~/.creds/gmail/creds.json

# Required: Directory containing mailbox subdirectories
mailbox_dir: ~/.creds/gmail/mailboxes/

# MCP Server configuration
mcp:
  mode: http            # 'http' or 'stdio'

# HTTP server configuration (only used when mcp.mode = http)
http:
  port: 63417          # Server port
  addr: localhost      # Server address

# Optional: Default mailbox to use
# mailbox: personal
```

#### Add Your First Mailbox

```bash
# Using config file (recommended)
emseepee gmail add --name personal --config-file config.yaml

# Using direct arguments
emseepee gmail add \
  --name personal \
  --creds-file ~/.creds/gmail/creds.json \
  --mailbox-dir ~/.creds/gmail/mailboxes/
```

#### Start the Server

```bash
# Using config file (recommended)
emseepee gmail serve --config-file config.yaml

# With overrides for specific use cases
emseepee gmail serve \
  --config-file config.yaml \
  --port 8080 \
  --mailbox=personal \
  --log-level=debug
```

### 2. Multi-Mailbox Setup

Add multiple Gmail accounts for comprehensive email management:

```bash
# Add personal account
emseepee gmail add --name personal --config-file config.yaml

# Add work account with custom settings
emseepee gmail add \
  --name work \
  --config-file config.yaml \
  --mailbox-dir /custom/work/mailboxes/

# Add side project account
emseepee gmail add --name startup --config-file config.yaml

# Verify all mailboxes
emseepee gmail serve --config-file config.yaml
# Then use list_mailboxes tool to confirm setup
```

## Multi-Mailbox Email Analysis

The Gmail MCP Server supports analyzing emails across multiple Gmail accounts simultaneously. Here are example prompts to get you started with the updated CLI structure.

### Comprehensive Email Analysis Prompt

Use this prompt for a complete overview of all your unread emails:

```text
I want you to analyze emails across all my Gmail mailboxes and create a comprehensive report. Please:

1. **Discover Available Mailboxes**: First, list all available mailboxes to see what accounts we're working with.

2. **Get Unread Emails from ALL Mailboxes**: Retrieve unread emails from all mailboxes (use the "all mailboxes" functionality) and organize them by mailbox.

3. **Create Individual Mailbox Tables**: For each mailbox, create a well-formatted table showing:
   - Subject (truncated to reasonable length)
   - Sender
   - Date
   - Labels (show label names, not just IDs)
   - Snippet (first 50-100 characters)

4. **Summary Analysis**: Provide a summary that includes:
   - Total unread emails across all mailboxes
   - Breakdown by mailbox
   - Most common labels across all emails
   - Any patterns you notice (promotional emails, important emails, etc.)

Please format the tables nicely with clear headers and make sure to show which emails belong to which mailbox. If there are no unread emails in a mailbox, just mention that.

Start by getting up to 10 emails total to keep the output manageable, but distribute them across all available mailboxes.
```

### Email Triage Prompt

Use this prompt when you need to quickly prioritize your emails:

```text
I need to quickly triage my unread emails across all my Gmail accounts. Please:

1. Get unread emails from ALL my mailboxes (use the empty list [] to get from all)
2. Create a priority-sorted table with these columns:
   - Mailbox
   - Subject
   - Sender
   - Priority (based on labels like "Important", "Urgent", etc.)
   - Labels
   - Date

3. Group them by priority:
   - High Priority (Important, Starred, etc.)
   - Work Related (based on sender domains or labels)
   - Personal
   - Promotional/Low Priority

4. Recommend which emails I should read first based on the labels and senders.

Limit to 15 emails total so it's not overwhelming, but make sure to sample from all my mailboxes.
```

### Technical Testing Prompt

Use this prompt to test and verify the multi-mailbox functionality:

```text
I want to test the multi-mailbox Gmail functionality. Please:

1. **List mailboxes**: Show me all available mailboxes that were set up with `emseepee gmail add`
2. **Test current mailbox**: Get 3 unread emails from the current mailbox only
3. **Test specific mailboxes**: Get emails from specific mailboxes (pick 2 from the list)
4. **Test ALL mailboxes**: Get emails from ALL mailboxes using both methods:
   - Using empty list: mailboxes=[]
   - Using "all" keyword: mailboxes=["all"]
5. **Verify consistency**: Confirm both "all" methods return the same results

For each test, create a table showing:
- Email ID
- Subject
- Mailbox ID
- Labels (with both ID and name)
- Sender

This will help verify that the mailbox parameter is working correctly and that emails are properly tagged with their source mailbox.

Note: Make sure the server was started with `emseepee gmail serve --config-file config.yaml` and all mailboxes were properly added using `emseepee gmail add` commands.
```

## How the LLM Will Process These Prompts

When you use these prompts, the LLM will automatically:

1. **Discover Mailboxes**: Call `list_mailboxes` to see all available Gmail accounts
2. **Fetch Emails**: Use `get_unread_emails` with the appropriate mailbox parameters:
   - `mailboxes=[]` - Gets emails from ALL mailboxes
   - `mailboxes=["all"]` - Alternative way to get emails from ALL mailboxes
   - `mailboxes=["account1", "account2"]` - Gets emails from specific mailboxes
   - No `mailboxes` parameter - Uses current mailbox only
3. **Organize Data**: Group emails by their `mailbox_id` field
4. **Extract Labels**: Use the `labels` array containing both label IDs and names
5. **Create Tables**: Format the information into readable tables
6. **Provide Analysis**: Offer insights and recommendations

## Expected Output Format

The LLM will generate organized output like this:

```markdown
# Gmail Multi-Mailbox Analysis

## Available Mailboxes
- **personal**: john.doe@gmail.com (current)
- **work**: john.doe@company.com
- **side-project**: john@startup.com

## Unread Emails by Mailbox

### Personal Mailbox (personal)
| Subject        | Sender           | Date   | Labels           | Snippet                            |
|----------------|------------------|--------|------------------|------------------------------------|
| Weekend Plans  | friend@email.com | Dec 15 | Inbox, Personal  | Hey, want to grab dinner this...   |
| Bank Statement | bank@chase.com   | Dec 14 | Inbox, Important | Your monthly statement is ready... |

### Work Mailbox (work)
| Subject   | Sender              | Date   | Labels                 | Snippet                        |
|-----------|---------------------|--------|------------------------|--------------------------------|
| Q4 Review | manager@company.com | Dec 15 | Inbox, Important, Work | Please review the quarterly... |

## Summary
- **Total unread emails**: 8
- **Personal**: 3 emails
- **Work**: 4 emails
- **Side-project**: 1 email
- **Most common labels**: Inbox (8), Important (3), Work (4)
```

## Advanced Usage Tips

### Mailbox Parameter Options

The `get_unread_emails` tool supports several ways to specify which mailboxes to query:

- **Current mailbox** (default): `get_unread_emails(max_emails=5)`
- **Specific mailboxes**: `get_unread_emails(max_emails=5, mailboxes=["work", "personal"])`
- **All mailboxes (method 1)**: `get_unread_emails(max_emails=10, mailboxes=[])`
- **All mailboxes (method 2)**: `get_unread_emails(max_emails=10, mailboxes=["all"])`

### Label Information

Each email includes rich label information:

```json
{
  "labels": [
    {"id": "INBOX", "name": "Inbox"},
    {"id": "IMPORTANT", "name": "Important"},
    {"id": "Label_123", "name": "My Custom Label"}
  ]
}
```

### Best Practices

1. **Start Small**: Begin with 5-10 emails to avoid overwhelming output
2. **Use Specific Mailboxes**: When you know which account you're interested in, specify it explicitly
3. **Leverage Labels**: Use label information to categorize and prioritize emails
4. **Combine with Other Tools**: Use `read_email` to get full content of important emails identified in your analysis

## Troubleshooting

If you encounter issues:

### Server Setup Issues

1. **Server won't start**:
   - Check config file syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
   - Verify required fields: `creds_file` and `mailbox_dir` are present
   - Try direct arguments: `emseepee gmail serve --creds-file ~/.creds/gmail/creds.json --mailbox-dir ~/.creds/gmail/mailboxes/`

2. **Mailbox not found**:
   - Use `emseepee gmail add --name <mailbox> --config-file config.yaml` to add mailboxes first
   - Check mailbox directory exists: `ls -la ~/.creds/gmail/mailboxes/`
   - Verify tokens.json exists in each mailbox subdirectory

3. **Configuration issues**:
   - Ensure config file uses correct YAML syntax (spaces, not tabs for indentation)
   - Check paths are correct (use `~` for home directory)
   - Verify nested structure: `mcp.mode`, `http.port`, `http.addr`

### Multi-Mailbox Issues

1. **No emails returned**: Check if you have unread emails using `list_mailboxes` first
2. **Missing mailboxes**: Ensure all your Gmail accounts are properly added with `emseepee gmail add`
3. **Label issues**: Some labels might be system-generated and appear as IDs only
4. **Rate limiting**: If you have many emails, start with smaller `max_emails` values

### Migration Issues

1. **Legacy structure**: Use `./migrate_tokens.sh` to migrate from old `--tokens-dir` structure
2. **Authentication problems**: Check that OAuth credentials file exists and is valid

## Related Tools

The Gmail MCP Server provides many other useful tools you can combine with multi-mailbox email analysis:

- `send_email` - Send emails from any mailbox
- `read_email` - Get full content of specific emails
- `list_labels` - See all available labels in a mailbox
- `search_emails` - Find emails matching specific criteria
- `mark_email_as_read` - Process emails after analysis

For more technical details, see the [Developer Documentation](../developer/README.md).

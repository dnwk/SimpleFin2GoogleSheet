# SimpleFin to Google Sheets Integration

**Automated Financial Data Aggregation for Personal Finance Management**

This Python script automatically syncs **all your US bank accounts** from multiple financial institutions into a single Google Sheet using SimpleFin Bridge. Get a unified view of your finances with automatic updates of account balances and transactions - no manual data entry required.

## 🎯 Use Cases

### Personal Finance Management
- **Unified Dashboard**: See all your bank accounts, credit cards, and investments in one Google Sheet
- **Budget Tracking**: Monitor spending across all accounts without logging into multiple banking websites
- **Transaction Analysis**: Analyze spending patterns with 60 days of transaction history
- **Net Worth Monitoring**: Track total balances across all financial institutions
- **Financial Planning**: Export data for tax preparation, expense reports, or financial advisors

### Automation Benefits
- **Save Time**: No more manual copying of transactions from multiple bank websites
- **Stay Updated**: Schedule automatic syncs (daily/weekly) to keep data current
- **Historical Records**: Maintain transaction history in accessible spreadsheet format
- **Multi-Bank Support**: Connect unlimited banks through SimpleFin's secure aggregation service
- **Selective Syncing**: Choose which accounts to track using ignore flags

### Why Use This?

**Traditional Problem:**
- Multiple bank accounts = Multiple logins
- Manual transaction downloads are tedious
- Data in different formats from each bank
- Hard to get comprehensive financial overview
- Time-consuming to track spending across institutions

**This Solution:**
- ✅ **One-time setup** connects all your banks via SimpleFin
- ✅ **Automated syncing** keeps data current without manual intervention
- ✅ **Standardized format** in familiar Google Sheets interface
- ✅ **Complete visibility** across all financial accounts
- ✅ **Privacy control** - your data stays in your Google Sheet

## ✨ Key Features

### Account Aggregation
- 🏦 **Multi-Bank Support**: Connect unlimited banks and financial institutions through SimpleFin Bridge
- 📊 **Automatic Discovery**: Detects new accounts automatically when added to SimpleFin
- 🔄 **Smart Syncing**: Only updates accounts you want (configurable ignore flags)
- 💰 **Real-Time Balances**: Fetches current balance for all connected accounts
- 📁 **Organized Structure**: Each account gets its own dedicated sheet

### Transaction Management
- 📅 **60-Day History**: Automatically pulls last 60 days of transactions
- ⏰ **Date Conversion**: Unix timestamps converted to readable dates with EPOCHTODATE formula
- 📈 **Sorted Display**: Transactions organized newest-first for easy review
- 🔍 **Detailed Data**: Includes description, amount, transaction ID, and pending status
- 💳 **All Account Types**: Supports checking, savings, credit cards, investments, loans

### Index Sheet Dashboard
- 📋 **Central Overview**: Master index with all accounts at a glance
- 🎨 **Professional Formatting**: Green header row, frozen for easy scrolling
- 🔗 **Navigation Links**: Click account names to jump to detailed sheets
- ✅ **Ignore Control**: Toggle sync on/off for individual accounts
- 🕐 **Last Updated Timestamps**: See when each account was last synced
- ⚡ **Quick Setup**: First run automatically populates all accounts

### Automation & Reliability
- 🔁 **Retry Logic**: Automatic retries on timeout/connection errors (up to 3 attempts)
- ⏱️ **Rate Limiting**: Built-in delays prevent Google Sheets API quota issues
- 📝 **Comprehensive Logging**: Detailed logs for troubleshooting and monitoring
- 🛡️ **Error Handling**: Graceful handling of API errors with clear messages
- 🔒 **Secure Authentication**: Uses OAuth service accounts for Google Sheets access

### Smart Features
- 🆕 **New Account Detection**: Automatically finds accounts added after initial setup
- 🔄 **Initial Setup Mode**: First run populates Index, then exits for review
- 📌 **State Management**: Remembers ignore flags and sheet mappings between runs
- 🏷️ **Duplicate Handling**: Automatically numbers duplicate account names
- 🔙 **Navigation**: "Back to Index" links in every account sheet
- 📐 **Column Formatting**: Optimized column widths for readability

### User Control
- 🎛️ **Selective Syncing**: Choose which accounts to update via ignore flag
- 🗓️ **Flexible Scheduling**: Run on-demand or schedule for automatic updates
- 🛠️ **Configurable**: Simple JSON configuration for easy customization
- 📊 **Google Sheets Native**: Work with familiar spreadsheet tools and formulas
- 🔐 **Privacy First**: Your financial data stays in your own Google account

## 🏦 How SimpleFin Bridge Works

**SimpleFin** is a secure financial data aggregation service that:
- Connects to thousands of banks and financial institutions
- Uses bank-grade security (same as Plaid, Mint, etc.)
- Provides standardized API access to your account data
- Eliminates need to share bank credentials with third-party apps
- Offers affordable pricing compared to enterprise solutions

**This script leverages SimpleFin to:**
1. Connect once to all your banks through SimpleFin's interface
2. Automatically fetch account balances and transactions
3. Sync data to your Google Sheet on your schedule
4. Maintain up-to-date financial overview without manual work

**Security Benefits:**
- Your bank passwords stay with SimpleFin (not in this script)
- Script only needs read-only SimpleFin access URL
- Data flows: Banks → SimpleFin → Your Script → Your Google Sheet
- You control the Google Sheet access and sharing

## 📊 What You Get

### Consolidated Financial Overview
- All bank accounts in one spreadsheet
- Current balances updated automatically
- 60 days of transaction history per account
- Easy-to-read format with proper date formatting
- Clickable navigation between accounts

### Time Savings
- No more logging into multiple bank websites
- No manual transaction downloads or copying
- Automated data refresh on your schedule
- Quick access to financial data anytime

### Financial Insights
- Compare spending across different accounts
- Track balance changes over time
- Identify recurring transactions
- Export data for budgeting apps or tax prep
- Create custom charts and pivot tables in Google Sheets

## How It Works

### Workflow

**First Run (Initial Setup):**
1. Creates Index sheet with column headers
2. Fetches all accounts from SimpleFin
3. Populates Index with account list (all set to ignore=false)
4. Exits with message to review Index

**Subsequent Runs (New Accounts Found):**
1. Reads existing Index sheet
2. Queries SimpleFin for current accounts
3. Detects new accounts not in Index
4. Appends new accounts to Index (ignore=false)
5. Exits with message to review

**Normal Sync (No New Accounts):**
1. Reads Index sheet
2. Checks SimpleFin for new accounts (none found)
3. Filters accounts where ignore=false
4. Processes each account one at a time:
   - Fetches transactions from SimpleFin
   - Updates/creates Google Sheet
   - Formats data with headers and formulas
5. Updates Index with latest balances and timestamps

### Index Sheet Structure

The Index sheet tracks all accounts with these columns:

| Column | Description | Example |
|--------|-------------|---------|
| **Account Name** | Name with hyperlink to sheet | =HYPERLINK(...) |
| **Account ID** | Unique SimpleFin account ID | abc123xyz |
| **Balance** | Current account balance | 1234.56 |
| **Sheet Name** | Name of the account's sheet | Checking Account |
| **Ignore** | Skip this account? (true/false) | false |
| **Last Updated** | Timestamp of last sync | 2025-11-13 14:30:00 |

**To skip syncing an account**: Change "Ignore" column to `true`

### Account Sheet Structure

Each account has its own sheet containing:

**Account Information:**
- Account Name
- Account ID  
- Balance
- Currency
- Available Balance

**Transactions Table:**
- Date (converted from Unix timestamp using `EPOCHTODATE()`)
- Description
- Amount
- Transaction ID
- Pending Status

**Navigation:**
- "← Back to Index" link at bottom

## Prerequisites

1. **SimpleFin Account**: You need a SimpleFin account with an access URL
2. **Google Cloud Project**: Set up a Google Cloud project with Sheets API enabled
3. **Service Account**: Create a service account and download credentials JSON
4. **Google Sheet**: Create a Google Sheet and share it with your service account email

## Setup Instructions

### 1. SimpleFin Setup

1. Sign up for SimpleFin at https://www.simplefin.org/
2. Create a SimpleFin token:
   - Go to https://beta-bridge.simplefin.org/my-account/tokens/create
   - Create a new token
   - Copy the base64-encoded token (it will look like a long string of random characters)
   - This token contains your claim URL encoded in base64 format
   
   ⚠️ **IMPORTANT**: Each token can only be claimed ONCE to generate an access URL. The script automatically saves the access URL to your config file after claiming. Keep the generated access URL safe, as you cannot claim the same token again.

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create a service account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and create
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose JSON format
   - Download and save as `credentials.json` in this directory

### 3. Google Sheet Setup

1. Create a new Google Sheet or use an existing one
2. Copy the Spreadsheet ID from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Share the spreadsheet with your service account email:
   - Open the Google Sheet
   - Click "Share"
   - Add the service account email (found in `credentials.json` as `client_email`)
   - Grant "Editor" permissions

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure the Script

1. Copy `config.json.example` to `config.json`:
   ```powershell
   Copy-Item config.json.example config.json
   ```

2. Edit `config.json` with your settings:
   ```json
   {
     "simplefin_token": "your-base64-encoded-token-here",
     "google_credentials_file": "credentials.json",
     "spreadsheet_id": "your-spreadsheet-id-here"
   }
   ```

   **Configuration Fields:**
   - `simplefin_token`: Your base64-encoded SimpleFin token (created at https://beta-bridge.simplefin.org/my-account/tokens/create)
   - `google_credentials_file`: Path to your Google service account credentials JSON file
   - `spreadsheet_id`: The ID of your Google Spreadsheet (from the URL)

## Usage

### First Time Setup

1. **Run the script for initial setup:**
   ```powershell
   python simplefin_to_sheets.py
   ```

2. **What happens:**
   - Script creates Index sheet with green header
   - Fetches all accounts from SimpleFin
   - Populates Index with all accounts (ignore=false by default)
   - **Exits automatically** with message to review

3. **Review the Index sheet:**
   - Open your Google Sheet
   - Check the Index sheet
   - For accounts you don't want to sync, change "Ignore" column to `true`
   - Save changes

4. **Run script again to begin syncing:**
   ```powershell
   python simplefin_to_sheets.py
   ```

### Regular Usage

Run the script whenever you want to sync:

```powershell
python simplefin_to_sheets.py
```

**The script will:**
1. Read Index sheet
2. Check SimpleFin for new accounts
   - **If new accounts found**: Adds them to Index and exits (review required)
   - **If no new accounts**: Continues to step 3
3. Process each non-ignored account:
   - Fetch latest transactions (last 60 days)
   - Update or create account sheet
   - Format data with proper dates and headers
4. Update Index with latest balances and timestamps
5. Add navigation links between Index and account sheets

### Managing Accounts

**To stop syncing an account:**
1. Open the Index sheet
2. Find the account row
3. Change "Ignore" column from `false` to `true`
4. Next run will skip this account

**When new accounts appear in SimpleFin:**
- Script automatically detects them
- Adds to Index sheet with ignore=false
- Exits for you to review
- Run again to sync the new accounts

### Understanding Script Behavior

| Scenario | Script Action |
|----------|---------------|
| Index sheet is empty | Initial setup: populate Index, then exit |
| New SimpleFin accounts found | Add to Index, then exit for review |
| No new accounts, some ignored | Sync only non-ignored accounts |
| All accounts ignored | Reads Index, finds nothing to sync, exits |
| Account removed from SimpleFin | Keeps in Index (won't update) |

## Output Format

### Index Sheet

**Header Row** (green background, white text, frozen):
- Account Name (with hyperlink to account sheet)
- Account ID
- Balance
- Sheet Name
- Ignore (true/false)
- Last Updated

**Data Rows:**
- One row per account
- Clickable account names link to sheets
- Ignore column controls sync behavior
- Last Updated shows most recent sync time

### Account Sheets

Each account has its own sheet with:

**Account Information Section:**
- Account Name
- Account ID
- Balance
- Currency
- Available Balance

**Transactions Section:**
- **Date**: Unix timestamp converted to readable date via `=EPOCHTODATE()` formula
- **Description**: Transaction description
- **Amount**: Transaction amount (as string from SimpleFin)
- **Transaction ID**: Unique transaction identifier
- **Pending**: "Yes" or "No" status

**Navigation:**
- "← Back to Index" hyperlink at bottom of each sheet

**Transaction Details:**
- Sorted by date (newest first)
- Limited to last 60 days
- Automatically formatted headers
- Date formulas display in local timezone

## Logging

Logs are written to:
- Console output (INFO level and above)
- `simplefin_sync.log` file (all levels)

## Scheduling

You can schedule this script to run automatically:

### Windows Task Scheduler

1. Open Task Scheduler
2. Create a new task
3. Set trigger (e.g., daily at specific time)
4. Set action to run:
   ```
   Program: python
   Arguments: C:\localfiles\SimpleFIN-GoogleSheet\simplefin_to_sheets.py
   Start in: C:\localfiles\SimpleFIN-GoogleSheet
   ```

### Using Windows PowerShell Script

Create a `.ps1` file to run the script:

```powershell
cd C:\localfiles\SimpleFIN-GoogleSheet
python simplefin_to_sheets.py
```

Then schedule this PowerShell script using Task Scheduler.

## Troubleshooting

### Common Issues

#### Script Exits After Running

**This is normal behavior in these cases:**
- **First run**: Index populated, review needed before syncing
- **New accounts detected**: New accounts added to Index, review required
- **All accounts ignored**: Nothing to sync

**To proceed**: Review Index sheet and run script again.

#### Authentication Errors

**SimpleFin Errors:**
- Verify your access URL is correct and active
- Check `simplefin_access_url` in `config.json` is valid
- If HTTP 403: Token may be revoked, create new one

**Google Sheets Errors:**
- Ensure service account email has Editor access to spreadsheet
- Verify `spreadsheet_id` in config matches your sheet URL
- Check credentials.json is valid and not expired

### HTTP 403 Forbidden Error

If you receive an HTTP 403 error:

**1. SimpleFin Token Already Claimed:**
- Your token has been used and cannot be claimed again
- **Solution:**
  - Create new token at https://beta-bridge.simplefin.org/my-account/tokens/create
  - Update `simplefin_token` in `config.json` with new token
  - Remove `simplefin_access_url` from `config.json` to force new claim
  - Run script again

**2. SimpleFin Access URL Revoked:**
- Your access URL is no longer valid (expired or manually revoked)
- **Solution:**
  - Create new token (same steps as above)
  - Delete old `simplefin_access_url` field
  - Script will claim new token and save new access URL

**3. Configuration Issue:**
- Ensure `config.json` has either valid `simplefin_token` OR `simplefin_access_url`
- Check for extra spaces/newlines in values
- Verify JSON syntax is correct

### SimpleFin API Timeout Errors

**Error message:** `Read timed out` or `HTTPSConnectionPool ... timeout`

**Cause:** SimpleFin API didn't respond within 30 seconds

**Solution:** 
- Script automatically retries up to 3 times with exponential backoff (1s, 2s, 4s delays)
- Usually resolves automatically
- If persists, SimpleFin service may be experiencing issues
- Check SimpleFin status or try again later

### Google Sheets Rate Limit Errors

**Error:** HTTP 429 or "Quota exceeded"

**Cause:** Too many API calls in short time (60 read requests/minute limit)

**Solution:**
- Script has built-in rate limiting with delays
- Automatic retry with exponential backoff (up to 5 attempts)
- If error persists, reduce sync frequency
- Let script complete without interruption

### Sheet Name Conflicts

**Issue:** Multiple accounts with same name

**Solution:**
- Script automatically appends numbers to duplicate names
- Example: "Checking Account", "Checking Account (2)", "Checking Account (3)"
- Check Index sheet "Sheet Name" column for actual names used

### Formulas Not Working

**Issue:** `EPOCHTODATE()` displays as text with quotes

**Cause:** `valueInputOption` was set to 'RAW' instead of 'USER_ENTERED'

**Solution:**
- **Fixed in current version** - formulas now process correctly
- If still seeing issue, check Google Sheets supports EPOCHTODATE function
- Alternatively, dates may need manual formatting in Google Sheets

### Missing Transactions

**Issue:** No transactions showing for account

**Possible causes:**
- SimpleFin may not have data for last 60 days
- Financial institution connection may be outdated
- Account may have no activity in period

**Solution:**
- Check SimpleFin dashboard for account status
- Verify financial institution connection is active
- Wait for transactions to post and run script again

### New Accounts Not Detected

**Issue:** Added account in SimpleFin but script doesn't find it

**Solution:**
- Ensure SimpleFin account is fully set up and active
- Run script again (may take a few minutes for SimpleFin to update)
- Check script logs for errors during account fetch
- Manually verify account appears in SimpleFin API response

### Index Sheet Changes Lost

**Issue:** Changes to Ignore column get overwritten

**Cause:** Script preserves existing Ignore flags, but may reset if Index is recreated

**Solution:**
- Don't delete Index sheet - script uses it for state
- Changes to Ignore column persist across runs
- If Index deleted, script treats as initial setup and resets all flags

## Important Notes & Best Practices

### Script Behavior

⚠️ **Exit Conditions** - Script will exit (not continue syncing) when:
- Index sheet is empty (initial setup)
- New SimpleFin accounts are detected and added
- This is intentional to let you review changes before syncing

✅ **Run script twice when**:
1. First time: Populates Index → exits
2. Second time: Syncs data → completes

### Data Management

📊 **Index Sheet is Critical**:
- Do NOT delete the Index sheet
- It tracks which accounts to sync/ignore
- Contains state information for smart updates
- If deleted, script treats as initial setup and resets

🔄 **Account Ignore Flags**:
- Set to `true` to skip syncing an account
- Changes persist across script runs
- Useful for archived or inactive accounts
- You can toggle anytime

📅 **Transaction Date Range**:
- Fixed at last 60 days
- Unix timestamps converted to readable dates via `EPOCHTODATE()` formula
- Dates display in your Google Sheets locale timezone

### Performance & Rate Limits

⏱️ **Google Sheets API Limits**:
- 60 read requests per minute per user
- Script includes 0.5-1 second delays between operations
- Automatic retry with exponential backoff on rate limits
- Don't run multiple instances simultaneously

🔄 **SimpleFin API Retry Logic**:
- Automatic retry on timeout/connection errors (up to 3 attempts)
- Exponential backoff: 1s, 2s, 4s delays
- No retry on token claiming (immediate fail for invalid tokens)

🚀 **Processing Speed**:
- Processes one account at a time
- Alternates between SimpleFin API and Google Sheets API
- Average: ~2-3 seconds per account
- Total time depends on number of active accounts

### SimpleFin Token Management

🔑 **Token vs Access URL**:
- **Token**: One-time use claim token (base64-encoded)
- **Access URL**: Permanent credentials (saved after claiming)
- Script automatically saves access URL to config
- You can delete token from config after first successful run

⚠️ **Token Claiming**:
- Each token can only be claimed ONCE
- Script does NOT retry token claiming (fails immediately)
- If claim fails, token is likely invalid or already used
- Create new token at: https://beta-bridge.simplefin.org/my-account/tokens/create

🔒 **Access URL Storage**:
- Automatically saved to `config.json` as `simplefin_access_url`
- Contains authentication credentials in URL
- Reused on subsequent runs
- Keep config.json secure and private

### Google Sheets Considerations

📝 **Formula Processing**:
- `valueInputOption` set to 'USER_ENTERED'
- Allows `EPOCHTODATE()` and `HYPERLINK()` formulas to work
- Formulas are evaluated by Google Sheets
- Manual edits to formulas will be overwritten on next sync

🔗 **Hyperlinks**:
- Index has clickable account names → links to account sheets
- Each account sheet has "← Back to Index" link
- Links use sheet name references
- May break if you manually rename sheets

🎨 **Formatting**:
- Index header has green background (#008000) with white text
- Header row is frozen for easy scrolling
- Account sheets have basic header formatting
- Custom formatting may be overwritten on updates

### Scheduling Considerations

⏰ **Recommended Frequency**:
- Daily sync: Best for active accounts
- Weekly sync: Fine for low-activity accounts
- Avoid: More than once per hour (unnecessary API usage)

🔔 **What to Monitor**:
- Check logs in `simplefin_sync.log`
- Look for repeated errors or timeouts
- Verify Index sheet ignore flags are respected
- Confirm new accounts are detected properly

### Data Accuracy

💰 **Balance Values**:
- Displayed as-is from SimpleFin (strings, not numbers)
- No conversion or formatting applied
- May include currency symbols from SimpleFin
- Use Google Sheets formulas if calculations needed

📊 **Transaction Amounts**:
- Stored as strings from SimpleFin API
- Negative = money out, Positive = money in
- No rounding or formatting applied by script

🕐 **Timestamps**:
- "Last Updated" in Index shows sync time
- Transaction dates use EPOCHTODATE formula
- Dates display in your timezone
- Format controlled by Google Sheets locale settings

## Security Notes

⚠️ **Critical Security Considerations:**

### Protect Your Credentials

**Never commit to version control:**
- `config.json` - Contains SimpleFin credentials
- `credentials.json` - Contains Google service account keys
- `*.log` - May contain sensitive data

**Recommended .gitignore:**
```
config.json
credentials.json
*.log
__pycache__/
*.py[cod]
.venv/
```

### SimpleFin Security

🔐 **Token & Access URL:**
- **Token**: Base64-encoded claim URL (one-time use)
  - Can only be claimed ONCE to get access URL
  - Delete from config after first successful run
  - Create at: https://beta-bridge.simplefin.org/my-account/tokens/create
  
- **Access URL**: Permanent credentials
  - Format: `https://username:password@bridge.simplefin.org/simplefin`
  - Contains authentication in URL
  - Automatically saved to config.json
  - If compromised, revoke and create new token

**Token Lifecycle:**
1. Create token → Get base64 token
2. Script decodes → Gets claim URL
3. Script claims → Gets access URL
4. Access URL saved → Token no longer needed
5. Subsequent runs use saved access URL

### Google Cloud Security

🔑 **Service Account:**
- Grant Editor permission only to specific spreadsheet
- Rotate credentials periodically
- Monitor usage in Google Cloud Console
- Keys don't expire but should be rotated annually

### Data Privacy

🔒 **What's Stored:**
- **SimpleFin**: Account connections, transactions, balances
- **Google Sheets**: Account data, last 60 days transactions
- **Local**: config.json (access URL), credentials.json, logs
- **NOT Stored**: Bank passwords, credit card numbers

👥 **Access Control:**
- SimpleFin access URL = read-only access to financial data
- Google service account = full edit access to spreadsheet
- Be careful who you share Google Sheet with

## Logging

- [SimpleFin Protocol](https://www.simplefin.org/protocol.html)
- [Google Sheets API](https://developers.google.com/sheets/api)

## License

This script is provided as-is for personal use.

## Support

For issues or questions:
1. Check the log file: `simplefin_sync.log`
2. Verify configuration settings
3. Test API access separately

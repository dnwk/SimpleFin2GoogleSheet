# SimpleFin to Google Sheets Integration

**Automatically sync all your bank accounts into one Google Sheet**

Connect your banks through SimpleFin Bridge and this script will automatically pull account balances and transactions into a Google Sheet - no manual data entry required.

## What This Does

- 🏦 Aggregates **all your bank accounts** into one Google Sheet
- 💰 Updates **current balances** automatically
- 📊 Pulls **transactions** for each account (configurable: 1-180 days, default 60)
- 🔄 Detects **new accounts** automatically
- ✅ Lets you **choose which accounts to sync** (ignore unwanted ones)
- 🔗 Creates **clickable navigation** between accounts
- ⏰ Converts dates to readable format (no Unix timestamps)

## Key Features

### Multi-Bank Support
- Connect unlimited banks and credit cards through SimpleFin
- Supports checking, savings, credit cards, investments, loans
- Automatic discovery when you add new accounts

### Smart Organization
- **Index Sheet**: Dashboard with all accounts, balances, and last updated times
- **Account Sheets**: Individual sheet per account with transactions
- **Navigation Links**: Click account names to view details, "Back to Index" on each sheet
- **Ignore Control**: Toggle sync on/off for any account

### Reliable Automation
- Auto-retries on timeouts (up to 3 attempts)
- Handles API rate limits gracefully
- Logs all activity for troubleshooting
- Preserves your settings between runs

## How It Works

```
Your Banks → SimpleFin Bridge → This Script → Your Google Sheet
```

1. You connect your banks to SimpleFin (one-time setup)
2. SimpleFin securely fetches your account data
3. This script pulls data from SimpleFin API
4. Data syncs to your Google Sheet on your schedule

**First Run**: Creates Index sheet, lists all accounts, exits for review
**Subsequent Runs**: Syncs data for non-ignored accounts
**When New Account Added**: Detects it, adds to Index, exits for review

## Setup

### Prerequisites

- **SimpleFin Account** - Sign up at https://www.simplefin.org/
- **Google Account** - For Google Sheets
- **Python 3.x** - Installed on your computer

### Step 1: Connect Your Banks to SimpleFin

1. **Sign up for SimpleFin**
   - Go to https://www.simplefin.org/ and create an account
   - SimpleFin costs around $1.50/month (pay-as-you-go pricing)

2. **Add Your Financial Institutions**
   - Log into SimpleFin at https://beta-bridge.simplefin.org/
   - Click **"Setup" → "Add Institution"**
   - Search for your bank/credit card by name
   - Click on your institution from the search results
   - Enter your online banking username and password
   - Complete any 2FA/security questions if prompted
   - SimpleFin will verify the connection

3. **Repeat for All Your Accounts**
   - Add each bank, credit card, investment account you want to track
   - You can add unlimited institutions
   - Each institution connection is separate

4. **Verify Accounts Appear**
   - Click **"Accounts"** in SimpleFin dashboard
   - You should see all your connected accounts with current balances
   - May take a few minutes for initial sync

**Troubleshooting SimpleFin Connections:**
- If login fails: Verify your bank credentials are correct
- If 2FA required: Complete the verification in SimpleFin interface
- If account not syncing: Check SimpleFin status page or contact support
- Some banks require periodic re-authentication (SimpleFin will notify you)

### Step 2: Create SimpleFin API Token

1. Go to https://beta-bridge.simplefin.org/my-account/tokens/create
2. Click **"Create Setup Token"**
3. Copy the base64-encoded token (long string of characters)
4. Save this token - you'll need it for configuration

⚠️ **Important**: Each token can only be claimed ONCE. The script will automatically convert it to a permanent access URL and save it.

### Step 3: Set Up Google Sheets

1. **Enable Google Sheets API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing one
   - Go to **"APIs & Services" → "Library"**
   - Search for "Google Sheets API" and click **"Enable"**

2. **Create Service Account**
   - Go to **"APIs & Services" → "Credentials"**
   - Click **"Create Credentials" → "Service Account"**
   - Enter a name (e.g., "SimpleFin Sync")
   - Click **"Create and Continue"** → **"Done"**
   - Click on the created service account
   - Go to **"Keys"** tab → **"Add Key" → "Create New Key"**
   - Choose **JSON** format and download
   - Save as `credentials.json` in the script directory

3. **Create and Share Google Sheet**
   - Create a new Google Sheet (or use existing one)
   - Copy the Spreadsheet ID from URL:  
     `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - Click **"Share"** button
   - Add the service account email (found in `credentials.json` as `client_email`)
   - Grant **"Editor"** permission
   - Click **"Send"**

### Step 4: Install Script

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create configuration file**
   ```bash
   cp config.json.example config.json
   ```

3. **Edit config.json**
   ```json
   {
     "simplefin_token": "paste-your-base64-token-here",
     "google_credentials_file": "credentials.json",
     "spreadsheet_id": "paste-your-spreadsheet-id-here",
     "transaction_days": 60
   }
   ```

   **Configuration Options:**
   - `simplefin_token`: Your SimpleFin setup token (base64-encoded)
   - `google_credentials_file`: Path to your Google service account JSON file
   - `spreadsheet_id`: Your Google Spreadsheet ID from the URL
   - `transaction_days`: (Optional) Number of days of transactions to fetch
     - Default: 60 days
     - Range: 1-180 days
     - Higher values = more data but slower syncs

## Usage

### Initial Setup

1. **Run the script first time**
   ```bash
   python simplefin_to_sheets.py
   ```

2. **What happens:**
   - Creates Index sheet with all your accounts
   - Exits automatically (this is normal!)

3. **Review your accounts**
   - Open your Google Sheet
   - Check the Index sheet
   - For accounts you don't want to sync, change **"Ignore"** column to `true`

4. **Run again to sync data**
   ```bash
   python simplefin_to_sheets.py
   ```
   - Now it will create sheets and sync transactions

### Regular Syncing

**Run anytime to update:**
```bash
python simplefin_to_sheets.py
```

**What it does:**
- Checks for new accounts in SimpleFin (if found, adds to Index and exits)
- Syncs all non-ignored accounts (fetches transactions, updates balances)
- Updates Index with latest sync timestamps

### Managing Accounts

**To stop syncing an account:**
- Open Index sheet
- Find the account
- Change "Ignore" from `false` to `true`

**When you add a new bank in SimpleFin:**
- Run the script
- It will detect the new account, add to Index, and exit
- Review the Index, then run again to sync

### Scheduling Automatic Updates

**Using cron (Linux/Mac):**
1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add a line to run daily at 8:00 AM:
   ```bash
   0 8 * * * cd /path/to/script/directory && python simplefin_to_sheets.py >> /path/to/script/directory/cron.log 2>&1
   ```

3. Save and exit

**Cron schedule examples:**
- Daily at 8 AM: `0 8 * * *`
- Every Monday at 9 AM: `0 9 * * 1`
- Twice daily (8 AM and 8 PM): `0 8,20 * * *`

**Recommended frequency**: Daily or weekly (avoid more than once per hour)

## What You Get

### Index Sheet
- Lists all accounts with clickable names
- Shows current balance for each account
- "Ignore" column to control syncing
- "Last Updated" timestamp
- Green header row (frozen for scrolling)

### Account Sheets (one per account)
- Account name, ID, balance
- Last 60 days of transactions
- Columns: Date, Description, Amount, Transaction ID, Pending status
- Sorted newest first
- "Back to Index" link at bottom

## Troubleshooting

### Script Exits Immediately

**This is normal when:**
- First run (creating Index)
- New accounts detected (added to Index)

**Solution**: Review Index sheet and run again

### Authentication Errors

**SimpleFin HTTP 403:**
- Token already claimed → Create new token
- Access URL revoked → Create new token and remove old `simplefin_access_url` from config

**Google Sheets errors:**
- Service account not shared with sheet → Share sheet with service account email
- Wrong spreadsheet ID → Verify ID from sheet URL

### SimpleFin Timeout

Script will automatically retry 3 times. If persistent, SimpleFin may be experiencing issues.

### Google Sheets Rate Limit

Script has built-in delays. If you see quota errors, reduce sync frequency.

### Missing Transactions

- Check if account is active in SimpleFin dashboard
- Verify bank connection is still valid (may need re-authentication)
- Account may have no activity in last 60 days

### New Account Not Detected

- Wait a few minutes for SimpleFin to fully sync
- Verify account appears in SimpleFin dashboard
- Run script again

## Important Notes

### Security

**Keep these files secure:**
- `config.json` - Contains SimpleFin access credentials
- `credentials.json` - Contains Google service account key
- Add to `.gitignore` if using version control

**Data flow:**
- Banks → SimpleFin (encrypted)
- SimpleFin → Script (HTTPS API)
- Script → Your Google Sheet (HTTPS API)
- Your bank passwords stay with SimpleFin only

### Script Behavior

- **First run**: Populates Index → exits
- **New accounts found**: Adds to Index → exits
- **Normal run**: Syncs all non-ignored accounts

Always review Index sheet after it exits!

### Data

- Transaction amounts are strings (not numbers) from SimpleFin
- Dates use `EPOCHTODATE()` formula (display in your timezone)
- Balance shown as-is from SimpleFin
- Transactions limited to last 60 days
- Ignore flags persist between runs

### Performance

- Processes one account at a time (~2-3 seconds each)
- Built-in rate limiting for Google Sheets API
- Automatic retries on timeouts
- Check logs in `simplefin_sync.log` for details

## Support

**Check logs first:** `simplefin_sync.log` in script directory

**Common resources:**
- SimpleFin documentation: https://www.simplefin.org/protocol.html
- Google Sheets API: https://developers.google.com/sheets/api
- SimpleFin support: Contact through beta-bridge.simplefin.org

## License

Provided as-is for personal use.

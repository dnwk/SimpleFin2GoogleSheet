#!/usr/bin/env python3
"""
SimpleFin to Google Sheets Integration

This script fetches account information and transactions from SimpleFin API
and syncs them to Google Sheets. Each account gets its own sheet with
account details and last 60 days of transactions.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import base64
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'simplefin_sync.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def retry_on_rate_limit(max_retries=5, initial_delay=10):
    """
    Decorator to retry API calls on rate limit errors with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (will be doubled for each retry)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    # Check if it's a rate limit error (429)
                    if e.resp.status == 429:
                        if attempt < max_retries - 1:
                            logger.warning(f"Rate limit hit, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"Rate limit exceeded after {max_retries} retries")
                            raise
                    else:
                        # Not a rate limit error, raise immediately
                        raise
            return None
        return wrapper
    return decorator


class SimplefinClient:
    """Client for interacting with SimpleFin API"""
    
    def __init__(self, access_url: str):
        """
        Initialize SimpleFin client
        
        Args:
            access_url: SimpleFin access URL (contains credentials)
        """
        self.access_url = access_url
        self.base_url = self._parse_base_url(access_url)
        self.auth_header = self._create_auth_header(access_url)
    
    @staticmethod
    def claim_token(token: str) -> str:
        """
        Claim a SimpleFin token to get access URL
        
        Process:
        1. Base64 decode the token to get the claim URL
        2. POST to the claim URL to get the access URL
        
        Args:
            token: Base64-encoded SimpleFin token
            
        Returns:
            SimpleFin access URL (format: https://user:pass@bridge.simplefin.org/simplefin)
        """
        try:
            # Step 1: Base64 decode the token to get claim URL
            logger.info("Decoding SimpleFin token to get claim URL")
            decoded_bytes = base64.b64decode(token)
            claim_url = decoded_bytes.decode('utf-8')
            logger.info(f"Claim URL obtained")
            
            # Step 2: POST to claim URL to get access URL
            logger.info("Claiming SimpleFin token (POST to claim URL)")
            headers = {'Content-Length': '0'}
            response = requests.post(claim_url, headers=headers, timeout=30)
            
            # Handle HTTP 403 - token already claimed or invalid
            if response.status_code == 403:
                logger.error("HTTP 403 Forbidden: SimpleFin token has already been claimed or is invalid")
                raise ValueError(
                    "SimpleFin token is invalid or already claimed. "
                    "Each token can only be claimed once. "
                    "Please create a new token at https://beta-bridge.simplefin.org/my-account/tokens/create"
                )
            
            response.raise_for_status()
            
            access_url = response.text.strip()
            logger.info("Successfully claimed SimpleFin token and obtained access URL")
            return access_url
            
        except base64.binascii.Error as e:
            logger.error(f"Error decoding SimpleFin token (invalid base64): {e}")
            raise ValueError(f"Invalid SimpleFin token format - must be valid base64: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error claiming SimpleFin token via POST request: {e}")
            raise ValueError(f"Failed to claim SimpleFin token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error claiming SimpleFin token: {e}")
            raise
        
    def _parse_base_url(self, access_url: str) -> str:
        """Extract base URL from access URL"""
        # Access URL format: https://username:password@bridge.simplefin.org/simplefin
        if '@' in access_url:
            protocol, rest = access_url.split('//', 1)
            if '@' in rest:
                _, domain_path = rest.split('@', 1)
                return f"{protocol}//{domain_path}"
        return access_url
    
    def _create_auth_header(self, access_url: str) -> str:
        """Create Basic Auth header from access URL"""
        if '@' in access_url:
            protocol, rest = access_url.split('//', 1)
            if '@' in rest:
                credentials, _ = rest.split('@', 1)
                auth_bytes = credentials.encode('utf-8')
                auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
                return f"Basic {auth_b64}"
        return ""
    
    def get_accounts_with_transactions(self, start_date: datetime, end_date: Optional[datetime] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Fetch all accounts and transactions within date range with retry logic
        
        Args:
            start_date: Start date for transactions
            end_date: End date for transactions (defaults to now)
            max_retries: Maximum number of retry attempts for timeout/connection errors
            
        Returns:
            Dictionary containing accounts with their information and transactions
        """
        if end_date is None:
            end_date = datetime.now()
        
        # SimpleFin uses Unix timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        url = f"{self.base_url}/accounts"
        params = {
            'start-date': start_timestamp,
            'end-date': end_timestamp
        }
        headers = {'Authorization': self.auth_header} if self.auth_header else {}
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching accounts and transactions from {start_date.date()} to {end_date.date()} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Handle HTTP 403 - access URL is invalid or revoked
                if response.status_code == 403:
                    logger.error("HTTP 403 Forbidden: SimpleFin access URL is invalid or has been revoked")
                    raise ValueError(
                        "SimpleFin access URL is invalid or has been revoked. "
                        "Please create a new token at https://beta-bridge.simplefin.org/my-account/tokens/create "
                        "and update your config.json with the new token. "
                        "Remove the old 'simplefin_access_url' from config to claim the new token."
                    )
                
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successfully fetched {len(data.get('accounts', []))} accounts with transactions")
                return data
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"SimpleFin API timeout/connection error: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error fetching accounts from SimpleFin after {max_retries} attempts: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching accounts from SimpleFin: {e}")
                raise
        
        # Should never reach here due to raise statements, but satisfy type checker
        return {'accounts': []}
    



class GoogleSheetsClient:
    """Client for interacting with Google Sheets API"""
    
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        Initialize Google Sheets client
        
        Args:
            credentials_file: Path to Google service account credentials JSON
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.service = self._authenticate(credentials_file)
    
    @staticmethod
    def sanitize_string(value: str, strip_unicode: bool = True) -> str:
        """
        Sanitize string for safe writing to Google Sheets
        - Prevents formula injection by escaping leading special characters
        - Removes null bytes and other problematic characters
        - By default strips non-ASCII Unicode characters (for account names)
        
        Args:
            value: String to sanitize
            strip_unicode: If True (default), remove non-ASCII characters
            
        Returns:
            Sanitized string safe for Google Sheets
        """
        if not isinstance(value, str):
            return value
        
        # Remove null bytes and other control characters (except newlines/tabs)
        value = ''.join(char for char in value if char == '\n' or char == '\t' or ord(char) >= 32)
        
        # Strip non-ASCII Unicode characters if requested (for account names)
        if strip_unicode:
            value = ''.join(char if ord(char) < 128 else '' for char in value)
            # Clean up any extra spaces created by Unicode removal
            value = ' '.join(value.split())
        
        # Prevent formula injection - escape leading special characters
        # Google Sheets formulas start with: = + - @ 
        if value and value[0] in ('=', '+', '-', '@'):
            value = "'" + value  # Prefix with single quote to treat as text
        
        return value
        
    def _authenticate(self, credentials_file: str):
        """Authenticate with Google Sheets API"""
        try:
            # Convert to absolute path relative to script directory if not absolute
            if not os.path.isabs(credentials_file):
                credentials_file = os.path.join(SCRIPT_DIR, credentials_file)
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)
            logger.info("Successfully authenticated with Google Sheets API")
            return service
        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {e}")
            raise
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def get_all_sheets(self) -> List[Dict[str, Any]]:
        """Get all sheets in the spreadsheet"""
        try:
            time.sleep(1)  # Throttle to stay under 60 req/min
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return spreadsheet.get('sheets', [])
        except HttpError as e:
            logger.error(f"Error getting sheets: {e}")
            raise
    
    def get_sheet_gid(self, sheet_name: str) -> Optional[int]:
        """Get the GID (sheet ID) for a sheet by name"""
        try:
            sheets = self.get_all_sheets()
            for sheet in sheets:
                if sheet.get('properties', {}).get('title') == sheet_name:
                    return sheet.get('properties', {}).get('sheetId')
            return None
        except Exception as e:
            logger.warning(f"Error getting sheet GID for '{sheet_name}': {e}")
            return None
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def find_sheet_by_account_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Find sheet by account ID stored in the sheet
        
        Args:
            account_id: SimpleFin account ID to search for
            
        Returns:
            Sheet properties if found, None otherwise
        """
        try:
            sheets = self.get_all_sheets()
            
            for sheet in sheets:
                sheet_props = sheet.get('properties', {})
                sheet_id = sheet_props.get('sheetId')
                sheet_name = sheet_props.get('title')
                
                # Check if sheet is hidden
                if sheet_props.get('hidden', False):
                    logger.info(f"Sheet '{sheet_name}' is hidden, skipping")
                    continue
                
                # Read account ID from cell A2
                try:
                    time.sleep(1)  # Throttle to stay under 60 req/min
                    range_name = f"'{sheet_name}'!A2"
                    result = self.service.spreadsheets().values().get(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name
                    ).execute()
                    
                    values = result.get('values', [])
                    if values and len(values[0]) > 0:
                        stored_account_id = values[0][0]
                        if stored_account_id == account_id:
                            logger.info(f"Found existing sheet for account {account_id}: {sheet_name}")
                            return sheet_props
                except HttpError:
                    # Sheet might be empty or not readable
                    continue
            
            return None
            
        except HttpError as e:
            logger.error(f"Error searching for sheet: {e}")
            raise
    
    def find_unique_sheet_name(self, base_name: str, account_id: str) -> str:
        """
        Find a unique sheet name by checking existing sheets.
        If base_name exists but has different account ID, append number.
        
        Args:
            base_name: Desired sheet name
            account_id: Account ID to check for conflicts
            
        Returns:
            Unique sheet name
        """
        try:
            sheets = self.get_all_sheets()
            existing_names = {}
            
            # Build map of sheet names to their account IDs
            for sheet in sheets:
                sheet_name = sheet.get('properties', {}).get('title', '')
                if not sheet_name:
                    continue
                    
                # Try to read account ID from this sheet
                try:
                    time.sleep(1)  # Throttle to stay under 60 req/min
                    range_name = f"'{sheet_name}'!A2"
                    result = self.service.spreadsheets().values().get(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name
                    ).execute()
                    
                    values = result.get('values', [])
                    if values and len(values[0]) > 0:
                        existing_names[sheet_name] = values[0][0]
                    else:
                        existing_names[sheet_name] = None
                except HttpError:
                    existing_names[sheet_name] = None
            
            # If base_name doesn't exist, use it
            if base_name not in existing_names:
                return base_name
            
            # If base_name exists with same account ID, we'll update it
            if existing_names[base_name] == account_id:
                return base_name
            
            # base_name exists with different account ID, find unique name
            counter = 2
            while True:
                new_name = f"{base_name} {counter}"
                if new_name not in existing_names:
                    logger.info(f"Sheet '{base_name}' exists with different account, using '{new_name}'")
                    return new_name
                # If it exists with same account ID, use it
                if existing_names.get(new_name) == account_id:
                    return new_name
                counter += 1
                
        except Exception as e:
            logger.warning(f"Error finding unique sheet name, using base name: {e}")
            return base_name
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def create_sheet(self, sheet_name: str) -> int:
        """
        Create a new sheet
        
        Args:
            sheet_name: Name for the new sheet
            
        Returns:
            Sheet ID of the created sheet
        """
        try:
            time.sleep(1.5)  # Throttle write operations more
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()
            
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            logger.info(f"Created new sheet: {sheet_name} (ID: {sheet_id})")
            return sheet_id
            
        except HttpError as e:
            logger.error(f"Error creating sheet: {e}")
            raise
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def update_sheet_data(self, sheet_name: str, data: List[List[Any]]):
        """
        Update sheet with data (overwrites existing content)
        
        Args:
            sheet_name: Name of the sheet to update
            data: 2D list of values to write
        """
        try:
            time.sleep(1.5)  # Throttle write operations more
            range_name = f"'{sheet_name}'!A1"
            
            # Clear existing content first
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!A:Z"
            ).execute()
            
            time.sleep(1)  # Delay between clear and update
            
            # Write new data
            body = {
                'values': data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Allow formulas to be processed
                body=body
            ).execute()
            
            logger.info(f"Updated sheet '{sheet_name}' with {len(data)} rows")
            
        except HttpError as e:
            logger.error(f"Error updating sheet data: {e}")
            raise
    
    @retry_on_rate_limit(max_retries=5, initial_delay=2)
    def format_sheet_header(self, sheet_name: str):
        """Format the header row with bold text and background color"""
        try:
            time.sleep(1)  # Rate limiting before format operation
            sheets = self.get_all_sheets()
            sheet_id = None
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,  # Row 3 (0-indexed), where transaction headers are
                        'endRowIndex': 3,
                        'startColumnIndex': 0,
                        'endColumnIndex': 10
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Error formatting sheet: {e}")
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def set_column_width(self, sheet_name: str, column_index: int, width_pixels: int):
        """Set the width of a specific column"""
        try:
            time.sleep(1)  # Throttle to stay under 60 req/min
            sheets = self.get_all_sheets()
            sheet_id = None
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [{
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': column_index,
                        'endIndex': column_index + 1
                    },
                    'properties': {
                        'pixelSize': width_pixels
                    },
                    'fields': 'pixelSize'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Error setting column width: {e}")
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def hide_sheet(self, sheet_name: str):
        """Hide a sheet"""
        try:
            time.sleep(1)  # Throttle to stay under 60 req/min
            sheets = self.get_all_sheets()
            sheet_id = None
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [{
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'hidden': True
                    },
                    'fields': 'hidden'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Error hiding sheet: {e}")
    
    @retry_on_rate_limit(max_retries=5, initial_delay=10)
    def unhide_sheet(self, sheet_name: str):
        """Unhide a sheet"""
        try:
            time.sleep(1)  # Throttle to stay under 60 req/min
            sheets = self.get_all_sheets()
            sheet_id = None
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [{
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'hidden': False
                    },
                    'fields': 'hidden'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Error unhiding sheet: {e}")


class SimplefinToSheetsSync:
    """Main synchronization class"""
    
    def __init__(self, config_file: str):
        """
        Initialize sync service
        
        Args:
            config_file: Path to configuration JSON file
        """
        self.config = self._load_config(config_file)
        # Store the absolute path to config file for later use (e.g., saving access URL)
        if not os.path.isabs(config_file):
            self.config_file = os.path.join(SCRIPT_DIR, config_file)
        else:
            self.config_file = config_file
        
        # Get access URL from token or use cached access URL
        access_url = self._get_access_url()
        
        self.simplefin = SimplefinClient(access_url)
        self.sheets = GoogleSheetsClient(
            self.config['google_credentials_file'],
            self.config['spreadsheet_id']
        )
    
    @staticmethod
    def _parse_simplefin_errors(accounts_data: Dict[str, Any]) -> List[str]:
        """
        Parse errors from SimpleFin API response to extract organization names
        that need attention.
        
        Args:
            accounts_data: Response from SimpleFin API
            
        Returns:
            List of organization names that have connection errors
        """
        error_orgs = []
        errors = accounts_data.get('errors', [])
        
        if not errors:
            return error_orgs
        
        logger.info(f"Found {len(errors)} error(s) in SimpleFin response")
        
        for error_msg in errors:
            if not isinstance(error_msg, str):
                continue
            
            # Parse: "Connection to [ORG NAME] may need attention..."
            if 'Connection to' in error_msg and 'may need attention' in error_msg:
                try:
                    # Extract text between "Connection to" and "may need attention"
                    start = error_msg.index('Connection to') + len('Connection to')
                    end = error_msg.index('may need attention')
                    org_name = error_msg[start:end].strip()
                    
                    if org_name:
                        error_orgs.append(org_name)
                        logger.warning(f"Connection error detected for: {org_name}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse error message: {error_msg}")
        
        return error_orgs
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            # Convert to absolute path relative to script directory
            if not os.path.isabs(config_file):
                config_file = os.path.join(SCRIPT_DIR, config_file)
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            required_keys = ['google_credentials_file', 'spreadsheet_id']
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"Missing required configuration key: {key}")
            
            # Convert google_credentials_file to absolute path relative to script directory
            if 'google_credentials_file' in config and not os.path.isabs(config['google_credentials_file']):
                config['google_credentials_file'] = os.path.join(SCRIPT_DIR, config['google_credentials_file'])
            
            # Must have either simplefin_token or simplefin_access_url
            if 'simplefin_token' not in config and 'simplefin_access_url' not in config:
                raise ValueError("Configuration must contain either 'simplefin_token' or 'simplefin_access_url'")
            
            # Validate transaction_days (optional, default to 60, max 180)
            transaction_days = config.get('transaction_days', 60)
            if not isinstance(transaction_days, int) or transaction_days < 1:
                logger.warning(f"Invalid transaction_days value: {transaction_days}. Using default: 60")
                config['transaction_days'] = 60
            elif transaction_days > 180:
                logger.warning(f"transaction_days ({transaction_days}) exceeds maximum of 180 days. Using 180.")
                config['transaction_days'] = 180
            else:
                config['transaction_days'] = transaction_days
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _get_access_url(self) -> str:
        """
        Get SimpleFin access URL - either from cached value or by claiming token
        
        Returns:
            SimpleFin access URL
        """
        # If we already have a cached access URL, use it
        if 'simplefin_access_url' in self.config and self.config['simplefin_access_url']:
            logger.info("Using cached SimpleFin access URL from configuration")
            return self.config['simplefin_access_url']
        
        # Otherwise, claim the token to get access URL
        if 'simplefin_token' in self.config and self.config['simplefin_token']:
            logger.info("Claiming SimpleFin token to obtain access URL")
            access_url = SimplefinClient.claim_token(self.config['simplefin_token'])
            
            # Always save the access URL to config for future use
            self._save_access_url(access_url)
            
            return access_url
        
        raise ValueError("No valid SimpleFin token or access URL found in configuration")
    
    def _save_access_url(self, access_url: str):
        """
        Save claimed access URL to config file for future use
        This is always done to prevent losing the access URL since tokens can only be claimed once.
        
        Args:
            access_url: SimpleFin access URL to save
        """
        try:
            self.config['simplefin_access_url'] = access_url
            
            # self.config_file is already an absolute path
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info("Saved SimpleFin access URL to configuration file for future use")
            logger.info("Tip: You can now remove 'simplefin_token' from config if desired")
            
        except Exception as e:
            logger.warning(f"Could not save access URL to config file: {e}")
            logger.info("Access URL will need to be claimed again on next run")
    
    def _get_index_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Read the Index sheet to get existing account mappings and ignore flags
        
        Returns:
            Dictionary mapping account_id to {account_name, sheet_name, balance, ignore, last_updated}
        """
        try:
            index_map = {}
            
            # Try to read Index sheet
            try:
                time.sleep(1)  # Throttle to stay under 60 req/min
                result = self.sheets.service.spreadsheets().values().get(
                    spreadsheetId=self.sheets.spreadsheet_id,
                    range="'Index'!A2:I1000"  # Read all data rows including Sheet GID
                ).execute()
                
                values = result.get('values', [])
                for row in values:
                    if len(row) >= 2:  # At least account name and ID
                        account_name = row[0]  # Column A
                        account_id = row[1]    # Column B
                        balance = row[2] if len(row) > 2 else ''
                        sheet_name = row[3] if len(row) > 3 else ''
                        sheet_gid_str = row[4] if len(row) > 4 else ''
                        # Convert sheet_gid to int if present
                        try:
                            sheet_gid = int(sheet_gid_str) if sheet_gid_str else None
                        except (ValueError, TypeError):
                            sheet_gid = None
                        org_name = row[5] if len(row) > 5 else ''
                        # Default to false if not specified or invalid
                        ignore_str = row[6].strip().lower() if len(row) > 6 and row[6] else 'false'
                        ignore = ignore_str == 'true'
                        # Connection status in column H (index 7)
                        connection_status = row[7] if len(row) > 7 else ''
                        last_updated = row[8] if len(row) > 8 else ''
                        
                        index_map[account_id] = {
                            'account_name': account_name,
                            'sheet_name': sheet_name,
                            'sheet_gid': sheet_gid,
                            'balance': balance,
                            'ignore': ignore,
                            'org_name': org_name,
                            'last_updated': last_updated
                        }
                
                logger.info(f"Loaded {len(index_map)} accounts from Index sheet")
                
            except HttpError as e:
                if e.resp.status == 400:
                    logger.info("Index sheet does not exist yet")
                else:
                    raise
            
            return index_map
            
        except Exception as e:
            logger.warning(f"Error reading Index sheet: {e}")
            return {}
    
    def _is_index_empty(self) -> bool:
        """
        Check if Index sheet is empty (only has header or no data)
        
        Returns:
            True if Index is empty/new, False if it contains data
        """
        try:
            time.sleep(1)  # Throttle to stay under 60 req/min
            result = self.sheets.service.spreadsheets().values().get(
                spreadsheetId=self.sheets.spreadsheet_id,
                range="'Index'!A2:B2"  # Check if there's any data in row 2
            ).execute()
            
            values = result.get('values', [])
            is_empty = len(values) == 0 or len(values[0]) < 2
            
            if is_empty:
                logger.info("Index sheet is empty (new/no data)")
            else:
                logger.info("Index sheet contains existing data")
            
            return is_empty
            
        except HttpError as e:
            logger.warning(f"Error checking if Index is empty: {e}")
            return True  # Assume empty if error
    
    def _clear_all_sheets_except_index(self):
        """
        Delete all sheets except the Index sheet
        """
        try:
            logger.info("Clearing all existing sheets except Index")
            sheets = self.sheets.get_all_sheets()
            
            sheets_to_delete = []
            for sheet in sheets:
                sheet_name = sheet.get('properties', {}).get('title', '')
                sheet_id = sheet.get('properties', {}).get('sheetId')
                
                if sheet_name != 'Index' and sheet_id is not None:
                    sheets_to_delete.append(sheet_id)
            
            if sheets_to_delete:
                logger.info(f"Deleting {len(sheets_to_delete)} existing sheets")
                
                # Delete in batches to avoid rate limits
                for sheet_id in sheets_to_delete:
                    try:
                        time.sleep(1.5)  # Throttle delete operations
                        requests = [{
                            'deleteSheet': {
                                'sheetId': sheet_id
                            }
                        }]
                        
                        body = {'requests': requests}
                        self.sheets.service.spreadsheets().batchUpdate(
                            spreadsheetId=self.sheets.spreadsheet_id,
                            body=body
                        ).execute()
                    except HttpError as e:
                        logger.warning(f"Could not delete sheet {sheet_id}: {e}")
                
                logger.info("Cleared all existing sheets")
            else:
                logger.info("No sheets to delete")
                
        except Exception as e:
            logger.error(f"Error clearing sheets: {e}")
            raise
    
    def _initial_setup(self):
        """
        Initial setup when Index is empty:
        1. Clear all sheets except Index
        2. Fetch all accounts from SimpleFin
        3. Populate Index with all accounts
        4. Exit
        """
        try:
            logger.info("=" * 60)
            logger.info("INITIAL SETUP MODE")
            logger.info("=" * 60)
            
            # Step 1: Clear all existing sheets except Index
            self._clear_all_sheets_except_index()
            
            # Step 2: Fetch all accounts from SimpleFin
            logger.info("Fetching all accounts from SimpleFin for initial setup")
            # Use a wide date range to get all accounts with minimal transaction data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)  # Just need 1 day for account info
            accounts_list = self.simplefin.get_accounts_with_transactions(start_date, end_date)
            all_accounts = accounts_list.get('accounts', [])
            
            if not all_accounts:
                logger.warning("No accounts found in SimpleFin")
                return
            
            logger.info(f"Found {len(all_accounts)} accounts in SimpleFin")
            
            # Step 3: Populate Index with all accounts
            accounts_info = []
            for account in all_accounts:
                account_id = account.get('id', '')
                account_name = account.get('name', 'Unknown Account')
                balance = account.get('balance', '')
                org_name = account.get('org', {}).get('name', '')
                
                # Generate sheet name (sanitized account name)
                base_name = account_name.replace('/', '-').replace('\\', '-')[:100]
                
                accounts_info.append({
                    'account_name': account_name,
                    'account_id': account_id,
                    'balance': balance,
                    'sheet_name': base_name,  # Will be finalized when sheets are created
                    'sheet_gid': None,  # Will be set when sheets are created
                    'org_name': org_name,
                    'ignore': False  # Default to false
                })
            
            # Update Index sheet
            logger.info("Populating Index sheet with all accounts")
            self._update_index_sheet(accounts_info, {})
            
            logger.info("=" * 60)
            logger.info("INITIAL SETUP COMPLETE")
            logger.info("=" * 60)
            logger.info("Index sheet has been populated with all accounts.")
            logger.info("Please review the Index sheet and set 'Ignore' to 'true' for accounts you don't want to sync.")
            logger.info("Run the script again to begin syncing account data.")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during initial setup: {e}")
            raise
    
    def _check_and_add_new_accounts(self, existing_index: Dict[str, Dict]) -> bool:
        """
        Check SimpleFin for new accounts not in Index and add them.
        
        Args:
            existing_index: Current index data from _get_index_data()
            
        Returns:
            True if new accounts were added (script should exit), False otherwise
        """
        try:
            logger.info("Checking SimpleFin for new accounts...")
            
            # Fetch all current accounts from SimpleFin
            # Use a wide date range to get all accounts with minimal transaction data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)  # Just need 1 day for account info
            accounts_list = self.simplefin.get_accounts_with_transactions(start_date, end_date)
            all_accounts = accounts_list.get('accounts', [])
            
            if not all_accounts:
                logger.warning("No accounts found in SimpleFin")
                return False
            
            # Find accounts not in existing index
            existing_account_ids = set(existing_index.keys())
            new_accounts = []
            
            for account in all_accounts:
                account_id = account.get('id', '')
                if account_id and account_id not in existing_account_ids:
                    new_accounts.append(account)
            
            if not new_accounts:
                logger.info("No new accounts found")
                return False
            
            logger.info(f"Found {len(new_accounts)} new account(s) in SimpleFin")
            
            # Get existing sheet names to avoid duplicates
            existing_sheets = self.sheets.get_all_sheets()
            existing_sheet_names = {s.get('properties', {}).get('title', '') for s in existing_sheets}
            
            # Prepare new account info
            new_accounts_info = []
            for account in new_accounts:
                account_id = account.get('id', '')
                account_name = account.get('name', 'Unknown Account')
                balance = account.get('balance', '')
                org_name = account.get('org', {}).get('name', '')
                
                # Generate unique sheet name
                base_name = account_name.replace('/', '-').replace('\\', '-')[:100]
                sheet_name = self.sheets.find_unique_sheet_name(base_name, account_id)
                
                logger.info(f"  - New account: {account_name} (ID: {account_id}, Sheet: {sheet_name})")
                
                new_accounts_info.append({
                    'account_name': account_name,
                    'account_id': account_id,
                    'balance': balance,
                    'sheet_name': sheet_name,
                    'sheet_gid': None,  # Will be set when sheet is created
                    'org_name': org_name,
                    'ignore': False  # Default to false for new accounts
                })
            
            # Combine existing and new accounts
            all_accounts_info = []
            
            # Add existing accounts first
            for account_id, info in existing_index.items():
                all_accounts_info.append({
                    'account_name': info.get('account_name', ''),
                    'account_id': account_id,
                    'balance': info.get('balance', ''),
                    'sheet_name': info.get('sheet_name', ''),
                    'sheet_gid': info.get('sheet_gid'),
                    'org_name': info.get('org_name', ''),
                    'ignore': info.get('ignore', False)
                })
            
            # Add new accounts
            all_accounts_info.extend(new_accounts_info)
            
            # Update Index sheet with combined data
            logger.info("Updating Index sheet with new accounts...")
            self._update_index_sheet(all_accounts_info, existing_index)
            
            logger.info("=" * 60)
            logger.info("NEW ACCOUNTS ADDED")
            logger.info("=" * 60)
            logger.info(f"Added {len(new_accounts)} new account(s) to Index sheet.")
            logger.info("Please review the Index sheet and set 'Ignore' to 'true' for accounts you don't want to sync.")
            logger.info("Run the script again to begin syncing account data.")
            logger.info("=" * 60)
            
            return True  # Signal to exit
            
        except Exception as e:
            logger.error(f"Error checking for new accounts: {e}")
            raise
    
    def _ensure_index_sheet_exists(self):
        """
        Ensure Index sheet exists, create if it doesn't
        """
        try:
            sheets = self.sheets.get_all_sheets()
            index_exists = any(s.get('properties', {}).get('title') == 'Index' for s in sheets)
            
            if not index_exists:
                logger.info("Index sheet does not exist, creating it now")
                self.sheets.create_sheet('Index')
                time.sleep(1.5)  # Wait after creation
                
                # Create header row
                header_data = [['Account Name', 'Account ID', 'Balance', 'Sheet Name', 'Sheet GID', 'Org Name', 'Ignore', 'Connection Status', 'Last Updated']]
                self.sheets.update_sheet_data('Index', header_data)
                
                # Format header with green background and white text
                try:
                    time.sleep(1)  # Throttle to stay under 60 req/min
                    sheets = self.sheets.get_all_sheets()
                    sheet_id = None
                    
                    for sheet in sheets:
                        if sheet['properties']['title'] == 'Index':
                            sheet_id = sheet['properties']['sheetId']
                            break
                    
                    if sheet_id is not None:
                        requests = [
                            # Green background with white text
                            {
                                'repeatCell': {
                                    'range': {
                                        'sheetId': sheet_id,
                                        'startRowIndex': 0,
                                        'endRowIndex': 1,
                                        'startColumnIndex': 0,
                                        'endColumnIndex': 9
                                    },
                                    'cell': {
                                        'userEnteredFormat': {
                                            'backgroundColor': {
                                                'red': 0.0,
                                                'green': 0.5,
                                                'blue': 0.0
                                            },
                                            'textFormat': {
                                                'bold': True,
                                                'foregroundColor': {
                                                    'red': 1.0,
                                                    'green': 1.0,
                                                    'blue': 1.0
                                                }
                                            }
                                        }
                                    },
                                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                                }
                            },
                            # Freeze header row
                            {
                                'updateSheetProperties': {
                                    'properties': {
                                        'sheetId': sheet_id,
                                        'gridProperties': {
                                            'frozenRowCount': 1
                                        }
                                    },
                                    'fields': 'gridProperties.frozenRowCount'
                                }
                            }
                        ]
                        
                        body = {'requests': requests}
                        self.sheets.service.spreadsheets().batchUpdate(
                            spreadsheetId=self.sheets.spreadsheet_id,
                            body=body
                        ).execute()
                except Exception as e:
                    logger.warning(f"Could not format Index header: {e}")
                
                logger.info("Created empty Index sheet")
            else:
                logger.info("Index sheet already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring Index sheet exists: {e}")
            raise
    
    def _update_index_sheet(self, accounts_info: List[Dict[str, Any]], existing_index: Dict[str, Dict[str, Any]], error_orgs: Optional[List[str]] = None):
        """
        Update or create the Index sheet with account information
        
        Args:
            accounts_info: List of dicts with account_name, account_id, balance, sheet_name, ignore, org_name, preserve_timestamp (optional)
            existing_index: Existing index data to preserve ignore flags
            error_orgs: List of organization names with connection errors
        """
        try:
            if error_orgs is None:
                error_orgs = []
            # Prepare data with hyperlinks
            data = []
            data.append(['Account Name', 'Account ID', 'Balance', 'Sheet Name', 'Sheet GID', 'Org Name', 'Ignore', 'Connection Status', 'Last Updated'])
            
            for info in accounts_info:
                account_id = info['account_id']
                account_name = info['account_name']
                sheet_name = info['sheet_name']
                
                # Preserve existing ignore flag if account exists in index
                if account_id in existing_index:
                    ignore_flag = existing_index[account_id].get('ignore', False)
                else:
                    # Default to false for new accounts
                    ignore_flag = info.get('ignore', False)
                
                # Create hyperlink formula for account name with actual GID
                if sheet_name:
                    # Use cached GID from account info if available
                    sheet_gid = info.get('sheet_gid')
                    if sheet_gid is None:
                        # Fallback to API call if not cached
                        sheet_gid = self.sheets.get_sheet_gid(sheet_name)
                    
                    if sheet_gid is not None:
                        # Use actual GID for hyperlink - sanitize account name for display
                        sanitized_name = self.sheets.sanitize_string(account_name)
                        account_name_formula = f'=HYPERLINK("#gid={sheet_gid}&range=A1", "{sanitized_name}")'
                    else:
                        # Sheet doesn't exist yet (initial setup), use plain name
                        account_name_formula = self.sheets.sanitize_string(account_name)
                else:
                    sheet_gid = None
                    account_name_formula = self.sheets.sanitize_string(account_name)
                
                # Check if account's org is in error list
                org_name = info.get('org_name', '')
                connection_status = ''
                if org_name and org_name in error_orgs:
                    connection_status = 'Connection broken. Attention required'
                
                # Preserve last update timestamp if account has error
                preserve_timestamp = info.get('preserve_timestamp', False)
                if preserve_timestamp and account_id in existing_index:
                    last_updated = existing_index[account_id].get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                data.append([
                    account_name_formula,
                    account_id,
                    info['balance'],
                    sheet_name,
                    sheet_gid if sheet_gid is not None else '',
                    self.sheets.sanitize_string(org_name),
                    str(ignore_flag).lower(),
                    connection_status,
                    last_updated
                ])
            
            # Update Index sheet
            time.sleep(1.5)  # Throttle write operations
            range_name = "'Index'!A1"
            
            # Clear existing content first
            self.sheets.service.spreadsheets().values().clear(
                spreadsheetId=self.sheets.spreadsheet_id,
                range="'Index'!A:Z"
            ).execute()
            
            time.sleep(1)  # Delay between clear and update
            
            # Write new data with formulas
            body = {
                'values': data
            }
            
            self.sheets.service.spreadsheets().values().update(
                spreadsheetId=self.sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Important: USER_ENTERED processes formulas
                body=body
            ).execute()
            
            # Format header
            self.sheets.format_sheet_header('Index')
            
            # Format Index header with green background and white text
            try:
                time.sleep(1)  # Throttle to stay under 60 req/min
                sheets = self.sheets.get_all_sheets()
                sheet_id = None
                
                for sheet in sheets:
                    if sheet['properties']['title'] == 'Index':
                        sheet_id = sheet['properties']['sheetId']
                        break
                
                if sheet_id is not None:
                    # Count number of accounts for table range
                    num_rows = len(accounts_info) + 1  # +1 for header
                    
                    requests = [
                        # Format header row with green background and white text
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': 0,
                                    'endRowIndex': 1,
                                    'startColumnIndex': 0,
                                    'endColumnIndex': 9
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': {
                                            'red': 0.0,
                                            'green': 0.5,
                                            'blue': 0.0
                                        },
                                        'textFormat': {
                                            'bold': True,
                                            'foregroundColor': {
                                                'red': 1.0,
                                                'green': 1.0,
                                                'blue': 1.0
                                            }
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                            }
                        },
                        # Add borders to create table appearance
                        {
                            'updateBorders': {
                                'range': {
                                    'sheetId': sheet_id,
                                    'startRowIndex': 0,
                                    'endRowIndex': num_rows,
                                    'startColumnIndex': 0,
                                    'endColumnIndex': 9
                                },
                                'top': {'style': 'SOLID', 'width': 1},
                                'bottom': {'style': 'SOLID', 'width': 1},
                                'left': {'style': 'SOLID', 'width': 1},
                                'right': {'style': 'SOLID', 'width': 1},
                                'innerHorizontal': {'style': 'SOLID', 'width': 1},
                                'innerVertical': {'style': 'SOLID', 'width': 1}
                            }
                        },
                        # Freeze header row
                        {
                            'updateSheetProperties': {
                                'properties': {
                                    'sheetId': sheet_id,
                                    'gridProperties': {
                                        'frozenRowCount': 1
                                    }
                                },
                                'fields': 'gridProperties.frozenRowCount'
                            }
                        }
                    ]
                    
                    body = {'requests': requests}
                    self.sheets.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.sheets.spreadsheet_id,
                        body=body
                    ).execute()
            except Exception as e:
                logger.warning(f"Could not format Index header: {e}")
            
            logger.info("Updated Index sheet successfully")
            
        except Exception as e:
            logger.error(f"Error updating Index sheet: {e}")
            raise
    
    def _prepare_account_data(self, account: Dict[str, Any], transactions: List[Dict[str, Any]], transaction_days: int = 60) -> List[List[Any]]:
        """
        Prepare account data for Google Sheets
        
        Args:
            account: Account information from SimpleFin
            transactions: List of transactions for this account
            transaction_days: Number of days of transactions included
            
        Returns:
            2D list formatted for Google Sheets
        """
        data = []
        
        # Account information section
        data.append(['Account Information'])
        data.append(['Account ID:', self.sheets.sanitize_string(account.get('id', ''))])
        data.append(['Account Name:', self.sheets.sanitize_string(account.get('name', ''))])
        data.append(['Currency:', self.sheets.sanitize_string(account.get('currency', 'USD'))])
        data.append(['Balance:', account.get('balance', '')])
        data.append(['Available Balance:', account.get('available-balance', '')])
        data.append(['Balance Date:', account.get('balance-date', '')])
        data.append(['Organization:', self.sheets.sanitize_string(account.get('org', {}).get('name', ''))])
        data.append([])  # Empty row
        
        # Holdings section (if available)
        holdings = account.get('holdings', [])
        if holdings:
            data.append(['Holdings'])
            data.append([])  # Empty row
            
            # Holdings headers
            data.append(['Symbol', 'Description', 'Shares', 'Purchase Price', 'Cost Basis', 'Market Value', 'Created Date', 'Currency', 'Holding ID'])
            
            # Sort holdings by symbol
            sorted_holdings = sorted(
                holdings,
                key=lambda x: x.get('symbol', '')
            )
            
            # Add holdings rows
            for holding in sorted_holdings:
                symbol = self.sheets.sanitize_string(holding.get('symbol', ''))
                description = self.sheets.sanitize_string(holding.get('description', ''))
                shares = holding.get('shares', '')
                purchase_price = holding.get('purchase_price', '')
                cost_basis = holding.get('cost_basis', '')
                market_value = holding.get('market_value', '')
                created = holding.get('created', '')
                currency = self.sheets.sanitize_string(holding.get('currency', 'USD'))
                holding_id = self.sheets.sanitize_string(holding.get('id', ''))
                
                # Convert Unix timestamp to Google Sheets date formula
                if created:
                    created_formula = f'=EPOCHTODATE({created})'
                else:
                    created_formula = ''
                
                data.append([symbol, description, shares, purchase_price, cost_basis, market_value, created_formula, currency, holding_id])
            
            data.append([])  # Empty row after holdings
        
        # Transactions section
        data.append([f'Transactions (Last {transaction_days} Days)'])
        data.append([])  # Empty row
        
        # Transaction headers
        data.append(['Date', 'Description', 'Amount', 'Transaction ID', 'Pending'])
        
        # Sort transactions by date (newest first)
        sorted_transactions = sorted(
            transactions,
            key=lambda x: x.get('posted', 0),
            reverse=True
        )
        
        # Add transaction rows
        for txn in sorted_transactions:
            posted_date = txn.get('posted', '')
            description = self.sheets.sanitize_string(txn.get('description', ''))
            amount = txn.get('amount', '')
            txn_id = self.sheets.sanitize_string(txn.get('id', ''))
            pending = 'Yes' if txn.get('pending', False) else 'No'
            
            # Convert Unix timestamp to Google Sheets date formula
            if posted_date:
                date_formula = f'=EPOCHTODATE({posted_date})'
            else:
                date_formula = ''
            
            data.append([date_formula, description, amount, txn_id, pending])
        
        # Add back link to Index at the bottom with actual Index GID
        data.append([])  # Empty row
        data.append([])  # Another empty row for spacing
        # Placeholder for back link - will be set when writing to sheet
        data.append(['BACK_TO_INDEX_PLACEHOLDER'])
        
        return data
    
    def sync(self):
        """Main synchronization process"""
        try:
            logger.info("Starting SimpleFin to Google Sheets synchronization")
            
            # Step 1: Ensure Index sheet exists
            self._ensure_index_sheet_exists()
            
            # Step 2: Check if Index is empty (initial setup needed)
            if self._is_index_empty():
                logger.info("Index sheet is empty - running initial setup")
                self._initial_setup()
                return  # Exit after initial setup
            
            # Step 3: Read Index sheet to get existing mappings and ignore flags
            logger.info("Reading Index sheet")
            index_data = self._get_index_data()
            
            if not index_data:
                logger.warning("Index sheet exists but contains no valid data")
                return
            
            logger.info(f"Loaded {len(index_data)} accounts from Index")
            
            # Step 4: Check for new accounts in SimpleFin
            new_accounts_added = self._check_and_add_new_accounts(index_data)
            
            if new_accounts_added:
                # New accounts were added, exit to let user review
                return
            
            # Step 5: Determine which accounts need updating
            accounts_to_update = []
            accounts_to_skip = []
            
            for account_id, account_info in index_data.items():
                if account_info.get('ignore', False):
                    accounts_to_skip.append((account_id, account_info))
                else:
                    accounts_to_update.append((account_id, account_info))
            
            logger.info(f"Processing {len(accounts_to_update)} accounts, skipping {len(accounts_to_skip)} ignored accounts")
            
            # Step 5: Fetch ALL accounts and transactions in ONE API call
            transaction_days = self.config.get('transaction_days', 60)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=transaction_days)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[SimpleFin API] Fetching all accounts and transactions in one call")
            logger.info(f"[SimpleFin API] Transaction range: {transaction_days} days")
            logger.info(f"{'='*60}")
            accounts_data = self.simplefin.get_accounts_with_transactions(start_date, end_date)
            
            # Parse errors from SimpleFin response
            error_orgs = self._parse_simplefin_errors(accounts_data)
            
            # Create a map of account_id -> account data for quick lookup
            accounts_map = {}
            for acc in accounts_data.get('accounts', []):
                accounts_map[acc.get('id')] = acc
            
            # Step 6: Process each account for sheet updates
            all_accounts_info = []
            
            for account_id, index_info in accounts_to_update:
                account_name = index_info.get('account_name', 'Unknown Account')
                # Strip Unicode for logging to prevent console encoding errors
                safe_account_name = ''.join(char if ord(char) < 128 else '' for char in account_name)
                safe_account_name = ' '.join(safe_account_name.split())  # Clean up spaces
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing account: {safe_account_name} (ID: {account_id})")
                logger.info(f"{'='*60}")
                
                # Get account data from the map
                account = accounts_map.get(account_id)
                
                if not account:
                    logger.warning(f"Account {account_id} not found in SimpleFin response, skipping")
                    continue
                
                balance = account.get('balance', '')
                org_name = account.get('org', {}).get('name', '')
                
                # Get sheet name from Index
                sheet_name = index_info.get('sheet_name', '')
                
                if not sheet_name:
                    # No sheet name in index, create one
                    base_name = account_name.replace('/', '-').replace('\\', '-')[:100]
                    sheet_name = self.sheets.find_unique_sheet_name(base_name, account_id)
                
                # Check if this account has connection errors
                has_connection_error = org_name and org_name in error_orgs
                
                # Check if sheet exists, create if needed
                sheets = self.sheets.get_all_sheets()
                sheet_exists = any(s.get('properties', {}).get('title') == sheet_name for s in sheets)
                
                if not sheet_exists:
                    logger.info(f"[Google Sheets API] Creating new sheet: {sheet_name}")
                    sheet_gid = self.sheets.create_sheet(sheet_name)
                else:
                    logger.info(f"[Google Sheets API] Sheet exists: {sheet_name}")
                    # Make sure sheet is not hidden
                    self.sheets.unhide_sheet(sheet_name)
                    # Get the GID for this sheet (only one API call needed)
                    sheet_gid = None
                    for s in sheets:
                        if s.get('properties', {}).get('title') == sheet_name:
                            sheet_gid = s.get('properties', {}).get('sheetId')
                            break
                
                # If connection error, add error banner but preserve existing data
                if has_connection_error:
                    logger.warning(f"Connection error detected for {org_name}, adding error banner")
                    
                    # Read existing sheet data (if any)
                    existing_data = []
                    try:
                        time.sleep(1)  # Throttle to stay under 60 req/min
                        result = self.sheets.service.spreadsheets().values().get(
                            spreadsheetId=self.sheets.spreadsheet_id,
                            range=f"'{sheet_name}'!A1:Z1000"
                        ).execute()
                        existing_data = result.get('values', [])
                    except Exception as e:
                        logger.warning(f"Could not read existing data from '{sheet_name}': {e}")
                    
                    # Create error banner to prepend
                    error_banner = [
                        [f'⚠️ CONNECTION ERROR - Last checked: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ⚠️'],
                        [f'Connection to {org_name} may need attention. Please re-authenticate in SimpleFin.'],
                        ['Data below may be outdated until connection is restored.'],
                        [],  # Separator
                    ]
                    
                    # Combine error banner with existing data
                    if existing_data:
                        # Remove old error banner if present (first 4 rows if they contain error message)
                        if existing_data and len(existing_data) > 0:
                            if '⚠️ CONNECTION ERROR' in str(existing_data[0]):
                                # Skip old error banner (4 rows)
                                existing_data = existing_data[4:] if len(existing_data) > 4 else []
                        
                        data = error_banner + existing_data
                    else:
                        # No existing data, create minimal sheet with error
                        data = error_banner + [
                            ['Account Information'],
                            ['Account ID:', self.sheets.sanitize_string(account.get('id', ''))],
                            ['Account Name:', self.sheets.sanitize_string(account.get('name', ''))],
                            [],
                            ['No data available - connection error prevents data retrieval.']
                        ]
                else:
                    # Prepare data normally
                    transactions = account.get('transactions', [])
                    logger.info(f"Preparing data for {len(transactions)} transactions")
                    data = self._prepare_account_data(account, transactions, transaction_days)
                
                # Get Index sheet GID for back link (only for normal data, not error message)
                if not has_connection_error:
                    index_gid = self.sheets.get_sheet_gid('Index')
                    if index_gid is not None:
                        # Replace placeholder with actual hyperlink using Index GID
                        for i, row in enumerate(data):
                            if row and row[0] == 'BACK_TO_INDEX_PLACEHOLDER':
                                data[i] = [f'=HYPERLINK("#gid={index_gid}&range=A1", "← Back to Index")']
                                break
                    else:
                        # Fallback if Index GID not found
                        for i, row in enumerate(data):
                            if row and row[0] == 'BACK_TO_INDEX_PLACEHOLDER':
                                data[i] = ['← Back to Index']
                                break
                
                # Update Google Sheet for this account
                if has_connection_error:
                    logger.info(f"[Google Sheets API] Updating sheet '{sheet_name}' with connection error message")
                else:
                    logger.info(f"[Google Sheets API] Updating sheet '{sheet_name}'")
                self.sheets.update_sheet_data(sheet_name, data)
                
                if not has_connection_error:
                    logger.info(f"[Google Sheets API] Formatting sheet '{sheet_name}'")
                    self.sheets.format_sheet_header(sheet_name)
                    
                    # Set column B width to 400 pixels
                    logger.info(f"[Google Sheets API] Setting column width for '{sheet_name}'")
                    self.sheets.set_column_width(sheet_name, 1, 400)
                    
                    logger.info(f"[SUCCESS] Successfully synced account: {safe_account_name}")
                else:
                    logger.warning(f"[WARNING] Account has connection error: {safe_account_name}")
                
                # Track for Index update
                org_name = account.get('org', {}).get('name', '')
                all_accounts_info.append({
                    'account_name': account_name,
                    'account_id': account_id,
                    'balance': balance,
                    'sheet_name': sheet_name,
                    'sheet_gid': sheet_gid,
                    'org_name': org_name,
                    'preserve_timestamp': has_connection_error,  # Don't update timestamp if error
                    'ignore': False
                })
            
            # Step 7: Process skipped accounts (hide sheets, add to index)
            for account_id, index_info in accounts_to_skip:
                account_name = index_info.get('account_name', 'Unknown Account')
                balance = index_info.get('balance', '')
                sheet_name = index_info.get('sheet_name', '')
                
                # Strip Unicode for logging
                safe_account_name = ''.join(char if ord(char) < 128 else '' for char in account_name)
                safe_account_name = ' '.join(safe_account_name.split())
                
                logger.info(f"Skipping ignored account: {safe_account_name}")
                
                if sheet_name:
                    self.sheets.hide_sheet(sheet_name)
                
                # Get org_name and sheet_gid from index_info
                org_name = index_info.get('org_name', '')
                sheet_gid = index_info.get('sheet_gid')
                all_accounts_info.append({
                    'account_name': account_name,
                    'account_id': account_id,
                    'balance': balance,
                    'sheet_name': sheet_name,
                    'sheet_gid': sheet_gid,
                    'org_name': org_name,
                    'ignore': True
                })
            
            # Step 8: Update Index sheet
            logger.info("\nUpdating Index sheet with latest information")
            self._update_index_sheet(all_accounts_info, index_data, error_orgs)
            
            logger.info("\n" + "="*60)
            logger.info("SYNCHRONIZATION COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            logger.info(f"Updated: {len(accounts_to_update)} accounts")
            logger.info(f"Skipped: {len(accounts_to_skip)} accounts")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
            raise


def main():
    """Main entry point"""
    # Use config.json relative to script directory
    config_file = os.path.join(SCRIPT_DIR, 'config.json')
    
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        logger.info("Please create a config.json file with the required settings")
        return 1
    
    try:
        sync_service = SimplefinToSheetsSync(config_file)
        sync_service.sync()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    exit(exit_code)

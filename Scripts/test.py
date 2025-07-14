import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

class OrganizationEmailsRetriever:
    def __init__(self):
        """Initialize the emails retriever with Graph API configuration"""
        # Load environment variables
        try:
            load_dotenv("Scripts/email.env")
        except:
            pass
        
        # Microsoft Graph API configuration
        self.tenant_id = os.getenv("TENANT_ID", "")
        self.client_id = os.getenv("CLIENT_ID", "")
        self.client_secret = os.getenv("CLIENT_SECRET", "")
        
        # Graph API URLs
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
        
        # Token management
        self.access_token = None
        self.token_expires_at = None
        
        # Validate configuration
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing required environment variables: TENANT_ID, CLIENT_ID, CLIENT_SECRET")
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token from Microsoft Graph API"""
        # Check if we have a valid cached token
        if (self.access_token and self.token_expires_at and 
            datetime.now() < self.token_expires_at):
            return self.access_token
        
        try:
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            response = requests.post(self.token_url, data=token_data, headers=headers)
            
            if response.status_code == 200:
                token_info = response.json()
                self.access_token = token_info.get('access_token')
                expires_in = token_info.get('expires_in', 3600)
                
                # Set expiration with 5-minute buffer
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                print("✅ Access token obtained successfully")
                return self.access_token
            else:
                error_detail = response.json()
                print(f"❌ Token error: {error_detail.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Graph API requests"""
        token = self._get_access_token()
        if not token:
            return {}
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_all_organization_emails(self) -> List[str]:
        """Get all email addresses from the organization"""
        all_emails = []
        
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                print("❌ Failed to get authorization token")
                return []
            
            # Get all users in the organization
            users_url = f"{self.graph_api_url}/users"
            
            # Parameters to get all users with email info
            params = {
                '$select': 'mail,userPrincipalName,displayName,jobTitle,department',
                '$filter': 'accountEnabled eq true',  # Only active users
                '$top': 999  # Max items per request
            }
            
            page_count = 0
            total_users = 0
            
            while users_url and page_count < 50:  # Safety limit
                print(f"📡 Fetching page {page_count + 1}...")
                
                response = requests.get(users_url, headers=headers, params=params if page_count == 0 else None)
                
                if response.status_code == 200:
                    data = response.json()
                    users = data.get('value', [])
                    
                    for user in users:
                        # Get primary email (mail field) or fallback to userPrincipalName
                        email = user.get('mail') or user.get('userPrincipalName')
                        
                        if email and '@' in email:
                            all_emails.append(email)
                            total_users += 1
                    
                    # Check for next page
                    users_url = data.get('@odata.nextLink')
                    params = None  # Clear params for subsequent requests
                    page_count += 1
                    
                    print(f"   ✅ Found {len(users)} users on this page")
                    
                elif response.status_code == 401:
                    print("❌ Unauthorized - token may have expired")
                    # Try to refresh token
                    self.access_token = None
                    headers = self._get_headers()
                    if headers.get('Authorization'):
                        continue  # Retry with new token
                    else:
                        break
                else:
                    print(f"❌ API error: {response.status_code}")
                    break
            
            print(f"✅ Total emails retrieved: {len(all_emails)}")
            return sorted(list(set(all_emails)))  # Remove duplicates and sort
            
        except Exception as e:
            print(f"❌ Error retrieving organization emails: {e}")
            return []
    
    def get_users_with_details(self) -> List[Dict[str, Any]]:
        """Get all users with detailed information"""
        all_users = []
        
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                print("❌ Failed to get authorization token")
                return []
            
            users_url = f"{self.graph_api_url}/users"
            
            params = {
                '$select': 'mail,userPrincipalName,displayName,jobTitle,department,officeLocation,mobilePhone',
                '$filter': 'accountEnabled eq true',
                '$top': 999
            }
            
            page_count = 0
            
            while users_url and page_count < 50:
                print(f"📡 Fetching detailed users page {page_count + 1}...")
                
                response = requests.get(users_url, headers=headers, params=params if page_count == 0 else None)
                
                if response.status_code == 200:
                    data = response.json()
                    users = data.get('value', [])
                    
                    for user in users:
                        email = user.get('mail') or user.get('userPrincipalName')
                        
                        if email and '@' in email:
                            user_info = {
                                'email': email,
                                'display_name': user.get('displayName', ''),
                                'job_title': user.get('jobTitle', ''),
                                'department': user.get('department', ''),
                                'office_location': user.get('officeLocation', ''),
                                'mobile_phone': user.get('mobilePhone', ''),
                                'user_principal_name': user.get('userPrincipalName', '')
                            }
                            all_users.append(user_info)
                    
                    users_url = data.get('@odata.nextLink')
                    params = None
                    page_count += 1
                    
                    print(f"   ✅ Processed {len(users)} users on this page")
                    
                else:
                    print(f"❌ API error: {response.status_code}")
                    break
            
            print(f"✅ Total users with details: {len(all_users)}")
            return all_users
            
        except Exception as e:
            print(f"❌ Error retrieving user details: {e}")
            return []
    
    def export_all_emails_to_excel(self, filename: str = None) -> str:
        """Export all organization emails to Excel file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"organization_emails_{timestamp}.xlsx"
        
        try:
            print("📧 Retrieving all organization emails...")
            users_details = self.get_users_with_details()
            
            if not users_details:
                print("❌ No users found to export")
                return ""
            
            # Create DataFrame
            df = pd.DataFrame(users_details)
            
            # Reorder columns for better readability
            column_order = [
                'email', 'display_name', 'job_title', 'department', 
                'office_location', 'mobile_phone', 'user_principal_name'
            ]
            df = df[column_order]
            
            # Rename columns for Excel
            df.columns = [
                'Email', 'Display Name', 'Job Title', 'Department',
                'Office Location', 'Mobile Phone', 'User Principal Name'
            ]
            
            # Sort by email
            df = df.sort_values('Email')
            
            # Export to Excel with formatting
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main sheet with all users
                df.to_excel(writer, sheet_name='All Users', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['All Users']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Create summary sheet
                self._create_summary_sheet(writer, df)
                
                # Create department breakdown sheet
                self._create_department_sheet(writer, df)
            
            print(f"✅ Excel file created: {filename}")
            print(f"📊 Total users exported: {len(df)}")
            return filename
            
        except Exception as e:
            print(f"❌ Error creating Excel file: {e}")
            return ""
    
    def _create_summary_sheet(self, writer, df):
        """Create summary sheet with statistics"""
        try:
            summary_data = {
                'Metric': [
                    'Total Users',
                    'Users with Job Title',
                    'Users with Department',
                    'Users with Office Location',
                    'Users with Mobile Phone',
                    'Unique Departments',
                    'Export Date'
                ],
                'Value': [
                    len(df),
                    len(df[df['Job Title'].notna() & (df['Job Title'] != '')]),
                    len(df[df['Department'].notna() & (df['Department'] != '')]),
                    len(df[df['Office Location'].notna() & (df['Office Location'] != '')]),
                    len(df[df['Mobile Phone'].notna() & (df['Mobile Phone'] != '')]),
                    df['Department'].nunique(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Auto-adjust columns
            worksheet = writer.sheets['Summary']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 30)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create summary sheet: {e}")
    
    def _create_department_sheet(self, writer, df):
        """Create department breakdown sheet"""
        try:
            # Get department counts
            dept_counts = df['Department'].value_counts().reset_index()
            dept_counts.columns = ['Department', 'User Count']
            
            # Handle empty/null departments
            dept_counts['Department'] = dept_counts['Department'].fillna('Not Specified')
            dept_counts.loc[dept_counts['Department'] == '', 'Department'] = 'Not Specified'
            
            dept_counts.to_excel(writer, sheet_name='Department Breakdown', index=False)
            
            # Auto-adjust columns
            worksheet = writer.sheets['Department Breakdown']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 40)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create department sheet: {e}")
    
    def export_emails_only_to_excel(self, filename: str = None) -> str:
        """Export just the email addresses to Excel (simple version)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emails_only_{timestamp}.xlsx"
        
        try:
            print("📧 Retrieving organization emails...")
            all_emails = self.get_all_organization_emails()
            
            if not all_emails:
                print("❌ No emails found to export")
                return ""
            
            # Create simple DataFrame with just emails
            df = pd.DataFrame({'Email': all_emails})
            
            # Export to Excel
            df.to_excel(filename, index=False, sheet_name='Organization Emails')
            
            print(f"✅ Simple email list exported: {filename}")
            print(f"📧 Total emails: {len(all_emails)}")
            return filename
            
        except Exception as e:
            print(f"❌ Error creating simple Excel file: {e}")
            return ""

# Usage examples
def main():
    """Example usage of the OrganizationEmailsRetriever"""
    
    # Initialize the retriever
    try:
        email_retriever = OrganizationEmailsRetriever()
        print("🚀 Email retriever initialized successfully")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Example 1: Export detailed user information to Excel
    print("\n📊 Exporting detailed user information to Excel...")
    detailed_filename = email_retriever.export_all_emails_to_excel()
    
    if detailed_filename:
        print(f"✅ Detailed Excel file created: {detailed_filename}")
        print("📋 This file contains:")
        print("   - All Users sheet with complete information")
        print("   - Summary sheet with statistics")
        print("   - Department Breakdown sheet")
    
    # Example 2: Export simple email list to Excel
    print("\n📧 Exporting simple email list to Excel...")
    simple_filename = email_retriever.export_emails_only_to_excel()
    
    if simple_filename:
        print(f"✅ Simple email list created: {simple_filename}")
        print("📋 This file contains just email addresses")
    
    # Example 3: Export with custom filename
    print("\n📁 Exporting with custom filename...")
    custom_filename = "my_organization_emails.xlsx"
    result = email_retriever.export_all_emails_to_excel(custom_filename)
    
    if result:
        print(f"✅ Custom filename export successful: {custom_filename}")

if __name__ == "__main__":
    main()
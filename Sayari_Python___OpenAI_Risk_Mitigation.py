import csv
import requests
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time

@dataclass
class CsvRow:
    """Stores data from each row of the CSV file."""
    name: str = ""
    address: str = ""
    country: str = ""

@dataclass
class AuthResponse:
    """Stores authentication response data."""
    access_token: str = ""
    token_type: str = ""
    expires_in: int = 0
    scope: str = ""

@dataclass
class CompanyInfo:
    """Stores information about a company returned from the API."""
    id: str = ""
    pep: bool = False
    sanctioned: bool = False
    label: str = ""
    translated_label: str = ""
    company_type: str = ""
    registration_date: str = ""
    type: str = ""

@dataclass
class Message:
    role: str = ""
    content: str = ""

@dataclass
class Choice:
    message: Message = None
    finish_reason: str = ""

@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class ChatGPTResponse:
    id: str = ""
    object: str = ""
    created: int = 0
    model: str = ""
    choices: List[Choice] = None
    usage: Usage = None

class SayariConsoleApp:
    # API Configuration
    BASE_URL = "https://api.sayari.com"
    AUTH_ENDPOINT = "/oauth/token"
    SEARCH_ENDPOINT = "/v1/search/entity"
    CLIENT_ID = ""
    CLIENT_SECRET = ""
    
    # OpenAI Configuration
    OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    OPENAI_MODEL = "gpt-3.5-turbo"
    OPENAI_AUTH_KEY = ""
    
    # Application Configuration - MODIFY THESE VALUES
    #CSV_FILE_PATH = "companies.csv"  # Path to your CSV file
    CSV_FILE_PATH = r"C:\Users\andrew.winter\Downloads\Sales Engineer Exercise Part 2.xlsx"
    SAVE_RESPONSES = True  # Whether to save API responses to files
    RESPONSE_FOLDER = "responses"  # Folder to save responses
    
    def __init__(self):
        """Initialize the application with empty data structures."""
        self.file_data: List[CsvRow] = []
        self.authentication_info = AuthResponse()
        self.company_info: List[CompanyInfo] = []
        
        # Create response folder if it doesn't exist and if saving is enabled
        if self.SAVE_RESPONSES and not os.path.exists(self.RESPONSE_FOLDER):
            os.makedirs(self.RESPONSE_FOLDER)
    
    def load_csv_data(self):
        """Load company data from CSV file."""
        print(f"Loading data from {self.CSV_FILE_PATH}...")
        
        try:
            with open(self.CSV_FILE_PATH, 'r', encoding='latin-1') as file:
                reader = csv.reader(file)
                
                # Skip header row
                next(reader, None)
                
                # Process each row in the CSV
                for row in reader:
                    csv_row = CsvRow(
                        name=row[0] if len(row) > 0 else "",
                        address=row[1] if len(row) > 1 else "",
                        country=row[2] if len(row) > 2 else ""
                    )
                    self.file_data.append(csv_row)
            
            print(f"Successfully loaded {len(self.file_data)} records")
            for i, row in enumerate(self.file_data):
                print(f"  {i+1}. Name: {row.name}, Address: {row.address}, Country: {row.country}")
            
            print()  # Empty line for readability
            return True
                
        except FileNotFoundError:
            print(f"Error: File '{self.CSV_FILE_PATH}' not found. Please check the file path.")
            return False
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            return False
    
    def authenticate(self):
        """Authenticate with the Sayari API."""
        print("Authenticating with Sayari API...")
        
        try:
            # Prepare the request payload
            payload = {
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "audience": "sayari.com",
                "grant_type": "client_credentials"
            }
            
            # Send the authentication request
            response = requests.post(
                f"{self.BASE_URL}{self.AUTH_ENDPOINT}",
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the response
                auth_data = response.json()
                
                # Update authentication info
                self.authentication_info = AuthResponse(
                    access_token=auth_data.get("access_token", ""),
                    token_type=auth_data.get("token_type", ""),
                    expires_in=auth_data.get("expires_in", 0),
                    scope=auth_data.get("scope", "")
                )
                
                # Check if authentication was successful
                if self.authentication_info.access_token:
                    print("Authentication successful!")
                    print(f"Token expires in {self.authentication_info.expires_in} seconds")
                    print()  # Empty line for readability
                    return True
                else:
                    print("Error: Access token not found in the response")
                    return False
            else:
                # Handle authentication failure
                print(f"Authentication failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False
    
    def search_companies(self):
        """Search for companies using the Sayari API."""
        # Check if authenticated
        if not self.authentication_info.access_token:
            print("Error: Not authenticated. Please authenticate first.")
            return False
            
        # Check if we have data to search
        if not self.file_data:
            print("Error: No company data loaded. Please load CSV data first.")
            return False
        
        print(f"Searching for {len(self.file_data)} companies...")
        
        # Set up headers with the authentication token
        headers = {
            "Authorization": f"Bearer {self.authentication_info.access_token}",
            "Content-Type": "application/json"
        }
        
        # Process each company in the file data
        for i, company in enumerate(self.file_data):
            print(f"Searching for company {i+1}/{len(self.file_data)}: {company.name}")
            
            # Create the search query
            query = f"(name.value:{company.name}~5^2 OR value.address:{company.address})"
            
            # Build the request payload
            payload = {
                "q": query,
                "filter": {
                    "entity_type": ["company"],
                    "county": [company.country]
                },
                "advanced": True
            }
            
            try:
                # Send the search request
                response = requests.post(
                    f"{self.BASE_URL}{self.SEARCH_ENDPOINT}?limit=1",
                    json=payload,
                    headers=headers
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Check if we have data
                    if response_data.get("data") and len(response_data["data"]) > 0:
                        # Extract company data from the first result
                        company_data = response_data["data"][0]
                        
                        # Create CompanyInfo object
                        company_info = CompanyInfo(
                            id=company_data.get("id", ""),
                            pep=company_data.get("pep", False),
                            sanctioned=company_data.get("sanctioned", False),
                            label=company_data.get("label", ""),
                            translated_label=company_data.get("translated_label", ""),
                            company_type=company_data.get("company_type", ""),
                            registration_date=company_data.get("registration_date", ""),
                            type=company_data.get("type", "")
                        )
                        
                        # Add to our list
                        self.company_info.append(company_info)
                        
                        print(f"  Match found: {company_info.label}")
                        print(f"  Sanctioned: {company_info.sanctioned}, PEP: {company_info.pep}")
                        
                        # Optionally save response to a file
                        if self.SAVE_RESPONSES:
                            filename = os.path.join(
                                self.RESPONSE_FOLDER, 
                                f"{company.name.replace(' ', '_')}_response.json"
                            )
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump(response_data, f, indent=2)
                    else:
                        print(f"  No matches found for {company.name}")
                    
                else:
                    print(f"  Search failed with status code: {response.status_code}")
                    print(f"  Response: {response.text}")
                
                # Add a small delay to avoid hitting API rate limits
                time.sleep(0.3)
                    
            except Exception as e:
                print(f"  An error occurred: {str(e)}")
        
        print(f"\nCompleted search with {len(self.company_info)} companies matched")
        print()  # Empty line for readability
        return len(self.company_info) > 0
    
    def get_risk_recommendations(self):
        """Get risk mitigation recommendations for companies using ChatGPT."""
        # Check if we have company data
        if not self.company_info:
            print("Error: No company data available. Please search for companies first.")
            return False
            
        # Get companies that are not sanctioned
        sanctioned_companies = [c for c in self.company_info if c.sanctioned]
        
        if not sanctioned_companies:
            print("No sanctioned companies found to analyze.")
            return False
        
        print(f"Getting risk recommendations for {len(sanctioned_companies)} sanctioned companies...")
        
        # Build the list of company names
        company_names = [c.label for c in sanctioned_companies]
        company_list_text = ", ".join(company_names)
        
        # Set up the prompt
        prompt = f"Please provide actionable recommendations for the specified companies to mitigate risks and improve compliance. The companies are: {company_list_text}"
        
        print("Sending request to ChatGPT...")
        
        # Prepare the request payload
        payload = {
            "model": self.OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": prompt
                }
            ]
        }
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.OPENAI_AUTH_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            # Send the request to OpenAI
            response = requests.post(
                self.OPENAI_ENDPOINT,
                json=payload,
                headers=headers
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    
                    print("\nRisk Mitigation Recommendations:")
                    print("=" * 80)
                    print(content)
                    print("=" * 80)
                    
                    # Optionally save the response
                    if self.SAVE_RESPONSES:
                        filename = os.path.join(self.RESPONSE_FOLDER, "risk_recommendations.txt")
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(content)
                
                return True
                
            else:
                print(f"ChatGPT request failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"An error occurred while calling OpenAI: {str(e)}")
            return False
    
    def find_closest_company(self):
        """Find the company closest to Sayari HQ using ChatGPT."""
        # Check if we have file data
        if not self.file_data:
            print("Error: No company data loaded. Please load CSV data first.")
            return False
        
        print("Finding company closest to Sayari HQ...")
        
        # Build the list of companies with addresses
        company_details = []

        i = 0
 
        for company in self.file_data:
            company_details.append(f"{i+1}. Company Name: {company.name}, full address of company: {company.address}, {company.country}")
            i = i+1
        
        company_list_text = " || ".join(company_details)
        
        # Set up the prompt
        prompt = (f"I have a list of {len(self.file_data)} companies and would like to find which company is located "
                 f"the closest to Sayari's HQ @ 829 7th St NW Floor 3, Washington, DC 20001, USA. "
                 f"The list of companies are {company_list_text}. "
                 f"Please list these companies in order from closest to furthest from Sayari's HQ and include just the "
                 f"company name and calculated distance from the Sayari HQ.")
        
        print("Sending request to ChatGPT...")
        
        # Prepare the request payload
        payload = {
            "model": self.OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": prompt
                }
            ]
        }
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.OPENAI_AUTH_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            # Send the request to OpenAI
            response = requests.post(
                self.OPENAI_ENDPOINT,
                json=payload,
                headers=headers
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    
                    print("\nCompanies by Distance to Sayari HQ:")
                    print("=" * 80)
                    print(content)
                    print("=" * 80)
                    
                    # Optionally save the response
                    if self.SAVE_RESPONSES:
                        filename = os.path.join(self.RESPONSE_FOLDER, "companies_by_distance.txt")
                        with open(filename, 'w', encoding='latin-1') as f:
                            f.write(content)
                
                return True
                
            else:
                print(f"ChatGPT request failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"An error occurred while calling OpenAI: {str(e)}")
            return False
    
    def run(self):
        """Run the console application with all steps."""
        print("=" * 80)
        print("SAYARI DEMONSTRATION CONSOLE APPLICATION")
        print("=" * 80)
        print()
        
        # Step 1: Load CSV data
        if not self.load_csv_data():
            return
        
        # Step 2: Authenticate
        if not self.authenticate():
            return
        
        # Step 3: Search for companies
        if not self.search_companies():
            return
        
        # Step 4: Get risk recommendations
        self.get_risk_recommendations()
        
        # Step 5: Find closest company
        self.find_closest_company()
        
        print("\nApplication finished successfully!")

# Sample usage with hardcoded inputs
def main():
    app = SayariConsoleApp()
    
    # Configure the application
    #app.CSV_FILE_PATH = "companies.csv"  # Path to your CSV file
    app.CSV_FILE_PATH = r"C:\Users\andrew.winter\Downloads\Sales Engineer Exercise Part 2.csv"
    app.SAVE_RESPONSES = True  # Whether to save API responses to files
    app.RESPONSE_FOLDER = "responses"  # Folder to save responses
    
    # Run the application
    app.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Website Summarizer Script

This script takes a URL as input and generates a markdown-formatted summary of the website's content
using the Claude AI model. It supports both static and JavaScript-rendered websites.

Example usage:
    python summarize.py cnn.com
    python summarize.py https://www.bbc.com

Requirements:
    - Python 3.6+
    - anthropic
    - beautifulsoup4
    - python-dotenv
    - requests
    - selenium
    - webdriver_manager

Environment variables:
    ANTHROPIC_API_KEY: Your Anthropic API key
"""

# imports
import os
import sys
import requests
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from anthropic import Anthropic
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()
os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'your-key-if-not-using-env')
claude = Anthropic()


class Website:
    """
    A class to handle website content extraction and preprocessing.

    Attributes:
        url (str): The website URL
        title (str): The website title
        text (str): The extracted and cleaned text content
    """

    url: str
    title: str
    text: str

    def __init__(self, url: str):
        """
        Initialize Website object and fetch content.

        Args:
            url (str): The website URL to process
        """
        # Add http:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url

        # Try static page first
        try:
            self._fetch_static()
        except Exception:
            # If static fetch fails or content seems incomplete, try with Selenium
            self._fetch_dynamic()

    def _fetch_static(self):
        """Fetch content using regular requests"""
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self._process_content(soup)

    def _fetch_dynamic(self):
        """Fetch content using Selenium for JavaScript-rendered pages"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Initialize the Chrome WebDriver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        try:
            driver.get(self.url)
            # Wait for page to load (adjust timeout as needed)
            time.sleep(5)  # Allow time for JavaScript content to load

            # Get the page source and process it
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            self._process_content(soup)
        finally:
            driver.quit()

    def _process_content(self, soup):
        """Process the BeautifulSoup content"""
        self.title = soup.title.string if soup.title else "No title found"

        # Remove irrelevant elements
        for irrelevant in soup.find_all(["script", "style", "img", "input", "iframe", "noscript"]):
            irrelevant.decompose()

        # Get text content
        self.text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""


def user_prompt_for(website: Website) -> str:
    """
    Generate the user prompt for the AI model based on website content.

    Args:
        website (Website): Website object containing the processed content

    Returns:
        str: Formatted prompt string for the AI model
    """
    user_prompt = f"You are looking at a website titled {website.title}. "
    user_prompt += "The contents of this website is as follows; \
please provide a short summary of this website in markdown. \
If it includes news or announcements, then summarize these too.\n\n"
    user_prompt += website.text
    return user_prompt


def summarize(url: str) -> str:
    """
    Generate a markdown-formatted summary of the website content using Claude AI.

    Args:
        url (str): URL of the website to summarize

    Returns:
        str: Markdown-formatted summary of the website content

    Raises:
        requests.exceptions.RequestException: If there's an error fetching the website
        anthropic.APIError: If there's an error with the Claude API
    """
    website = Website(url)

    response = claude.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        system="You are an assistant that analyzes the contents of a website and provides a short summary, ignoring text that might be navigation related. Respond in markdown.",
        messages=[
            {
                "role": "user",
                "content": user_prompt_for(website)
            }
        ]
    )

    return response.content[0].text


def main():
    """
    Main function to handle command-line execution.

    Example usage:
        python summarize.py cnn.com
        python summarize.py https://www.bbc.com
    """
    if len(sys.argv) != 2:
        print("Usage: python summarize.py <url>")
        print("Examples:")
        print("  python summarize.py cnn.com")
        print("  python summarize.py https://www.bbc.com")
        print("\nNote: Make sure you have set the ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    url = sys.argv[1]
    try:
        summary = summarize(url)
        print(summary)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

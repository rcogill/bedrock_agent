"""Research tools for the research agent."""

import io
import re
from typing import Annotated
from urllib.parse import urlparse

import requests
from ddgs import DDGS
from langchain_core.tools import tool

# Common headers to mimic a browser request
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Request timeout in seconds
REQUEST_TIMEOUT = 30


def _clean_html_to_text(html: str) -> str:
    """Convert HTML to plain text by removing tags and cleaning up whitespace."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # Replace common block elements with newlines
    html = re.sub(r'<(br|hr|p|div|h[1-6]|li|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)
    
    # Decode common HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    
    # Clean up whitespace
    html = re.sub(r'\n\s*\n', '\n\n', html)  # Multiple newlines to double
    html = re.sub(r' +', ' ', html)  # Multiple spaces to single
    html = '\n'.join(line.strip() for line in html.split('\n'))  # Strip each line
    html = html.strip()
    
    return html


@tool
def web_search(
    query: Annotated[str, "The search query to look up on the web."],
    num_results: Annotated[int, "Number of results to return (max 10)."] = 5
) -> str:
    """Search the web using DuckDuckGo and return a list of relevant results with titles, URLs, and snippets."""
    try:
        # Validate inputs
        if not query.strip():
            return "Error: Search query cannot be empty."
        
        num_results = min(max(1, num_results), 10)
        
        # Use the ddgs library for reliable DuckDuckGo search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        
        if not results:
            return f"No results found for query: '{query}'"
        
        # Format results
        output_lines = [f"Search results for '{query}':\n"]
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('href', result.get('link', 'No URL'))
            snippet = result.get('body', '')
            
            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   URL: {url}")
            if snippet:
                output_lines.append(f"   {snippet}")
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    except Exception as e:
        return f"Error performing web search: {str(e)}"


@tool
def fetch_webpage(
    url: Annotated[str, "The URL of the webpage to fetch."],
    max_length: Annotated[int, "Maximum number of characters to return."] = 50000
) -> str:
    """Fetch a webpage and return its contents as plain text, with HTML tags removed."""
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        
        if parsed.scheme not in ('http', 'https'):
            return f"Error: Invalid URL scheme '{parsed.scheme}'. Only http and https are supported."
        
        if not parsed.netloc:
            return "Error: Invalid URL - no domain specified."
        
        # Fetch the page
        response = requests.get(
            url,
            headers=BROWSER_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return f"Error: URL returned non-text content type: {content_type}. Use fetch_pdf for PDF documents."
        
        # Convert HTML to text
        text = _clean_html_to_text(response.text)
        
        if not text:
            return f"Error: No text content found at '{url}'."
        
        # Truncate if necessary
        if len(text) > max_length:
            text = text[:max_length] + f"\n\n[Content truncated at {max_length} characters]"
        
        return f"Content from '{url}':\n\n{text}"
    
    except requests.exceptions.Timeout:
        return f"Error: Request timed out after {REQUEST_TIMEOUT} seconds."
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to '{url}'. Check the URL and your internet connection."
    except requests.exceptions.RequestException as e:
        return f"Error fetching webpage: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def fetch_pdf(
    url: Annotated[str, "The URL of the PDF document to fetch."],
    max_length: Annotated[int, "Maximum number of characters to return."] = 50000
) -> str:
    """Fetch a PDF document from the web and extract its text content."""
    try:
        # Import pypdf here to make it an optional dependency
        try:
            from pypdf import PdfReader
        except ImportError:
            return "Error: pypdf library is not installed. Install it with: pip install pypdf"
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        
        if parsed.scheme not in ('http', 'https'):
            return f"Error: Invalid URL scheme '{parsed.scheme}'. Only http and https are supported."
        
        if not parsed.netloc:
            return "Error: Invalid URL - no domain specified."
        
        # Fetch the PDF
        response = requests.get(
            url,
            headers={
                **BROWSER_HEADERS,
                "Accept": "application/pdf,*/*",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
            return f"Error: URL does not appear to be a PDF. Content-Type: {content_type}"
        
        # Check file size (limit to 50MB)
        content_length = len(response.content)
        if content_length > 50_000_000:
            return f"Error: PDF is too large ({content_length / 1_000_000:.1f}MB). Maximum size is 50MB."
        
        # Parse PDF
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
        
        if not text_parts:
            return f"Error: Could not extract text from PDF at '{url}'. The PDF may be image-based or encrypted."
        
        text = "\n\n".join(text_parts)
        
        # Truncate if necessary
        if len(text) > max_length:
            text = text[:max_length] + f"\n\n[Content truncated at {max_length} characters]"
        
        return f"PDF content from '{url}' ({len(reader.pages)} pages):\n\n{text}"
    
    except requests.exceptions.Timeout:
        return f"Error: Request timed out after {REQUEST_TIMEOUT} seconds."
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to '{url}'. Check the URL and your internet connection."
    except requests.exceptions.RequestException as e:
        return f"Error fetching PDF: {str(e)}"
    except Exception as e:
        return f"Error processing PDF: {str(e)}"


# Registry of research tools
RESEARCH_TOOL_REGISTRY = {
    "web_search": web_search,
    "fetch_webpage": fetch_webpage,
    "fetch_pdf": fetch_pdf,
}

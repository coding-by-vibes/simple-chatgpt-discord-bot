import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Tuple
import wikipedia
from urllib.parse import urlparse
import re
import openai
import os

class ArticleSummarizer:
    def __init__(self):
        """Initialize the article summarizer."""
        # Set up OpenAI API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        # Common paywall indicators - only strong indicators
        self.paywall_indicators = [
            'subscribe to continue reading',
            'subscription required',
            'premium members only',
            'paid subscribers only',
            'this content is for subscribers only',
            'sign in to read full story',
            'unlock full access',
            'premium content locked'
        ]
        # Site-specific paywall detection rules
        self.site_paywall_rules = {
            'gamerant.com': {
                'allowed_classes': ['article-body', 'article-content'],
                'ignore_indicators': ['subscribe', 'newsletter', 'sign up']
            }
        }
        # Common irrelevant content indicators
        self.irrelevant_indicators = [
            'advertisement', 'sponsored', 'affiliate', 'you may also like',
            'related articles', 'popular posts', 'trending now', 'more stories',
            'newsletter signup', 'social media', 'follow us', 'share this',
            'comment section', 'comments', 'leave a comment', 'cookie policy',
            'privacy policy', 'terms of service', 'all rights reserved',
            'copyright notice', 'image caption', 'photo credit', 'credit:',
            'image source:', 'source:', 'via:', 'getty images', 'reuters',
            'associated press', 'ap photo', 'shutterstock', 'istock'
        ]
        # Common irrelevant HTML elements
        self.irrelevant_elements = [
            'header', 'footer', 'nav', 'aside', 'script', 'style',
            'noscript', 'iframe', 'form', 'button', 'input', 'select',
            'option', 'meta', 'link', 'noscript', 'object', 'embed',
            'param', 'track', 'source', 'canvas', 'svg', 'math',
            'dialog', 'menu', 'menuitem', 'command', 'keygen', 'output',
            'progress', 'meter', 'details', 'summary', 'figure', 'figcaption'
        ]
        # Common irrelevant classes and IDs
        self.irrelevant_classes = [
            'ad', 'advertisement', 'sponsored', 'promoted', 'sidebar',
            'social-share', 'newsletter', 'comments', 'related',
            'popular', 'trending', 'footer', 'header', 'navigation',
            'menu', 'cookie-notice', 'privacy-notice', 'newsletter-signup',
            'social-media', 'share-buttons', 'author-bio', 'author-info',
            'author-box', 'post-meta', 'post-footer', 'post-tags',
            'post-categories', 'post-navigation', 'pagination'
        ]

    def is_wikipedia_url(self, url: str) -> bool:
        """Check if the URL is from Wikipedia."""
        parsed = urlparse(url)
        return 'wikipedia.org' in parsed.netloc

    def extract_wikipedia_title(self, url: str) -> Optional[str]:
        """Extract the Wikipedia article title from URL."""
        try:
            # Handle both /wiki/Article_Title and /wiki/Article_Title_(disambiguation) formats
            title = url.split('/wiki/')[-1]
            # Remove any URL parameters
            title = title.split('?')[0]
            # Replace underscores with spaces
            title = title.replace('_', ' ')
            return title
        except:
            return None

    def get_wikipedia_summary(self, url: str, sentences: int = 5) -> Optional[Tuple[str, str]]:
        """Get a Wikipedia summary from a URL."""
        try:
            title = self.extract_wikipedia_title(url)
            if not title:
                return None

            # Get the page
            page = wikipedia.page(title)
            
            # Get summary
            summary = wikipedia.summary(title, sentences=sentences)
            
            return summary, page.url
        except wikipedia.exceptions.DisambiguationError as e:
            # Handle disambiguation pages
            try:
                # Try with the first option
                page = wikipedia.page(e.options[0])
                summary = wikipedia.summary(e.options[0], sentences=sentences)
                return summary, page.url
            except:
                return None
        except:
            return None

    def detect_paywall(self, soup: BeautifulSoup, url: str) -> Tuple[bool, str]:
        """Detect if the page has a paywall and return the type of paywall."""
        # Get domain for site-specific rules
        domain = urlparse(url).netloc.lower()
        site_rules = self.site_paywall_rules.get(domain)
        
        # Check for site-specific rules
        if site_rules:
            # For sites with known structure, check if main content is accessible
            for class_name in site_rules.get('allowed_classes', []):
                content = soup.find(class_=class_name)
                if content and len(content.get_text().strip()) > 200:  # Content exists and has substantial length
                    return False, ""
        
        # Get visible text content
        text_content = ' '.join(soup.stripped_strings).lower()
        
        # Check for strong paywall indicators in text
        for indicator in self.paywall_indicators:
            if indicator in text_content:
                # If site-specific rules exist, check if this indicator should be ignored
                if site_rules and any(ignore in indicator for ignore in site_rules.get('ignore_indicators', [])):
                    continue
                return True, "subscription"
        
        # Check for common paywall class names and IDs
        paywall_classes = ['paywall', 'subscription-wall', 'premium-content', 'members-only']
        for class_name in paywall_classes:
            element = soup.find(class_=re.compile(f"^{class_name}$", re.I))
            if element and element.is_displayed():  # Check if element is visible
                return True, "subscription"
        
        # Check for common paywall meta tags
        meta_tags = soup.find_all('meta', property=re.compile('og:type|article:section'))
        for tag in meta_tags:
            if tag.get('content', '').lower() in ['premium', 'subscription']:
                return True, "subscription"
        
        return False, ""

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove multiple spaces and newlines
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        # Remove multiple punctuation marks
        text = re.sub(r'([.,!?])\1+', r'\1', text)
        return text.strip()

    def is_irrelevant_content(self, text: str) -> bool:
        """Check if content is likely irrelevant."""
        text = text.lower()
        # Check for irrelevant indicators
        if any(indicator in text for indicator in self.irrelevant_indicators):
            return True
        # Check for very short content (likely metadata)
        if len(text.split()) < 3:
            return True
        # Check for common irrelevant patterns
        if re.search(r'©\s*\d{4}|all rights reserved|privacy policy|terms of service', text.lower()):
            return True
        return False

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the page."""
        # Remove irrelevant elements
        for element in soup.find_all(self.irrelevant_elements):
            element.decompose()

        # Remove elements with irrelevant classes or IDs
        for class_name in self.irrelevant_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
            for element in soup.find_all(id=re.compile(class_name, re.I)):
                element.decompose()

        # Try to find the main content container
        main_content = None
        common_content_tags = ['article', 'main', 'div[role="main"]', 'div[class*="content"]']
        
        for tag in common_content_tags:
            if tag.startswith('div'):
                main_content = soup.find('div', attrs={'role': 'main'}) or \
                             soup.find('div', class_=re.compile('content|article|post'))
            else:
                main_content = soup.find(tag)
            if main_content:
                break

        # If no main content container found, use body
        if not main_content:
            main_content = soup.find('body')

        if not main_content:
            return ""

        # Extract text content
        content = []
        for element in main_content.stripped_strings:
            text = self.clean_text(element)
            if text and not self.is_irrelevant_content(text):
                content.append(text)

        return ' '.join(content)

    def get_article_content(self, url: str) -> Optional[Dict]:
        """Extract main content from a webpage."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for paywall with URL context
            has_paywall, paywall_type = self.detect_paywall(soup, url)
            if has_paywall:
                return {
                    'error': 'content_restricted',
                    'message': f'This article appears to be restricted ({paywall_type})'
                }
            
            # Extract main content
            content = self.extract_main_content(soup)
            
            # Try to get the article title
            title = None
            title_candidates = [
                soup.find('h1'),
                soup.find('meta', property='og:title'),
                soup.find('meta', property='article:title'),
                soup.find('title')
            ]
            
            for candidate in title_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        title = candidate.get('content')
                    else:
                        title = candidate.get_text()
                    if title:
                        title = self.clean_text(title)
                        break
            
            return {
                "content": content,
                "title": title,
                "url": url
            }
        except Exception as e:
            print(f"Error fetching article: {e}")
            return None

    def summarize_article(self, url: str, summary_type: str = "regular", max_length: int = 1000) -> Optional[Dict]:
        """Summarize an article from a URL.
        
        Args:
            url: The URL of the article to summarize
            summary_type: Type of summary ("tldr", "regular", or "detailed")
            max_length: Maximum length of the summary in tokens
        """
        try:
            # Check if it's a Wikipedia URL
            if self.is_wikipedia_url(url):
                # Adjust sentences based on summary type
                sentences = {
                    "tldr": 2,
                    "regular": 5,
                    "detailed": 8
                }.get(summary_type, 5)
                
                result = self.get_wikipedia_summary(url, sentences=sentences)
                if result:
                    summary, url = result
                    return {
                        "title": self.extract_wikipedia_title(url),
                        "summary": summary,
                        "url": url,
                        "source": "Wikipedia"
                    }
                return None

            # For other websites
            article_data = self.get_article_content(url)
            if not article_data:
                return None
            
            # Check for paywall
            if "error" in article_data and article_data["error"] == "paywall":
                return {
                    "error": "paywall",
                    "title": "Paywalled Article",
                    "url": url,
                    "type": article_data["type"]
                }

            # Adjust system prompt based on summary type
            system_prompts = {
                "tldr": "You are an article summarizer. Create an extremely concise summary (2-3 sentences) focusing only on the most essential information. Be brief and direct.",
                "regular": "You are an article summarizer. Create a concise summary of the article's main points, focusing on the key information and avoiding any promotional or irrelevant content.",
                "detailed": "You are an article summarizer. Create a comprehensive summary of the article, including main points, supporting details, and key takeaways. Focus on providing a thorough understanding while avoiding promotional content."
            }

            # Adjust max tokens based on summary type
            max_tokens = {
                "tldr": 150,
                "regular": 500,
                "detailed": 1000
            }.get(summary_type, 500)

            # Use OpenAI to generate summary
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompts.get(summary_type, system_prompts["regular"])},
                    {"role": "user", "content": f"Please summarize this article:\n\n{article_data['content'][:4000]}"}  # Limit content length
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )

            summary = response.choices[0].message['content']
            
            return {
                "title": article_data["title"] or "Article",
                "summary": summary,
                "url": url,
                "source": "Web Article",
                "type": summary_type
            }
        except Exception as e:
            print(f"Error summarizing article: {e}")
            return None

    def format_summary(self, summary_data: Dict) -> str:
        """Format the summary for Discord."""
        if not summary_data:
            return "❌ Could not summarize the article."

        # Handle paywall error
        if "error" in summary_data and summary_data["error"] == "paywall":
            return (
                f"⚠️ **Paywalled Article Detected**\n\n"
                f"This article appears to be behind a paywall or subscription requirement.\n"
                f"URL: {summary_data['url']}\n\n"
                "**Tips:**\n"
                "- Try accessing the article through your institution's library\n"
                "- Look for alternative sources or similar articles\n"
                "- Check if the article is available in an open access format"
            )

        # Add summary type indicator if it's not a regular summary
        type_indicator = ""
        if summary_data.get("type") == "tldr":
            type_indicator = "**TL;DR:**\n"
        elif summary_data.get("type") == "detailed":
            type_indicator = "**Detailed Summary:**\n"

        response = f"**{summary_data['title']}**\n\n"
        response += f"{type_indicator}{summary_data['summary']}\n\n"
        response += f"**Source:** {summary_data['source']}\n"
        response += f"**Link:** {summary_data['url']}"
        
        return response 
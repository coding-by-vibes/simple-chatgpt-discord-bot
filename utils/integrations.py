import wikipedia
import re
from typing import Dict, Optional, Tuple, List
import tiktoken
from datetime import datetime

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to rough estimation if tiktoken fails
        return len(text.split()) * 1.3

def get_wikipedia_summary(query: str, sentences: int = 5) -> Optional[Tuple[str, str]]:
    """Get a Wikipedia summary for a query.
    
    Args:
        query: The search query
        sentences: Number of sentences to include in summary
        
    Returns:
        Optional[Tuple[str, str]]: Tuple of (summary, url) if found, None otherwise
    """
    try:
        # Search for the page
        search_results = wikipedia.search(query, results=1)
        if not search_results:
            return None
            
        # Get the page
        page = wikipedia.page(search_results[0])
        
        # Get the summary
        summary = wikipedia.summary(search_results[0], sentences=sentences)
        
        # Clean up the summary
        summary = re.sub(r'\([^)]*\)', '', summary)  # Remove parenthetical notes
        summary = re.sub(r'\s+', ' ', summary)  # Normalize whitespace
        summary = summary.strip()
        
        return summary, page.url
        
    except wikipedia.exceptions.DisambiguationError as e:
        # Handle disambiguation pages
        options = e.options[:5]  # Get first 5 options
        return None, f"Multiple matches found. Please be more specific. Options: {', '.join(options)}"
    except wikipedia.exceptions.PageError:
        return None, "No Wikipedia article found."
    except Exception as e:
        return None, f"Error: {str(e)}"

def format_wikipedia_response(title: str, summary: str, url: str, 
                            summary_type: str = "regular",
                            query_note: str = "") -> str:
    """Format a Wikipedia response with appropriate styling.
    
    Args:
        title: The article title
        summary: The article summary
        url: The article URL
        summary_type: Type of summary (tldr, regular, detailed)
        query_note: Optional note about query modification
        
    Returns:
        str: Formatted response
    """
    # Add summary type indicator
    type_indicator = ""
    if summary_type == "tldr":
        type_indicator = "**TL;DR:**\n"
    elif summary_type == "detailed":
        type_indicator = "**Detailed Summary:**\n"
    
    # Format the response
    response = f"**{title}**\n\n{type_indicator}{summary}\n\n**Source:** Wikipedia\n**Link:** {url}"
    
    # Add query note if provided
    if query_note:
        response += f"\n\n{query_note}"
    
    return response

def estimate_conversation_tokens(conversation_history: List[Dict]) -> Dict:
    """Estimate token usage for a conversation.
    
    Args:
        conversation_history: List of conversation messages
        
    Returns:
        Dict: Token usage information
    """
    total_tokens = 0
    message_breakdown = []
    
    for msg in conversation_history:
        # Rough estimate: 1 token ≈ 4 characters
        tokens = len(msg['content']) // 4
        total_tokens += tokens
        message_breakdown.append({
            'role': msg['role'],
            'tokens': tokens
        })
    
    return {
        'total_tokens': total_tokens,
        'message_breakdown': message_breakdown
    }

def clean_wikipedia_query(query: str) -> str:
    """Clean and normalize a Wikipedia search query.
    
    Args:
        query: The search query
        
    Returns:
        str: Cleaned query
    """
    # Remove common words and phrases
    query = re.sub(r'\b(a|an|the|what|who|where|when|why|how|is|are|was|were|will|would|could|should|can|may|might|must)\b', '', query, flags=re.IGNORECASE)
    
    # Remove special characters
    query = re.sub(r'[^\w\s-]', '', query)
    
    # Normalize whitespace
    query = ' '.join(query.split())
    
    return query.strip()

def get_wikipedia_suggestions(query: str) -> List[str]:
    """Get Wikipedia search suggestions for a query.
    
    Args:
        query: The search query
        
    Returns:
        List[str]: List of suggested search terms
    """
    try:
        suggestions = wikipedia.search(query, results=5)
        return suggestions
    except:
        return []

def get_wikipedia_categories(page_title: str) -> List[str]:
    """Get categories for a Wikipedia page.
    
    Args:
        page_title: The Wikipedia page title
        
    Returns:
        List[str]: List of categories
    """
    try:
        page = wikipedia.page(page_title)
        return page.categories
    except:
        return [] 
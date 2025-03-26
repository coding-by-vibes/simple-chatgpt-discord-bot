import re
import json
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import aiohttp
import os
from urllib.parse import quote
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me
import asyncio

class RecipeManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Add headers for HTTP requests with more browser-like properties
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }
        # Add site-specific patterns
        self.site_patterns = {
            'seriouseats.com': {
                'ingredients': r'##\s*Ingredients\s*([^#]+?)(?=\n\s*##\s*Directions)',
                'instructions': r'##\s*Directions\s*([^#]+?)(?=\n\s*##\s*Special Equipment)',
                'servings': r'##\s*Recipe Details\s*[^#]*?Serves\s*([^#]+)',
                'prep_time': r'##\s*Recipe Details\s*[^#]*?Prep\s*([^#]+)',
                'cook_time': r'##\s*Recipe Details\s*[^#]*?Cook\s*([^#]+)',
                'total_time': r'##\s*Recipe Details\s*[^#]*?Total\s*([^#]+)',
            }
        }
        self.recipe_patterns = {
            'ingredients': [
                r'ingredients?:\s*([^#]+)',
                r'what you\'ll need:\s*([^#]+)',
                r'for the [^#]+:\s*([^#]+)',
                r'you will need:\s*([^#]+)',
                r'ingredients\s*list:\s*([^#]+)',
                r'what you need:\s*([^#]+)',
                r'for this recipe:\s*([^#]+)',
                r'ingredients\s*for\s*[^#]+:\s*([^#]+)',
                r'ingredients\s*([^#]+?)(?=\n\s*(?:directions|instructions|steps|method|how to make|preparation|procedure|cooking steps))',
                r'##\s*Ingredients\s*([^#]+?)(?=\n\s*##\s*Directions)',
            ],
            'instructions': [
                r'instructions?:\s*([^#]+)',
                r'directions?:\s*([^#]+)',
                r'steps?:\s*([^#]+)',
                r'method:\s*([^#]+)',
                r'how to make:\s*([^#]+)',
                r'preparation:\s*([^#]+)',
                r'procedure:\s*([^#]+)',
                r'cooking\s*steps?:\s*([^#]+)',
                r'directions\s*([^#]+?)(?=\n\s*(?:notes|special equipment|make-ahead|storage|nutrition facts))',
                r'##\s*Directions\s*([^#]+?)(?=\n\s*##\s*Special Equipment)',
            ],
            'servings': [
                r'serves?\s*(\d+(?:\s*to\s*\d+)?)',
                r'makes?\s*(\d+(?:\s*to\s*\d+)?)',
                r'(\d+(?:\s*to\s*\d+)?)\s*servings?',
                r'yield:\s*(\d+(?:\s*to\s*\d+)?)',
                r'(\d+(?:\s*to\s*\d+)?)\s*portions?',
                r'##\s*Recipe Details\s*[^#]*?Serves\s*([^#]+)',
            ],
            'prep_time': [
                r'prep(?:aration)?\s*time:\s*([^#]+)',
                r'prep:\s*([^#]+)',
                r'preparation:\s*([^#]+)',
                r'prep\s*and\s*planning:\s*([^#]+)',
                r'prep\s*([^#]+)',
                r'##\s*Recipe Details\s*[^#]*?Prep\s*([^#]+)',
            ],
            'cook_time': [
                r'cook(?:ing)?\s*time:\s*([^#]+)',
                r'cook:\s*([^#]+)',
                r'cooking:\s*([^#]+)',
                r'active\s*cooking\s*time:\s*([^#]+)',
                r'infusing\s*time:\s*([^#]+)',
                r'##\s*Recipe Details\s*[^#]*?Cook\s*([^#]+)',
            ],
            'total_time': [
                r'total\s*time:\s*([^#]+)',
                r'total:\s*([^#]+)',
                r'ready\s*in:\s*([^#]+)',
                r'time\s*needed:\s*([^#]+)',
                r'##\s*Recipe Details\s*[^#]*?Total\s*([^#]+)',
            ],
        }
        self.search_api_key = os.getenv('GOOGLE_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        # Validate API credentials
        if not self.search_api_key or not self.search_engine_id:
            self.logger.warning("Google Search API credentials not configured. Recipe search will be limited.")
            self.search_enabled = False
        else:
            self.search_enabled = True
            
        # Updated list of recipe sites with more popular sources
        self.recipe_sites = [
            'allrecipes.com',
            'foodnetwork.com',
            'cooking.nytimes.com',
            'food.com',
            'tasty.co',
            'simplyrecipes.com',
            'cookingclassy.com',
            'tasteofhome.com',
            'recipetineats.com',
            'cookpad.com',
            'bbcgoodfood.com',
            'delish.com',
            'foodandwine.com',
            'food52.com',
            'kitchn.com',
            'marthastewart.com',
            'pioneerwoman.com',
            'southernliving.com',
            'spendwithpennies.com',
            'thespruceeats.com',
            'seriouseats.com'
        ]

    def extract_recipe(self, text: str, source_url: Optional[str] = None) -> Optional[Dict]:
        """Extract recipe information from text."""
        try:
            recipe = {
                'ingredients': [],
                'instructions': [],
                'servings': None,
                'prep_time': None,
                'cook_time': None,
                'total_time': None,
                'source_url': source_url,
                'extracted_at': datetime.now().isoformat(),
            }

            # Use a single regex pattern for ingredients and instructions
            recipe_pattern = r'(?:ingredients?|what you\'ll need|you will need):\s*([^#]+?)(?=\n\s*(?:directions?|instructions?|steps?|method|how to make|preparation|procedure|cooking steps))'
            match = re.search(recipe_pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                recipe['ingredients'] = self._parse_ingredients(match.group(1).strip())

            instructions_pattern = r'(?:directions?|instructions?|steps?|method|how to make|preparation|procedure|cooking steps):\s*([^#]+?)(?=\n\s*(?:notes|special equipment|make-ahead|storage|nutrition facts))'
            match = re.search(instructions_pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                recipe['instructions'] = self._parse_instructions(match.group(1).strip())

            # Combine time patterns into a single pattern
            time_pattern = r'(?:prep(?:aration)?|cook(?:ing)?|total)\s*time:\s*([^#]+)'
            for match in re.finditer(time_pattern, text, re.IGNORECASE | re.DOTALL):
                time_type = match.group(0).split()[0].lower()
                if 'prep' in time_type:
                    recipe['prep_time'] = match.group(1).strip()
                elif 'cook' in time_type:
                    recipe['cook_time'] = match.group(1).strip()
                elif 'total' in time_type:
                    recipe['total_time'] = match.group(1).strip()

            # Simplified servings pattern
            servings_pattern = r'(?:serves?|makes?|yield):\s*([^#]+)'
            match = re.search(servings_pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                recipe['servings'] = match.group(1).strip()

            return recipe if recipe['ingredients'] or recipe['instructions'] else None

        except Exception as e:
            self.logger.error(f"Error extracting recipe: {str(e)}")
            return None

    def _parse_ingredients(self, text: str) -> List[str]:
        """Parse ingredients text into a list of ingredients."""
        # Simplified ingredient parsing
        ingredients = [
            re.sub(r'^[-•*]\s*', '', line.strip())
            for line in text.split('\n')
            if line.strip() and not any(x in line.lower() for x in ['nutrition', 'calories', 'serving'])
        ]
        return ingredients

    def _parse_instructions(self, text: str) -> List[str]:
        """Parse instructions text into a list of steps."""
        try:
            # First try to find numbered steps
            numbered_steps = re.findall(r'\d+[\.\)]\s*([^\n]+)', text)
            if numbered_steps:
                # Filter out empty steps and clean up
                steps = [step.strip() for step in numbered_steps if step.strip()]
                # Remove any remaining step numbers from the beginning
                steps = [re.sub(r'^\d+[\.\)]\s*', '', step) for step in steps]
                return steps

            # If no numbered steps, try to find steps with other indicators
            step_indicators = [
                r'Step\s+\d+[\.\)]\s*([^\n]+)',
                r'Step\s+[A-Za-z]+[\.\)]\s*([^\n]+)',
                r'[A-Za-z][\.\)]\s*([^\n]+)',
                r'•\s*([^\n]+)',
                r'-\s*([^\n]+)',
                r'\*\s*([^\n]+)'
            ]
            
            for pattern in step_indicators:
                steps = re.findall(pattern, text)
                if steps:
                    # Filter out empty steps and clean up
                    steps = [step.strip() for step in steps if step.strip()]
                    # Remove any remaining step numbers or indicators
                    steps = [re.sub(r'^(?:Step\s+\d+[\.\)]|Step\s+[A-Za-z]+[\.\)]|[A-Za-z][\.\)]|•|-|\*)\s*', '', step) for step in steps]
                    return steps

            # If no steps found with indicators, split by newlines and clean up
            lines = text.split('\n')
            steps = []
            current_step = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_step:
                        steps.append(' '.join(current_step))
                        current_step = []
                else:
                    # Skip lines that look like headers or metadata
                    if not any(x in line.lower() for x in ['serious eats', 'photo by', 'image by', 'recipe', 'ingredients', 'directions']):
                        current_step.append(line)
            
            # Add the last step if exists
            if current_step:
                steps.append(' '.join(current_step))
            
            # Clean up steps
            steps = [
                re.sub(r'^\d+[\.\)]\s*', '', step)  # Remove leading numbers
                for step in steps
                if step and len(step) > 1  # Filter out empty or single-character steps
            ]
            
            # If we still have no valid steps, try to split by periods
            if not steps:
                sentences = re.split(r'[.!?]+', text)
                steps = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]
            
            # Final cleanup to ensure no empty steps
            steps = [step for step in steps if step.strip()]
            
            return steps
            
        except Exception as e:
            self.logger.error(f"Error parsing instructions: {str(e)}")
            return []

    def format_recipe_card(self, recipe: Dict) -> List[str]:
        """Format recipe into a concise card format, splitting into multiple messages if needed."""
        try:
            if not recipe:
                self.logger.error("Attempted to format empty recipe")
                return ["Error: No recipe data available"]

            # Log the recipe data for debugging
            self.logger.info(f"Formatting recipe card for: {recipe.get('title', 'Untitled Recipe')}")
            
            messages = []
            current_message = "```markdown\n"
            
            # Add title if available
            if recipe.get('title'):
                current_message = f"```markdown\n📝 {recipe['title']}\n"
            
            # Combine time information into one line if available
            time_info = []
            try:
                if recipe.get('prep_time'):
                    time_info.append(f"Prep: {recipe['prep_time']}")
                if recipe.get('cook_time'):
                    time_info.append(f"Cook: {recipe['cook_time']}")
                if recipe.get('total_time'):
                    time_info.append(f"Total: {recipe['total_time']}")
                if time_info:
                    current_message += "⏱️ " + " | ".join(time_info) + "\n"
            except Exception as e:
                self.logger.warning(f"Error formatting time info: {str(e)}")
            
            try:
                if recipe.get('servings'):
                    current_message += f"👥 {recipe['servings']}\n"
            except Exception as e:
                self.logger.warning(f"Error formatting servings: {str(e)}")
            
            # Format ingredients more compactly
            try:
                if recipe.get('ingredients'):
                    current_message += "\nIngredients:\n"
                    # Show all ingredients
                    for ing in recipe['ingredients']:
                        if ing and isinstance(ing, str):
                            # Check if adding this ingredient would exceed the limit
                            if len(current_message + f"• {ing}\n") > 1900:
                                current_message += "\n```"
                                messages.append(current_message)
                                current_message = "```markdown\n"
                            current_message += f"• {ing}\n"
            except Exception as e:
                self.logger.warning(f"Error formatting ingredients: {str(e)}")
            
            # Format instructions more compactly
            try:
                if recipe.get('instructions'):
                    current_message += "\nSteps:\n"
                    # Show all steps without truncation
                    for i, step in enumerate(recipe['instructions'], 1):
                        if step and isinstance(step, str):
                            # Remove "Step X" prefix if present
                            step = re.sub(r'^Step\s+\d+\s*', '', step)
                            step_text = f"{i}. {step}\n"
                            
                            # Check if adding this step would exceed the limit
                            if len(current_message + step_text) > 1900:
                                current_message += "\n```"
                                messages.append(current_message)
                                current_message = "```markdown\n"
                            current_message += step_text
            except Exception as e:
                self.logger.warning(f"Error formatting instructions: {str(e)}")
            
            # Only add source if it's not too long
            try:
                if recipe.get('url'):
                    source_text = f"\nSource: {recipe['url']}"
                    # Check if adding the source would exceed the limit
                    if len(current_message + source_text) > 1900:
                        current_message += "\n```"
                        messages.append(current_message)
                        current_message = "```markdown\n"
                    current_message += source_text
            except Exception as e:
                self.logger.warning(f"Error formatting source URL: {str(e)}")
            
            # Close the markdown code block for the last message
            current_message += "\n```"
            messages.append(current_message)
            
            # Log the final message lengths
            for i, msg in enumerate(messages, 1):
                self.logger.info(f"Generated message {i} with length: {len(msg)}")
            
            return messages

        except Exception as e:
            self.logger.error(f"Error formatting recipe card: {str(e)}")
            return ["Error formatting recipe card"]

    def is_recipe_content(self, text: str) -> bool:
        """Check if text appears to contain a recipe."""
        # Look for common recipe indicators
        indicators = [
            r'ingredients?',
            r'instructions?',
            r'directions?',
            r'steps?',
            r'serves?',
            r'makes?',
            r'prep\s*time',
            r'cook\s*time',
            r'total\s*time',
        ]
        
        # Check for multiple indicators
        count = sum(1 for pattern in indicators if re.search(pattern, text, re.IGNORECASE))
        return count >= 2  # Return True if at least 2 indicators are found 

    async def search_recipes(self, query: str, max_results: int = 3) -> List[Dict]:
        """Search for recipes online."""
        try:
            if not self.search_enabled:
                self.logger.warning("Recipe search is disabled due to missing API credentials")
                return []

            if not self.search_api_key:
                self.logger.error("Google API key not configured")
                return []

            if not self.search_engine_id:
                self.logger.error("Google Search Engine ID not configured")
                return []

            # Add recipe-specific terms to the query
            enhanced_query = f"{query} recipe cooking instructions ingredients"
            self.logger.info(f"Searching for recipes with query: {enhanced_query}")
            
            # Create search URL
            base_url = "https://www.googleapis.com/customsearch/v1"
            
            # Use a simpler search approach with fewer sites initially
            initial_sites = self.recipe_sites[:5]  # Start with top 5 sites
            site_query = " OR ".join(f"site:{site}" for site in initial_sites)
            full_query = f"{enhanced_query} ({site_query})"
            
            params = {
                'key': self.search_api_key,
                'cx': self.search_engine_id,
                'q': full_query,
                'num': max_results,
                'safe': 'off',
                'exactTerms': 'recipe'  # Ensure we get recipe pages
            }
            
            self.logger.info(f"Making API request with params: {params}")

            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    self.logger.info(f"API Response Status: {response.status}")
                    
                    if response.status == 403:
                        self.logger.error("Invalid API key or Search Engine ID")
                        return []
                    elif response.status != 200:
                        self.logger.error(f"Search API error: {response.status}")
                        return []

                    data = await response.json()
                    self.logger.info(f"API Response Data: {data}")
                    
                    if 'error' in data:
                        self.logger.error(f"API Error: {data['error'].get('message', 'Unknown error')}")
                        return []

                    if 'items' not in data:
                        self.logger.warning("No search results found")
                        return []

                    results = []
                    for item in data['items']:
                        # Extract recipe information from the search result
                        recipe_info = {
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'snippet': item.get('snippet', ''),
                            'source': self._extract_source(item.get('link', '')),
                            'rating': self._extract_rating(item.get('snippet', '')),
                            'cooking_time': self._extract_cooking_time(item.get('snippet', '')),
                            'difficulty': self._extract_difficulty(item.get('snippet', ''))
                        }
                        results.append(recipe_info)

                    self.logger.info(f"Found {len(results)} recipe results")
                    return results

        except Exception as e:
            self.logger.error(f"Error searching recipes: {str(e)}")
            return []

    def _extract_source(self, url: str) -> str:
        """Extract the source website from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "Unknown source"

    def _extract_rating(self, text: str) -> Optional[str]:
        """Extract rating information from text."""
        try:
            # Look for common rating patterns
            rating_patterns = [
                r'(\d+(?:\.\d+)?)\s*out\s*of\s*(\d+)',
                r'(\d+(?:\.\d+)?)\s*\/\s*(\d+)',
                r'(\d+(?:\.\d+)?)\s*stars?',
            ]
            
            for pattern in rating_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        return f"{match.group(1)}/{match.group(2)}"
                    return f"{match.group(1)}/5"
            return None
        except Exception:
            return None

    def _extract_cooking_time(self, text: str) -> Optional[str]:
        """Extract cooking time information from text."""
        try:
            time_patterns = [
                r'(\d+)\s*(?:min|minute|hr|hour)s?\s*to\s*cook',
                r'cooking\s*time:\s*(\d+)\s*(?:min|minute|hr|hour)s?',
                r'cook\s*for\s*(\d+)\s*(?:min|minute|hr|hour)s?',
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    time = int(match.group(1))
                    if 'hr' in match.group(0) or 'hour' in match.group(0):
                        return f"{time} hour{'s' if time != 1 else ''}"
                    return f"{time} minute{'s' if time != 1 else ''}"
            return None
        except Exception:
            return None

    def _extract_difficulty(self, text: str) -> Optional[str]:
        """Extract difficulty level from text."""
        try:
            difficulty_patterns = [
                r'(easy|simple|beginner)',
                r'(medium|moderate|intermediate)',
                r'(hard|difficult|advanced)',
            ]
            
            for pattern in difficulty_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).capitalize()
            return None
        except Exception:
            return None

    def format_search_results(self, results: List[Dict]) -> str:
        """Format search results into a readable message."""
        if not results:
            return "No recipes found matching your search."

        message = "🔍 **Recipe Search Results**\n\n"
        
        for i, recipe in enumerate(results, 1):
            message += f"**{i}. {recipe['title']}**\n"
            
            if recipe.get('source'):
                message += f"📌 Source: {recipe['source']}\n"
            
            if recipe.get('rating'):
                message += f"⭐ Rating: {recipe['rating']}\n"
            
            if recipe.get('cooking_time'):
                message += f"⏱️ Time: {recipe['cooking_time']}\n"
            
            if recipe.get('difficulty'):
                message += f"📊 Difficulty: {recipe['difficulty']}\n"
            
            if recipe.get('link'):
                message += f"🔗 Link: {recipe['link']}\n"
            
            message += "\n"  # Add spacing between recipes
        
        return message 

    def _convert_iso_duration(self, duration: str) -> str:
        """Convert ISO 8601 duration format to human readable time."""
        try:
            # Remove PT prefix
            duration = duration.replace('PT', '')
            
            # Initialize time components
            hours = 0
            minutes = 0
            seconds = 0
            
            # Parse hours
            if 'H' in duration:
                hours_part = duration.split('H')[0]
                hours = int(hours_part)
                duration = duration.split('H')[1]
            
            # Parse minutes
            if 'M' in duration:
                minutes_part = duration.split('M')[0]
                minutes = int(minutes_part)
                duration = duration.split('M')[1]
            
            # Parse seconds
            if 'S' in duration:
                seconds_part = duration.split('S')[0]
                seconds = int(seconds_part)
            
            # Convert to total minutes
            total_minutes = hours * 60 + minutes + (seconds // 60)
            
            # Format the output
            if total_minutes >= 60:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if minutes == 0:
                    return f"{hours} hour{'s' if hours != 1 else ''}"
                return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"
                
        except Exception as e:
            self.logger.error(f"Error converting ISO duration: {str(e)}")
            return duration  # Return original if conversion fails

    async def extract_recipe_from_article(self, url: str) -> Optional[Dict]:
        """Extract recipe information from a URL using recipe-scrapers with fallback logic."""
        try:
            # First try to fetch the page to verify accessibility
            async with aiohttp.ClientSession(headers=self.headers) as session:
                try:
                    self.logger.info(f"Attempting to fetch URL: {url}")
                    async with session.get(url, timeout=30, ssl=False) as response:
                        if response.status == 403:
                            self.logger.warning(f"Access forbidden (403) for {url}. Trying with alternative headers...")
                            # Try with a different set of headers
                            alt_headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Accept-Encoding': 'gzip, deflate',  # Remove brotli from alternative headers
                                'Connection': 'keep-alive',
                                'Upgrade-Insecure-Requests': '1'
                            }
                            async with aiohttp.ClientSession(headers=alt_headers) as alt_session:
                                async with alt_session.get(url, timeout=30, ssl=False) as alt_response:
                                    if alt_response.status != 200:
                                        self.logger.error(f"Failed to fetch URL {url} with alternative headers: Status {alt_response.status}")
                                        return None
                                    html_content = await alt_response.text()
                                    self.logger.info(f"Successfully fetched URL: {url} with alternative headers")
                        elif response.status != 200:
                            self.logger.error(f"Failed to fetch URL {url}: Status {response.status}")
                            return None
                        else:
                            try:
                                html_content = await response.text()
                                self.logger.info(f"Successfully fetched URL: {url}")
                            except Exception as e:
                                self.logger.warning(f"Error decoding response: {str(e)}. Trying without brotli compression...")
                                # Try again without brotli compression
                                alt_headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Accept-Encoding': 'gzip, deflate',
                                    'Connection': 'keep-alive',
                                    'Upgrade-Insecure-Requests': '1'
                                }
                                async with aiohttp.ClientSession(headers=alt_headers) as alt_session:
                                    async with alt_session.get(url, timeout=30, ssl=False) as alt_response:
                                        if alt_response.status != 200:
                                            self.logger.error(f"Failed to fetch URL {url} with alternative headers: Status {alt_response.status}")
                                            return None
                                        html_content = await alt_response.text()
                                        self.logger.info(f"Successfully fetched URL: {url} with alternative headers")
                except aiohttp.ClientError as e:
                    self.logger.error(f"Network error while fetching {url}: {str(e)}")
                    return None
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout while fetching {url}")
                    return None
                except Exception as e:
                    self.logger.error(f"Unexpected error while fetching {url}: {str(e)}")
                    return None

            # Try recipe-scrapers first
            try:
                self.logger.info(f"Attempting to scrape recipe from {url} using recipe-scrapers")
                recipe = scrape_me(url)
                
                # Extract basic recipe info with error handling
                title = recipe.title() if hasattr(recipe, 'title') else None
                ingredients = recipe.ingredients() if hasattr(recipe, 'ingredients') else []
                
                # Handle instructions more carefully
                instructions = []
                if hasattr(recipe, 'instructions'):
                    try:
                        raw_instructions = recipe.instructions()
                        if isinstance(raw_instructions, str):
                            # Split by newlines and clean up
                            instructions = [step.strip() for step in raw_instructions.split('\n') if step.strip()]
                            # If we got empty steps, try splitting by periods
                            if not instructions or any(not step for step in instructions):
                                sentences = re.split(r'[.!?]+', raw_instructions)
                                instructions = [s.strip() for s in sentences if s.strip()]
                        elif isinstance(raw_instructions, list):
                            instructions = [step.strip() for step in raw_instructions if step.strip()]
                            # If we got empty steps, try combining related steps
                            if not instructions or any(not step for step in instructions):
                                combined_text = ' '.join(raw_instructions)
                                sentences = re.split(r'[.!?]+', combined_text)
                                instructions = [s.strip() for s in sentences if s.strip()]
                    except Exception as e:
                        self.logger.warning(f"Failed to parse instructions: {str(e)}")
                
                # Clean up instructions to remove empty steps and ensure proper formatting
                instructions = [step for step in instructions if step and len(step) > 1]
                if instructions:
                    # Remove any remaining step numbers or indicators
                    instructions = [re.sub(r'^(?:Step\s+\d+[\.\)]|Step\s+[A-Za-z]+[\.\)]|[A-Za-z][\.\)]|•|-|\*)\s*', '', step) for step in instructions]
                    # Remove any leading numbers
                    instructions = [re.sub(r'^\d+[\.\)]\s*', '', step) for step in instructions]
                    # Final cleanup
                    instructions = [step.strip() for step in instructions if step.strip()]
                
                # Try to get yields with error handling
                try:
                    yields = recipe.yields()
                except Exception as e:
                    self.logger.warning(f"Failed to get yields: {str(e)}")
                    yields = None
                    
                # Try to get times with error handling
                try:
                    prep_time = recipe.prep_time()
                    if prep_time and not isinstance(prep_time, int):
                        prep_time = self._convert_iso_duration(prep_time) if 'PT' in prep_time else prep_time
                    else:
                        prep_time = None
                except Exception as e:
                    self.logger.warning(f"Failed to get prep time: {str(e)}")
                    prep_time = None
                    
                try:
                    cook_time = recipe.cook_time()
                    if cook_time and not isinstance(cook_time, int):
                        cook_time = self._convert_iso_duration(cook_time) if 'PT' in cook_time else cook_time
                    else:
                        cook_time = None
                except Exception as e:
                    self.logger.warning(f"Failed to get cook time: {str(e)}")
                    cook_time = None
                    
                try:
                    total_time = recipe.total_time()
                    if total_time and not isinstance(total_time, int):
                        total_time = self._convert_iso_duration(total_time) if 'PT' in total_time else total_time
                    else:
                        total_time = None
                except Exception as e:
                    self.logger.warning(f"Failed to get total time: {str(e)}")
                    total_time = None

                # If we have either ingredients or instructions, create a recipe object
                if ingredients or instructions:
                    self.logger.info(f"Successfully extracted recipe from {url} using recipe-scrapers")
                    return {
                        "title": title,
                        "ingredients": ingredients or [],
                        "instructions": instructions or [],
                        "servings": yields,
                        "prep_time": prep_time,
                        "cook_time": cook_time,
                        "total_time": total_time,
                        "url": url
                    }
            except Exception as e:
                self.logger.warning(f"Recipe-scrapers failed for {url}: {str(e)}")

            # If recipe-scrapers failed, try structured data extraction
            self.logger.info(f"Attempting structured data extraction for {url}")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for structured data
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Recipe':
                        # Extract recipe data from structured data
                        recipe_data = {
                            "title": data.get('name'),
                            "ingredients": data.get('recipeIngredient', []),
                            "instructions": [step.get('text', '') for step in data.get('recipeInstructions', [])],
                            "servings": data.get('recipeYield'),
                            "prep_time": data.get('prepTime'),
                            "cook_time": data.get('cookTime'),
                            "total_time": data.get('totalTime'),
                            "url": url
                        }
                        
                        # Only return if we have either ingredients or instructions
                        if recipe_data["ingredients"] or recipe_data["instructions"]:
                            self.logger.info(f"Successfully extracted recipe from {url} using structured data")
                            return recipe_data
                except Exception as e:
                    self.logger.warning(f"Failed to parse structured data: {str(e)}")
                    continue

            # If both methods failed, try text-based extraction
            self.logger.info(f"Attempting text-based extraction for {url}")
            recipe_data = self._extract_recipe_from_text(html_content)
            if recipe_data:
                recipe_data["url"] = url
                self.logger.info(f"Successfully extracted recipe from {url} using text-based extraction")
                return recipe_data

            self.logger.warning(f"Failed to extract recipe from {url} using all methods")
            return None

        except Exception as e:
            self.logger.error(f"Error extracting recipe from {url}: {str(e)}")
            return None

    def _extract_recipe_from_text(self, html_content: str) -> Optional[Dict]:
        """Extract recipe information from HTML content using text-based patterns."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Initialize recipe data
            recipe_data = {
                "title": None,
                "ingredients": [],
                "instructions": [],
                "servings": None,
                "prep_time": None,
                "cook_time": None,
                "total_time": None
            }
            
            # Try to find title
            title_tag = soup.find('h1')
            if title_tag:
                recipe_data["title"] = title_tag.get_text().strip()
            
            # Extract ingredients
            for pattern in self.recipe_patterns['ingredients']:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    ingredients_text = match.group(1).strip()
                    recipe_data["ingredients"] = self._parse_ingredients(ingredients_text)
                    break
            
            # Extract instructions
            for pattern in self.recipe_patterns['instructions']:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    instructions_text = match.group(1).strip()
                    recipe_data["instructions"] = self._parse_instructions(instructions_text)
                    break
            
            # Extract servings
            for pattern in self.recipe_patterns['servings']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    recipe_data["servings"] = match.group(1).strip()
                    break
            
            # Extract times
            for pattern in self.recipe_patterns['prep_time']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    recipe_data["prep_time"] = match.group(1).strip()
                    break
            
            for pattern in self.recipe_patterns['cook_time']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    recipe_data["cook_time"] = match.group(1).strip()
                    break
            
            for pattern in self.recipe_patterns['total_time']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    recipe_data["total_time"] = match.group(1).strip()
                    break
            
            # Only return if we have either ingredients or instructions
            if recipe_data["ingredients"] or recipe_data["instructions"]:
                return recipe_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in text-based extraction: {str(e)}")
            return None 
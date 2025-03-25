import re
from typing import Dict, List, Optional, Tuple
import ast
from collections import defaultdict

class CodeAnalyzer:
    def __init__(self):
        """Initialize the code analyzer with patterns and rules."""
        # Code quality patterns
        self.quality_patterns = {
            "long_function": r"def\s+\w+\s*\([^)]*\):[\s\S]*?(?:\n\s{4}){10,}",
            "long_line": r".{100,}",
            "magic_number": r"\b\d{4,}\b",
            "todo_comment": r"#\s*(TODO|FIXME|XXX|HACK)",
            "print_statement": r"print\s*\(",
            "hardcoded_string": r'["\'](?:[^"\']*["\']){3,}',
            "nested_loop": r"for\s+.*:\s*\n\s+for\s+.*:",
            "complex_condition": r"if\s+.*\s+and\s+.*\s+and\s+.*:",
            "global_variable": r"global\s+\w+",
            "bare_except": r"except:",
            "pass_statement": r"pass\s*$"
        }
        
        # Performance patterns
        self.performance_patterns = {
            "list_comprehension": r"\[.*for.*in.*\]",
            "generator_expression": r"\(.*for.*in.*\)",
            "set_operation": r"set\(.*\)",
            "dictionary_comprehension": r"\{.*for.*in.*\}",
            "lambda_function": r"lambda\s+.*:",
            "map_filter": r"(?:map|filter)\s*\(",
            "list_append": r"\.append\s*\(",
            "list_extend": r"\.extend\s*\(",
            "string_concatenation": r"\+\s*[\"']",
            "in_operator": r"\bin\b"
        }
        
        # Security patterns
        self.security_patterns = {
            "eval_exec": r"(?:eval|exec)\s*\(",
            "shell_command": r"(?:os\.system|subprocess\.call)\s*\(",
            "file_operation": r"open\s*\(",
            "sql_injection": r"\.execute\s*\(\s*[\"'].*%.*[\"']",
            "password_hardcoded": r"password\s*=\s*[\"'].*[\"']",
            "sensitive_data": r"(?:api_key|secret|token|password|key)\s*=\s*[\"'].*[\"']",
            "unsafe_yaml": r"yaml\.load\s*\(",
            "pickle_usage": r"pickle\.(?:load|loads|dump|dumps)\s*\(",
            "temp_file": r"tempfile\.NamedTemporaryFile\s*\(",
            "random_seed": r"random\.seed\s*\("
        }
        
        # Best practices patterns
        self.best_practices_patterns = {
            "docstring": r'""".*?"""',
            "type_hint": r":\s*(?:int|float|str|bool|list|dict|set|tuple|Optional|Union|Any)",
            "constant_uppercase": r"[A-Z_]{3,}\s*=",
            "class_docstring": r"class\s+\w+\s*:[\s\S]*?\"\"\"",
            "function_docstring": r"def\s+\w+\s*\([^)]*\):[\s\S]*?\"\"\"",
            "logging_usage": r"logging\.(?:debug|info|warning|error|critical)\s*\(",
            "assert_statement": r"assert\s+",
            "context_manager": r"with\s+",
            "enum_usage": r"Enum\s*\(",
            "dataclass_usage": r"@dataclass"
        }
    
    def analyze_code(self, code: str) -> Dict[str, List[Dict[str, str]]]:
        """Analyze code and return suggestions for improvement.
        
        Args:
            code: The code to analyze
            
        Returns:
            Dict containing analysis results and suggestions
        """
        results = {
            "quality": [],
            "performance": [],
            "security": [],
            "best_practices": [],
            "complexity": []
        }
        
        try:
            # Parse code into AST
            tree = ast.parse(code)
            
            # Analyze code quality
            for pattern_name, pattern in self.quality_patterns.items():
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    results["quality"].append({
                        "type": pattern_name,
                        "line": code[:match.start()].count('\n') + 1,
                        "suggestion": self._get_quality_suggestion(pattern_name)
                    })
            
            # Analyze performance
            for pattern_name, pattern in self.performance_patterns.items():
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    results["performance"].append({
                        "type": pattern_name,
                        "line": code[:match.start()].count('\n') + 1,
                        "suggestion": self._get_performance_suggestion(pattern_name)
                    })
            
            # Analyze security
            for pattern_name, pattern in self.security_patterns.items():
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    results["security"].append({
                        "type": pattern_name,
                        "line": code[:match.start()].count('\n') + 1,
                        "suggestion": self._get_security_suggestion(pattern_name)
                    })
            
            # Analyze best practices
            for pattern_name, pattern in self.best_practices_patterns.items():
                matches = re.finditer(pattern, code, re.MULTILINE)
                for match in matches:
                    results["best_practices"].append({
                        "type": pattern_name,
                        "line": code[:match.start()].count('\n') + 1,
                        "suggestion": self._get_best_practices_suggestion(pattern_name)
                    })
            
            # Analyze complexity
            complexity_results = self._analyze_complexity(tree)
            results["complexity"].extend(complexity_results)
            
        except SyntaxError as e:
            results["quality"].append({
                "type": "syntax_error",
                "line": e.lineno,
                "suggestion": f"Syntax error: {str(e)}"
            })
        
        return results
    
    def _analyze_complexity(self, tree: ast.AST) -> List[Dict[str, str]]:
        """Analyze code complexity using AST.
        
        Args:
            tree: The AST of the code
            
        Returns:
            List of complexity issues and suggestions
        """
        complexity_issues = []
        
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.nested_depth = 0
                self.max_nested_depth = 0
                self.issues = []
            
            def visit_If(self, node):
                self.nested_depth += 1
                self.max_nested_depth = max(self.max_nested_depth, self.nested_depth)
                if self.nested_depth > 4:
                    self.issues.append({
                        "type": "high_nesting",
                        "line": node.lineno,
                        "suggestion": "Consider refactoring to reduce nesting depth"
                    })
                self.generic_visit(node)
                self.nested_depth -= 1
            
            def visit_For(self, node):
                self.nested_depth += 1
                self.max_nested_depth = max(self.max_nested_depth, self.nested_depth)
                if self.nested_depth > 4:
                    self.issues.append({
                        "type": "high_nesting",
                        "line": node.lineno,
                        "suggestion": "Consider refactoring to reduce nesting depth"
                    })
                self.generic_visit(node)
                self.nested_depth -= 1
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        complexity_issues.extend(visitor.issues)
        
        return complexity_issues
    
    def _get_quality_suggestion(self, pattern_name: str) -> str:
        """Get suggestion for quality issues."""
        suggestions = {
            "long_function": "Consider breaking down this function into smaller, more focused functions",
            "long_line": "Line is too long. Consider breaking it into multiple lines",
            "magic_number": "Consider defining this number as a named constant",
            "todo_comment": "Address this TODO comment to improve code quality",
            "print_statement": "Consider using logging instead of print statements",
            "hardcoded_string": "Consider moving repeated strings to constants",
            "nested_loop": "Consider using itertools.product() or restructuring to reduce nesting",
            "complex_condition": "Consider breaking down this complex condition into smaller parts",
            "global_variable": "Avoid using global variables. Consider passing values as parameters",
            "bare_except": "Avoid bare except clauses. Catch specific exceptions instead",
            "pass_statement": "Consider implementing proper functionality instead of using pass"
        }
        return suggestions.get(pattern_name, "Review this code section for potential improvements")
    
    def _get_performance_suggestion(self, pattern_name: str) -> str:
        """Get suggestion for performance issues."""
        suggestions = {
            "list_comprehension": "Consider using a generator expression for better memory usage",
            "generator_expression": "Good use of generator expression for memory efficiency",
            "set_operation": "Consider using set operations for better performance with unique items",
            "dictionary_comprehension": "Good use of dictionary comprehension for efficient mapping",
            "lambda_function": "Consider using a named function for better readability and reusability",
            "map_filter": "Consider using list comprehension for better readability",
            "list_append": "Consider using list comprehension or extend() for multiple items",
            "list_extend": "Good use of extend() for adding multiple items",
            "string_concatenation": "Consider using f-strings or join() for string concatenation",
            "in_operator": "Consider using set for faster lookups"
        }
        return suggestions.get(pattern_name, "Review this code section for potential performance improvements")
    
    def _get_security_suggestion(self, pattern_name: str) -> str:
        """Get suggestion for security issues."""
        suggestions = {
            "eval_exec": "Avoid using eval() or exec(). They can execute arbitrary code",
            "shell_command": "Use subprocess.run() with shell=False for better security",
            "file_operation": "Always use context managers (with) for file operations",
            "sql_injection": "Use parameterized queries to prevent SQL injection",
            "password_hardcoded": "Never hardcode passwords. Use environment variables or secure storage",
            "sensitive_data": "Avoid hardcoding sensitive data. Use secure configuration management",
            "unsafe_yaml": "Use yaml.safe_load() instead of yaml.load()",
            "pickle_usage": "Avoid using pickle for security reasons. Use JSON or other safe formats",
            "temp_file": "Always use delete=True with temporary files",
            "random_seed": "Avoid setting random seed in production code"
        }
        return suggestions.get(pattern_name, "Review this code section for potential security issues")
    
    def _get_best_practices_suggestion(self, pattern_name: str) -> str:
        """Get suggestion for best practices."""
        suggestions = {
            "docstring": "Good use of docstring for documentation",
            "type_hint": "Good use of type hints for better code clarity",
            "constant_uppercase": "Good use of uppercase for constants",
            "class_docstring": "Good use of class docstring for documentation",
            "function_docstring": "Good use of function docstring for documentation",
            "logging_usage": "Good use of logging for proper error tracking",
            "assert_statement": "Good use of assertions for debugging",
            "context_manager": "Good use of context manager for resource management",
            "enum_usage": "Good use of Enum for type safety",
            "dataclass_usage": "Good use of dataclass for data structures"
        }
        return suggestions.get(pattern_name, "Consider following Python best practices") 
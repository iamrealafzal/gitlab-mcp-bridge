"""
Log Analyzer Service for parsing error logs and extracting context
"""
import re
import os
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Service for analyzing log files and extracting error information"""
    
    # Common error patterns
    ERROR_PATTERNS = [
        # Python tracebacks
        (r'File "([^"]+)", line (\d+)', 'python'),
        (r'Traceback \(most recent call last\):', 'python'),
        # JavaScript/Node.js errors
        (r'at (.+?) \((.+?):(\d+):(\d+)\)', 'javascript'),
        (r'Error: (.+)', 'javascript'),
        # Java stack traces
        (r'at (.+?)\((.+?):(\d+)\)', 'java'),
        # Generic file:line patterns (but exclude pure numbers)
        (r'([^\s:]+\.(py|js|java|ts|tsx|go|rs|rb|php)):(\d+):', 'generic'),
        (r'([^\s:]+\.(py|js|java|ts|tsx|go|rs|rb|php))\((\d+)\)', 'generic'),
        # File path patterns with slashes (more reliable)
        (r'([^\s:]+/[^\s:]+):(\d+)', 'generic'),
        (r'([^\s:]+\\[^\s:]+):(\d+)', 'generic'),
    ]
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = None
        self.errors = []
    
    def read_log(self) -> str:
        """Read log file content"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Log file not found: {self.file_path}")
        
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()
        return self.content
    
    def extract_errors(self) -> List[Dict[str, any]]:
        """
        Extract error information from log file
        
        Returns:
            List of error dictionaries with 'type', 'message', 'file_path', 'line_number', 'context'
        """
        if not self.content:
            self.read_log()
        
        errors = []
        lines = self.content.split('\n')
        
        # Look for error patterns
        for i, line in enumerate(lines):
            for pattern, error_type in self.ERROR_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    error_info = {
                        'type': error_type,
                        'line_in_log': i + 1,
                        'raw_line': line,
                    }
                    
                    # Extract file path and line number if available
                    if error_type == 'python' and len(match.groups()) >= 2:
                        error_info['file_path'] = match.group(1)
                        error_info['line_number'] = int(match.group(2))
                    elif error_type == 'javascript' and len(match.groups()) >= 3:
                        error_info['file_path'] = match.group(2)
                        error_info['line_number'] = int(match.group(3))
                    elif error_type == 'java' and len(match.groups()) >= 3:
                        error_info['file_path'] = match.group(2)
                        error_info['line_number'] = int(match.group(3))
                    elif error_type == 'generic':
                        # Generic patterns have different group structures
                        # Pattern 1: ([^\s:]+\.(py|js|...)):(\d+): - groups: 1=file, 2=ext, 3=line
                        # Pattern 2: ([^\s:]+\.(py|js|...))\((\d+)\) - groups: 1=file, 2=ext, 3=line
                        # Pattern 3: ([^\s:]+/[^\s:]+):(\d+) - groups: 1=file, 2=line
                        # Pattern 4: ([^\s:]+\\[^\s:]+):(\d+) - groups: 1=file, 2=line
                        groups = match.groups()
                        if len(groups) >= 3:
                            # Pattern with file extension: group 1 is file, group 3 is line
                            error_info['file_path'] = match.group(1)
                            error_info['line_number'] = int(match.group(3))
                        elif len(groups) >= 2:
                            # Pattern without extension: group 1 is file, group 2 is line
                            error_info['file_path'] = match.group(1)
                            error_info['line_number'] = int(match.group(2))
                    
                    # Extract context (surrounding lines)
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    error_info['context'] = '\n'.join(lines[context_start:context_end])
                    
                    errors.append(error_info)
        
        # Also look for common error keywords
        error_keywords = ['ERROR', 'EXCEPTION', 'FAILED', 'CRITICAL', 'FATAL']
        for i, line in enumerate(lines):
            if any(keyword in line.upper() for keyword in error_keywords):
                # Check if we already captured this line
                if not any(e['line_in_log'] == i + 1 for e in errors):
                    errors.append({
                        'type': 'generic',
                        'line_in_log': i + 1,
                        'raw_line': line,
                        'context': '\n'.join(lines[max(0, i - 5):min(len(lines), i + 5)]),
                    })
        
        self.errors = errors
        return errors
    
    def get_file_references(self) -> List[Tuple[str, Optional[int]]]:
        """
        Extract unique file references from errors
        
        Returns:
            List of tuples (file_path, line_number)
        """
        if not self.errors:
            self.extract_errors()
        
        file_refs = []
        for error in self.errors:
            if 'file_path' in error:
                file_path = error['file_path']
                line_number = error.get('line_number')
                
                # Normalize file path (remove leading/trailing whitespace)
                file_path = file_path.strip()
                
                # Avoid duplicates
                if (file_path, line_number) not in file_refs:
                    file_refs.append((file_path, line_number))
        
        return file_refs
    
    def get_summary(self) -> Dict[str, any]:
        """Get a summary of errors found in the log"""
        if not self.errors:
            self.extract_errors()
        
        return {
            'total_errors': len(self.errors),
            'error_types': list(set(e['type'] for e in self.errors)),
            'file_references': len(self.get_file_references()),
            'log_file': self.file_path,
        }


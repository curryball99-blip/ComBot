"""
Ticket Data Extractor Service
============================

Handles extraction and cleaning of ticket data for analysis, dealing with:
- Inconsistent data formats
- Missing fields (L1/L2 Analysis, L3 Analysis, etc.)
- Noisy text with encoding issues
- Multiple potential sources for description text
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class TicketDataExtractor:
    """Extracts and cleans ticket data for analysis"""
    
    def __init__(self):
        # Common noise patterns to clean
        self.noise_patterns = [
            (r'-n-n', '\n'),  # Fix line breaks
            (r'-n', '\n'),    # Fix line breaks  
            (r'\\n', '\n'),   # Fix escaped newlines
            (r'\n+', '\n'),   # Multiple newlines to single
            (r'•_', '• '),    # Fix bullet points
            (r'_-n', '\n'),   # More line break issues
        ]
        
        # Fields that might contain description-like content
        self.description_fields = [
            'description',
            'l1_l2_analysis', 
            'l1_analysis',
            'l2_analysis',
            'initial_analysis',
            'summary'
        ]
        
        # Analysis fields in order of preference
        self.analysis_fields = [
            'l3_engineer_analysis',
            'l3_analysis', 
            'l1_l2_analysis',
            'l2_analysis',
            'l1_analysis',
            'initial_analysis'
        ]

    def extract_ticket_content(self, ticket_details: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract and clean the main content fields from a ticket.
        
        Returns:
            Dict with keys: 'description', 'analysis', 'summary', 'clean_text'
        """
        try:
            # Extract basic fields
            summary = self._clean_text(ticket_details.get('summary', ''))
            
            # Extract description - try multiple sources
            description = self._extract_best_description(ticket_details)
            
            # Extract analysis - try multiple sources  
            analysis = self._extract_best_analysis(ticket_details)
            
            # Create combined clean text for analysis
            clean_parts = []
            if summary:
                clean_parts.append(f"Summary: {summary}")
            if description:
                clean_parts.append(f"Description: {description}")
            if analysis:
                clean_parts.append(f"Technical Analysis: {analysis}")
                
            clean_text = "\n\n".join(clean_parts)
            
            return {
                'summary': summary,
                'description': description, 
                'analysis': analysis,
                'clean_text': clean_text,
                'has_analysis': bool(analysis.strip()),
                'has_description': bool(description.strip())
            }
            
        except Exception as e:
            logger.error(f"Error extracting ticket content: {e}")
            # Return minimal safe content
            return {
                'summary': ticket_details.get('summary', ''),
                'description': str(ticket_details.get('description', '')),
                'analysis': '',
                'clean_text': ticket_details.get('summary', '') + '\n' + str(ticket_details.get('description', '')),
                'has_analysis': False,
                'has_description': bool(ticket_details.get('description'))
            }

    def _extract_best_description(self, ticket_details: Dict[str, Any]) -> str:
        """Extract the best available description from multiple potential sources"""
        
        # Try custom fields first (often has the real content)
        custom_fields = ticket_details.get('custom_fields', {}) or {}
        
        # Check all potential description sources
        candidates = []
        
        # 1. Primary description field
        desc = ticket_details.get('description', '')
        if desc and len(str(desc).strip()) > 10:
            candidates.append(('primary_description', str(desc)))
            
        # 2. Custom fields that might contain description
        for field in self.description_fields:
            value = custom_fields.get(field, '')
            if value and len(str(value).strip()) > 10:
                candidates.append((field, str(value)))
                
        # 3. Comments (sometimes contain the real description)
        comments = ticket_details.get('comments', [])
        if comments:
            # Get first substantial comment
            for comment in comments[:3]:  # Check first 3 comments
                body = comment.get('body', '')
                if body and len(str(body).strip()) > 20:
                    candidates.append(('comment_description', str(body)))
                    break
        
        # Choose the best candidate (longest substantive content)
        if candidates:
            # Filter out very short or clearly non-descriptive content
            valid_candidates = []
            for source, content in candidates:
                clean_content = self._clean_text(content)
                # Skip if too short or looks like metadata
                if (len(clean_content) > 15 and 
                    not self._looks_like_metadata(clean_content)):
                    valid_candidates.append((source, clean_content, len(clean_content)))
            
            if valid_candidates:
                # Sort by length and take the longest substantive description
                valid_candidates.sort(key=lambda x: x[2], reverse=True)
                return valid_candidates[0][1]
        
        # Fallback to summary if no good description found
        return self._clean_text(ticket_details.get('summary', ''))

    def _extract_best_analysis(self, ticket_details: Dict[str, Any]) -> str:
        """Extract the best available technical analysis"""
        
        custom_fields = ticket_details.get('custom_fields', {}) or {}
        
        # Try analysis fields in order of preference
        for field in self.analysis_fields:
            value = custom_fields.get(field, '')
            if value and len(str(value).strip()) > 10:
                clean_value = self._clean_text(str(value))
                # Make sure it's not just repeating the description
                if not self._is_duplicate_content(clean_value, ticket_details.get('description', '')):
                    return clean_value
                    
        return ''

    def _clean_text(self, text: str) -> str:
        """Clean text from common noise and formatting issues"""
        if not text:
            return ''
            
        text = str(text)
        
        # Apply noise cleaning patterns
        for pattern, replacement in self.noise_patterns:
            text = re.sub(pattern, replacement, text)
            
        # Additional cleaning
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines to single
        text = text.strip()
        
        # Remove common prefixes that add noise
        prefixes_to_remove = [
            'Helix Ticket No -',
            'Initial_Analysis_&_Outcome_By_GCS_Team -',
            'Dear @',
            'Good Day..!!',
        ]
        
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                # Find the end of this metadata line and remove it
                lines = text.split('\n')
                if lines:
                    # Skip first line if it starts with metadata
                    remaining_lines = []
                    skip_first = True
                    for line in lines:
                        if skip_first and any(line.strip().startswith(p) for p in prefixes_to_remove):
                            skip_first = False
                            continue
                        remaining_lines.append(line)
                    text = '\n'.join(remaining_lines).strip()
                break
        
        return text

    def _looks_like_metadata(self, content: str) -> bool:
        """Check if content looks like metadata rather than description"""
        content_lower = content.lower()
        
        # Metadata indicators
        metadata_indicators = [
            'helix ticket no',
            'ticket creation time', 
            'company -',
            'country -',
            'product name -',
            'environment -',
            'owner(hw/os/db/api)',
            'numbers_of_user_impacted',
            'any_recent_changes'
        ]
        
        # If it contains multiple metadata indicators, it's probably metadata
        indicator_count = sum(1 for indicator in metadata_indicators if indicator in content_lower)
        return indicator_count >= 2

    def _is_duplicate_content(self, text1: str, text2: str) -> bool:
        """Check if two texts are substantially the same (avoiding duplicates)"""
        if not text1 or not text2:
            return False
            
        # Simple similarity check - if 80% of words overlap, consider duplicate
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
            
        overlap = len(words1 & words2)
        smaller_set = min(len(words1), len(words2))
        
        return (overlap / smaller_set) > 0.8

    def get_ticket_context_for_analysis(self, ticket_details: Dict[str, Any]) -> str:
        """
        Get a clean, formatted context string suitable for AI analysis.
        This is the main method to use for preparing ticket data for the LLM.
        """
        extracted = self.extract_ticket_content(ticket_details)
        
        # Build structured context
        context_parts = []
        
        # Always include basic info
        context_parts.append(f"Ticket: {ticket_details.get('key', 'Unknown')}")
        context_parts.append(f"Status: {ticket_details.get('status', 'Unknown')}")
        context_parts.append(f"Priority: {ticket_details.get('priority', 'Unknown')}")
        context_parts.append(f"Assignee: {ticket_details.get('assignee', 'Unassigned')}")
        
        # Add main content
        if extracted['summary']:
            context_parts.append(f"\nSummary:\n{extracted['summary']}")
            
        if extracted['description']:
            context_parts.append(f"\nProblem Description:\n{extracted['description']}")
            
        if extracted['analysis']:
            context_parts.append(f"\nExisting Technical Analysis:\n{extracted['analysis']}")
        
        # Add metadata about data quality
        data_quality_notes = []
        if not extracted['has_description']:
            data_quality_notes.append("⚠️ Limited problem description available")
        if not extracted['has_analysis']:
            data_quality_notes.append("⚠️ No technical analysis available yet")
            
        if data_quality_notes:
            context_parts.append(f"\nData Quality Notes:\n" + "\n".join(data_quality_notes))
        
        return "\n".join(context_parts)


# Singleton instance
ticket_data_extractor = TicketDataExtractor()
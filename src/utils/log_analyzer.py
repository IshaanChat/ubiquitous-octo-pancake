"""Log analysis and aggregation utilities."""
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class LogStats:
    """Statistics about log entries."""
    total_entries: int = 0
    error_count: int = 0
    warning_count: int = 0
    unique_endpoints: int = 0
    avg_response_time: float = 0.0
    endpoints: Dict[str, int] = None  # Endpoint -> count
    status_codes: Dict[str, int] = None  # Status code -> count
    error_types: Dict[str, int] = None  # Error type -> count

class LogAnalyzer:
    """Analyzes log files for patterns and statistics."""
    
    def __init__(self, log_path: str):
        """Initialize the analyzer.
        
        Args:
            log_path: Path to log file
        """
        self.log_path = Path(log_path)
        self.logger = logging.getLogger(__name__)
        
        # Patterns for log analysis
        self.endpoint_pattern = re.compile(r'(?:GET|POST|PUT|DELETE|PATCH) ([^ ]+)')
        self.status_pattern = re.compile(r'status (\d{3})')
        self.time_pattern = re.compile(r'completed in (\d+\.\d+)s')
        self.error_pattern = re.compile(r'Error: (.+?) -')

    def analyze_timeframe(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> LogStats:
        """Analyze logs within a timeframe.
        
        Args:
            start_time: Start of analysis period
            end_time: End of analysis period
        
        Returns:
            Statistics about the logs
        """
        stats = LogStats()
        stats.endpoints = defaultdict(int)
        stats.status_codes = defaultdict(int)
        stats.error_types = defaultdict(int)
        
        total_time = 0.0
        response_count = 0
        
        try:
            with self.log_path.open('r') as f:
                for line in f:
                    try:
                        # Parse timestamp
                        timestamp_str = line.split(' - ')[0]
                        entry_time = datetime.strptime(
                            timestamp_str, 
                            '%Y-%m-%d %H:%M:%S,%f'
                        )
                        
                        # Check timeframe
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue
                        
                        stats.total_entries += 1
                        
                        # Check log level
                        if "ERROR" in line:
                            stats.error_count += 1
                            # Extract error type
                            if error_match := self.error_pattern.search(line):
                                error_type = error_match.group(1)
                                stats.error_types[error_type] += 1
                        elif "WARNING" in line:
                            stats.warning_count += 1
                        
                        # Extract endpoint
                        if endpoint_match := self.endpoint_pattern.search(line):
                            endpoint = endpoint_match.group(1)
                            stats.endpoints[endpoint] += 1
                        
                        # Extract status code
                        if status_match := self.status_pattern.search(line):
                            status = status_match.group(1)
                            stats.status_codes[status] += 1
                        
                        # Extract response time
                        if time_match := self.time_pattern.search(line):
                            time = float(time_match.group(1))
                            total_time += time
                            response_count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"Error parsing log line: {e}")
                        continue
            
            # Calculate averages and counts
            stats.unique_endpoints = len(stats.endpoints)
            if response_count > 0:
                stats.avg_response_time = total_time / response_count
            
            self.logger.info(
                f"Analyzed {stats.total_entries} log entries:\n"
                f"- Errors: {stats.error_count}\n"
                f"- Warnings: {stats.warning_count}\n"
                f"- Unique endpoints: {stats.unique_endpoints}\n"
                f"- Avg response time: {stats.avg_response_time:.2f}s"
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs: {e}")
            raise
    
    def get_error_summary(
        self, 
        hours: int = 24
    ) -> List[Tuple[str, str, int]]:
        """Get summary of errors in the last N hours.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            List of (timestamp, error_message, count) tuples
        """
        start_time = datetime.now() - timedelta(hours=hours)
        errors = defaultdict(list)
        
        try:
            with self.log_path.open('r') as f:
                for line in f:
                    if "ERROR" not in line:
                        continue
                        
                    try:
                        # Parse timestamp
                        timestamp_str = line.split(' - ')[0]
                        entry_time = datetime.strptime(
                            timestamp_str,
                            '%Y-%m-%d %H:%M:%S,%f'
                        )
                        
                        if entry_time < start_time:
                            continue
                        
                        # Extract error message
                        if error_match := self.error_pattern.search(line):
                            error_msg = error_match.group(1)
                            errors[error_msg].append(entry_time)
                            
                    except Exception as e:
                        self.logger.warning(f"Error parsing error line: {e}")
                        continue
            
            # Summarize errors
            summary = []
            for error_msg, timestamps in errors.items():
                count = len(timestamps)
                latest = max(timestamps)
                summary.append((latest.isoformat(), error_msg, count))
            
            # Sort by count and timestamp
            summary.sort(key=lambda x: (-x[2], x[0]))
            
            self.logger.info(
                f"Found {len(summary)} unique errors in the last {hours} hours"
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error summarizing errors: {e}")
            raise
    
    def export_stats(
        self,
        stats: LogStats,
        output_file: str
    ) -> None:
        """Export statistics to JSON file.
        
        Args:
            stats: Statistics to export
            output_file: Path to output JSON file
        """
        try:
            # Convert defaultdict to dict for JSON serialization
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "total_entries": stats.total_entries,
                "error_count": stats.error_count,
                "warning_count": stats.warning_count,
                "unique_endpoints": stats.unique_endpoints,
                "avg_response_time": stats.avg_response_time,
                "endpoints": dict(stats.endpoints),
                "status_codes": dict(stats.status_codes),
                "error_types": dict(stats.error_types)
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            self.logger.info(f"Exported statistics to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error exporting statistics: {e}")
            raise
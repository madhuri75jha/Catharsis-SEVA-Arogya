"""CloudWatch Service for querying and displaying application logs"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from aws_services.base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class CloudWatchService(BaseAWSClient):
    """Service for querying CloudWatch logs"""
    
    def __init__(self, log_group_name: str, region: str):
        """
        Initialize CloudWatchService
        
        Args:
            log_group_name: CloudWatch log group name
            region: AWS region
        """
        super().__init__('logs', region)
        self.log_group_name = log_group_name
        logger.info(f"CloudWatch service initialized for log group: {log_group_name}")
    
    def query_logs(self, start_time: datetime, end_time: datetime, 
                   filter_pattern: Optional[str] = None, 
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query CloudWatch logs with date range and optional filter
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            filter_pattern: CloudWatch filter pattern (optional)
            limit: Maximum number of log entries to return
            
        Returns:
            List of log entry dictionaries
        """
        try:
            # Convert datetime to milliseconds timestamp
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            # Build filter log events parameters
            params = {
                'logGroupName': self.log_group_name,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': limit
            }
            
            if filter_pattern:
                params['filterPattern'] = filter_pattern
            
            # Query logs
            response = self.client.filter_log_events(**params)
            
            # Format log entries
            log_entries = []
            for event in response.get('events', []):
                log_entries.append(self.format_log_entry(event))
            
            logger.info(f"Retrieved {len(log_entries)} log entries")
            return log_entries
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to query CloudWatch logs: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying logs: {str(e)}")
            raise
    
    def get_log_events(self, next_token: Optional[str] = None, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      filter_pattern: Optional[str] = None,
                      limit: int = 100) -> Dict[str, Any]:
        """
        Get log events with pagination support
        
        Args:
            next_token: Pagination token from previous request
            start_time: Start of time range
            end_time: End of time range
            filter_pattern: CloudWatch filter pattern
            limit: Maximum number of entries
            
        Returns:
            Dictionary with events and next_token
        """
        try:
            params = {
                'logGroupName': self.log_group_name,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            if filter_pattern:
                params['filterPattern'] = filter_pattern
            if next_token:
                params['nextToken'] = next_token
            
            response = self.client.filter_log_events(**params)
            
            # Format events
            events = [self.format_log_entry(event) for event in response.get('events', [])]
            
            return {
                'events': events,
                'next_token': response.get('nextToken'),
                'has_more': 'nextToken' in response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to get log events: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting log events: {str(e)}")
            raise
    
    def format_log_entry(self, log_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format log entry for UI display
        
        Args:
            log_event: Raw CloudWatch log event
            
        Returns:
            Formatted log entry dictionary
        """
        timestamp_ms = log_event.get('timestamp', 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
        
        message = log_event.get('message', '')
        
        # Try to extract log level from message
        level = 'INFO'
        if 'ERROR' in message.upper():
            level = 'ERROR'
        elif 'WARNING' in message.upper() or 'WARN' in message.upper():
            level = 'WARNING'
        elif 'DEBUG' in message.upper():
            level = 'DEBUG'
        
        return {
            'timestamp': timestamp.isoformat(),
            'message': message,
            'level': level,
            'log_stream': log_event.get('logStreamName', ''),
            'event_id': log_event.get('eventId', '')
        }
    
    def search_logs(self, search_text: str, start_time: datetime, 
                   end_time: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search logs for text within date range
        
        Args:
            search_text: Text to search for
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of entries
            
        Returns:
            List of matching log entries
        """
        # Use CloudWatch filter pattern for text search
        filter_pattern = f'"{search_text}"' if search_text else None
        
        return self.query_logs(start_time, end_time, filter_pattern, limit)
    
    def get_log_streams(self) -> List[str]:
        """
        Get list of log streams in the log group
        
        Returns:
            List of log stream names
        """
        try:
            response = self.client.describe_log_streams(
                logGroupName=self.log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=50
            )
            
            streams = [stream['logStreamName'] for stream in response.get('logStreams', [])]
            return streams
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to get log streams: {error_code}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting log streams: {str(e)}")
            return []

"""
Base telephony provider interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers"""
    
    @abstractmethod
    async def make_call(
        self,
        to_number: str,
        from_number: Optional[str] = None,
        webhook_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Initiate an outbound call
        
        Args:
            to_number: Destination phone number
            from_number: Originating phone number
            webhook_url: URL for call events
            **kwargs: Provider-specific options
            
        Returns:
            Call ID from the provider
        """
        pass
    
    @abstractmethod
    async def end_call(self, call_id: str) -> bool:
        """
        End an active call
        
        Args:
            call_id: Provider's call ID
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get call status and details
        
        Args:
            call_id: Provider's call ID
            
        Returns:
            Call status information
        """
        pass
    
    @abstractmethod
    async def send_sms(
        self,
        to_number: str,
        from_number: str,
        message: str,
        **kwargs
    ) -> str:
        """
        Send SMS message
        
        Args:
            to_number: Destination phone number
            from_number: Originating phone number
            message: SMS content
            **kwargs: Provider-specific options
            
        Returns:
            Message ID from the provider
        """
        pass
    
    @abstractmethod
    async def transfer_call(
        self,
        call_id: str,
        to_number: str,
        **kwargs
    ) -> bool:
        """
        Transfer an active call
        
        Args:
            call_id: Current call ID
            to_number: Transfer destination
            **kwargs: Provider-specific options
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        **kwargs
    ) -> bool:
        """
        Play audio file in call
        
        Args:
            call_id: Active call ID
            audio_url: URL of audio file
            **kwargs: Provider-specific options
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def start_recording(self, call_id: str, **kwargs) -> str:
        """
        Start call recording
        
        Args:
            call_id: Active call ID
            **kwargs: Provider-specific options
            
        Returns:
            Recording ID
        """
        pass
    
    @abstractmethod
    async def stop_recording(self, call_id: str, recording_id: str) -> bool:
        """
        Stop call recording
        
        Args:
            call_id: Active call ID
            recording_id: Recording ID to stop
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def get_recording(self, recording_id: str) -> Dict[str, Any]:
        """
        Get recording details and URL
        
        Args:
            recording_id: Recording ID
            
        Returns:
            Recording information including download URL
        """
        pass
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Validation status
        """
        # Basic E.164 format validation
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone_number.replace(' ', '').replace('-', '')))
    
    def format_phone_number(self, phone_number: str, country_code: str = "+1") -> str:
        """
        Format phone number to E.164
        
        Args:
            phone_number: Phone number to format
            country_code: Default country code
            
        Returns:
            Formatted phone number
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present
        if not phone_number.startswith('+'):
            if len(digits) == 10:  # US number without country code
                return f"{country_code}{digits}"
            elif len(digits) == 11 and digits[0] == '1':  # US number with 1
                return f"+{digits}"
        
        return f"+{digits}" if not phone_number.startswith('+') else phone_number

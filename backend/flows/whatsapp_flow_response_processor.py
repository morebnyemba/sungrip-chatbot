"""
Service for processing WhatsApp Flow responses.

Following conventions from morebnyemba/Kalai-Safaris repo.
Handles the conversion of flow response data into flow session context.
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from .models import WhatsAppFlow, WhatsAppFlowResponse, FlowSession
from conversations.models import Contact

logger = logging.getLogger(__name__)


class WhatsAppFlowResponseProcessor:
    """
    Processes WhatsApp Flow responses and updates flow session context.
    """
    
    @staticmethod
    @transaction.atomic
    def process_response(
        whatsapp_flow: WhatsAppFlow, 
        contact: Contact, 
        response_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Processes WhatsApp flow response and updates the contact's flow session context.
        
        This method:
        1. Saves the WhatsAppFlowResponse for audit/history
        2. Updates the active FlowSession with the response data
        3. Sets a flag to trigger automatic transition in the flow
        
        Args:
            whatsapp_flow: The WhatsAppFlow instance
            contact: The contact who submitted the response
            response_data: The response payload from Meta
            
        Returns:
            Dict with status and notes, or None if failed
        """
        try:
            # Save the flow response for audit/history
            flow_response = WhatsAppFlowResponse.objects.create(
                whatsapp_flow=whatsapp_flow,
                contact=contact,
                flow_token=response_data.get('flow_token', ''),
                response_data=response_data,
                is_processed=True,
                processed_at=timezone.now()
            )
            logger.info(
                f"Saved WhatsAppFlowResponse {flow_response.id} for contact {contact.phone_number} "
                f"and flow {whatsapp_flow.name}"
            )

            # Update the flow session for the contact (if in a flow)
            flow_session = FlowSession.objects.select_for_update().filter(
                contact=contact,
                status='active'
            ).first()
            
            if not flow_session:
                logger.warning(
                    f"No active flow session for contact {contact.phone_number} "
                    f"when processing WhatsApp flow response"
                )
                return {
                    "success": False, 
                    "notes": "No active flow session for contact."
                }
            
            # Merge WhatsApp flow data into the flow context
            context = flow_session.context_data or {}
            wa_data = response_data.get('data', response_data)
            
            # Merge at top level for easy access in transitions and templates
            context.update(wa_data)
            
            # Also keep under a subkey for backward compatibility and debugging
            context['whatsapp_flow_data'] = wa_data
            
            # Set the flag for transition condition - this is critical for automatic transition
            context['whatsapp_flow_response_received'] = True
            
            # Update the flow session with the new context
            flow_session.context_data = context
            flow_session.updated_at = timezone.now()
            flow_session.save(update_fields=["context_data", "updated_at"])
            
            logger.info(
                f"Successfully updated flow session {flow_session.id} for contact {contact.phone_number} "
                f"with WhatsApp flow data. Set whatsapp_flow_response_received=True. "
                f"Current step: {flow_session.current_step.name if flow_session.current_step else 'None'}"
            )
            
            # Note: Flow continuation will be triggered asynchronously by the calling code
            # via process_flow_continuation_task to ensure reliable transaction handling.
            # This matches hanna's pattern where the processor only updates context.
            
            return {
                "success": True, 
                "notes": f"Flow session {flow_session.id} updated with WhatsApp flow data."
            }
            
        except Exception as e:
            logger.error(
                f"Error processing WhatsApp flow response for contact {contact.phone_number}: {e}", 
                exc_info=True
            )
            # Transaction will be rolled back automatically due to @transaction.atomic
            return None
    
    @staticmethod
    def get_response_by_token(flow_token: str) -> Optional[WhatsAppFlowResponse]:
        """
        Retrieves a WhatsAppFlowResponse by flow token.
        
        Args:
            flow_token: The flow token to search for
            
        Returns:
            WhatsAppFlowResponse instance or None if not found
        """
        try:
            return WhatsAppFlowResponse.objects.get(flow_token=flow_token)
        except WhatsAppFlowResponse.DoesNotExist:
            logger.warning(f"No WhatsAppFlowResponse found for token: {flow_token}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving WhatsAppFlowResponse by token: {e}", exc_info=True)
            return None
    
    @staticmethod
    def mark_response_processed(
        response: WhatsAppFlowResponse, 
        notes: str = None
    ) -> bool:
        """
        Marks a WhatsAppFlowResponse as processed.
        
        Args:
            response: The WhatsAppFlowResponse instance
            notes: Optional processing notes
            
        Returns:
            bool: True if successful
        """
        try:
            response.is_processed = True
            response.processed_at = timezone.now()
            if notes:
                response.processing_notes = notes
            response.save()
            
            logger.info(f"Marked WhatsAppFlowResponse {response.id} as processed")
            return True
            
        except Exception as e:
            logger.error(f"Error marking response as processed: {e}", exc_info=True)
            return False

"""
Conversational flows models for WhatsApp chatbot

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm repos.
Supports building complex conversational flows with steps and transitions.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class Flow(models.Model):
    """
    Represents a complete conversational flow for the solar chatbot.
    
    Examples: Customer inquiry flow, Quote request flow, Installation scheduling flow
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique name for this flow (used as an identifier)."
    )
    friendly_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="A user-friendly name for display purposes."
    )
    description = models.TextField(
        blank=True, 
        null=True,
        help_text="A brief description of what this flow does."
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Is this flow currently active and can be triggered?"
    )
    trigger_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of keywords/phrases that can trigger this flow "
            "(e.g., [\"solar panel\", \"quote\", \"installation\"]). Case-insensitive match."
        )
    )
    trigger_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Configuration for advanced triggers, e.g., regex for data extraction."
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.friendly_name or self.name} ({'Active' if self.is_active else 'Inactive'})"

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.trigger_keywords, list):
            raise ValidationError({
                'trigger_keywords': _("Trigger keywords must be a list.")
            })
        if not all(isinstance(keyword, str) for keyword in self.trigger_keywords):
            raise ValidationError({
                'trigger_keywords': _("All items in trigger_keywords must be strings.")
            })

    def save(self, *args, **kwargs) -> None:
        if not self.friendly_name:
            self.friendly_name = self.name.replace('_', ' ').replace('-', ' ').title()
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        verbose_name = 'Conversational Flow'
        verbose_name_plural = 'Conversational Flows'


class FlowStep(models.Model):
    """
    Represents a single step or node within a Flow.
    """
    STEP_TYPE_CHOICES = [
        ('send_message', _('Send Message')),
        ('question', _('Ask Question')),
        ('condition', _('Conditional Branch')),
        ('action', _('Perform Action')),
        ('wait_for_reply', _('Wait for Reply')),
        ('end_flow', _('End Flow')),
        ('start_flow_node', _('Start Flow Node')),
        ('human_handover', _('Handover to Human Agent')),
        ('switch_flow', _('Switch to Another Flow')),
    ]

    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='steps')
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name for this step (e.g., 'Welcome Message', 'Ask System Size')."
    )
    step_type = models.CharField(max_length=50, choices=STEP_TYPE_CHOICES)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for this step, structure depends on step_type."
    )
    is_entry_point = models.BooleanField(
        default=False,
        help_text="Is this the first step of the flow? Only one step per flow should be an entry point."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.flow.name} - {self.name} ({self.get_step_type_display()})"

    def clean(self) -> None:
        super().clean()
        # Ensure only one entry point per flow
        if self.is_entry_point:
            query = FlowStep.objects.filter(flow=self.flow, is_entry_point=True)
            if self.pk:
                query = query.exclude(pk=self.pk)
            if query.exists():
                raise ValidationError({
                    'is_entry_point': _(f"Flow '{self.flow.name}' already has an entry point. Only one is allowed.")
                })

        if not isinstance(self.config, dict):
            raise ValidationError({'config': _("Config must be a valid JSON object (dictionary).")})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['flow', 'created_at']
        unique_together = [['flow', 'name']]
        verbose_name = 'Flow Step'
        verbose_name_plural = 'Flow Steps'


class FlowTransition(models.Model):
    """
    Defines a transition from one FlowStep to another based on conditions.
    """
    current_step = models.ForeignKey(
        FlowStep,
        on_delete=models.CASCADE,
        related_name='outgoing_transitions'
    )
    next_step = models.ForeignKey(
        FlowStep,
        on_delete=models.CASCADE,
        related_name='incoming_transitions',
        help_text="The step to transition to if conditions are met."
    )
    condition_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for the condition that triggers this transition."
    )
    priority = models.IntegerField(
        default=0,
        help_text="Order of evaluation for transitions from the same step (lower numbers evaluated first)."
    )

    def __str__(self) -> str:
        return (f"From '{self.current_step.name}' to '{self.next_step.name}' "
                f"(Prio: {self.priority})")

    def clean(self) -> None:
        super().clean()
        if self.current_step and self.next_step:
            if self.current_step.flow_id != self.next_step.flow_id:
                raise ValidationError(
                    _("The current_step and next_step must belong to the same flow.")
                )

        if not isinstance(self.condition_config, dict):
            raise ValidationError({'condition_config': _("Condition config must be a valid JSON object.")})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['current_step', 'priority']
        verbose_name = 'Flow Transition'
        verbose_name_plural = 'Flow Transitions'


class FlowSession(models.Model):
    """
    Tracks an active conversational flow session for a contact.
    """
    contact = models.ForeignKey(
        'conversations.Contact',
        on_delete=models.CASCADE,
        related_name='flow_sessions'
    )
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE)
    current_step = models.ForeignKey(
        FlowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The current step the user is at in this flow."
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Session-specific data collected during the flow (e.g., user responses, calculated values)."
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('abandoned', 'Abandoned'),
            ('error', 'Error'),
        ],
        default='active'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.flow.name} ({self.status})"

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Flow Session'
        verbose_name_plural = 'Flow Sessions'

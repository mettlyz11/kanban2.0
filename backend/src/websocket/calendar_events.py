"""
Calendar Real-time Events Module
Handles event changes, meeting reminders, and schedule updates
"""
from flask_socketio import emit, join_room, leave_room
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CalendarEventHandler:
    """Calendar Event Handler"""
    
    @staticmethod
    def register_events(socketio):
        """Register calendar-related events"""
        
        @socketio.on('calendar_subscribe')
        def handle_calendar_subscribe(data):
            """User subscribes to calendar updates"""
            user_id = data.get('user_id')
            if user_id:
                room = f'calendar:{user_id}'
                join_room(room)
                logger.info(f'User subscribed to calendar: {room}')
                emit('calendar_subscribed', {'status': 'success'})
        
        @socketio.on('calendar_unsubscribe')
        def handle_calendar_unsubscribe(data):
            """User unsubscribes from calendar"""
            user_id = data.get('user_id')
            if user_id:
                room = f'calendar:{user_id}'
                leave_room(room)
        
        @socketio.on('event_created')
        def handle_event_created(data):
            """New calendar event created"""
            event = data.get('event')
            attendees = event.get('attendees', [])
            
            logger.info(f'Calendar event created: {event.get("title")}')
            
            # Notify all attendees
            for attendee_id in attendees:
                room = f'calendar:{attendee_id}'
                emit('calendar_event_added', {
                    'event': event,
                    'created_by': data.get('user_id')
                }, room=room, broadcast=True)
        
        @socketio.on('event_updated')
        def handle_event_updated(data):
            """Calendar event updated"""
            event = data.get('event')
            attendees = event.get('attendees', [])
            changes = data.get('changes', {})
            
            logger.info(f'Calendar event updated: {event.get("title")}')
            
            # Notify all attendees about changes
            for attendee_id in attendees:
                room = f'calendar:{attendee_id}'
                emit('calendar_event_changed', {
                    'event_id': event.get('id'),
                    'title': event.get('title'),
                    'changes': changes,
                    'updated_by': data.get('user_id'),
                    'timestamp': datetime.now().isoformat()
                }, room=room, broadcast=True)
        
        @socketio.on('event_deleted')
        def handle_event_deleted(data):
            """Calendar event deleted"""
            event_id = data.get('event_id')
            title = data.get('title')
            attendees = data.get('attendees', [])
            
            logger.info(f'Calendar event deleted: {title}')
            
            for attendee_id in attendees:
                room = f'calendar:{attendee_id}'
                emit('calendar_event_removed', {
                    'event_id': event_id,
                    'title': title,
                    'deleted_by': data.get('user_id')
                }, room=room, broadcast=True)
        
        @socketio.on('meeting_reminder')
        def handle_meeting_reminder(data):
            """Meeting reminder triggered"""
            meeting_id = data.get('meeting_id')
            attendees = data.get('attendees', [])
            minutes_before = data.get('minutes_before', 15)
            
            logger.info(f'Meeting reminder: {meeting_id} in {minutes_before} minutes')
            
            for attendee_id in attendees:
                room = f'calendar:{attendee_id}'
                emit('meeting_alert', {
                    'meeting_id': meeting_id,
                    'title': data.get('title'),
                    'start_time': data.get('start_time'),
                    'minutes_before': minutes_before,
                    'location': data.get('location')
                }, room=room, broadcast=True)

# Helper functions for API integration
def emit_calendar_event_created(event, user_id):
    """Emit calendar event created from API"""
    attendees = event.get('attendees', [])
    for attendee_id in attendees:
        room = f'calendar:{attendee_id}'
        emit('calendar_event_added', {
            'event': event,
            'created_by': user_id
        }, room=room, broadcast=True)

def emit_calendar_event_updated(event, changes, user_id):
    """Emit calendar event updated from API"""
    attendees = event.get('attendees', [])
    for attendee_id in attendees:
        room = f'calendar:{attendee_id}'
        emit('calendar_event_changed', {
            'event_id': event.get('id'),
            'title': event.get('title'),
            'changes': changes,
            'updated_by': user_id,
            'timestamp': datetime.now().isoformat()
        }, room=room, broadcast=True)

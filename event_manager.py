class EventManager:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.listeners:
            self.listeners[event_type] = []

        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        callbacks = self.listeners.get(event_type, [])

        if callback in callbacks:
            callbacks.remove(callback)

    def emit(self, event_type, **data):
        event = {
            "type": event_type,
            **data,
        }

        for callback in self.listeners.get(event_type, [])[:]:
            callback(event)

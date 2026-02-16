from logging import Filter

class ActorMetadataFilter(Filter):
    """This adds the actor arg to the log if it was not provided at the log site"""
    def filter(self, record):
        if not hasattr(record, 'actor'):
            record.actor = 'internal' 
        return True
from math import floor

def simple_human_readable_duration(duration_seconds) -> str:
    """
    Return a human-readable text (str) for a given duration in seconds:
    hours, minutes & seconds elapsed
    """
    hours   = floor(duration_seconds // 3600)
    minutes = floor(duration_seconds % 3600 // 60)
    seconds = floor(duration_seconds % 60) if duration_seconds > 60 else round(duration_seconds % 60,3) # high precision only for small durations
    formatted_duration = ''
    if hours != 0:
        formatted_duration += '{}h '.format(hours)
    if minutes != 0 or hours != 0:
        formatted_duration += '{}m '.format(minutes)
    formatted_duration += '{}s'.format(seconds)
    return formatted_duration
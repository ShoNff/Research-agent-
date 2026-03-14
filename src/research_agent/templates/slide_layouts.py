"""PowerPoint slide layout constants."""

# Dimensions (16:9)
SLIDE_WIDTH_INCHES = 13.333
SLIDE_HEIGHT_INCHES = 7.5

# Font sizes (points)
TITLE_FONT_SIZE = 28
SUBTITLE_FONT_SIZE = 18
BODY_FONT_SIZE = 16
BULLET_FONT_SIZE = 14
CAPTION_FONT_SIZE = 10

# Color palette (RGB tuples)
COLORS = {
    "primary": (41, 65, 122),        # Dark blue
    "secondary": (70, 130, 180),     # Steel blue
    "accent": (218, 165, 32),        # Gold
    "text": (51, 51, 51),            # Dark gray
    "text_light": (119, 119, 119),   # Medium gray
    "light_bg": (245, 247, 250),     # Light gray-blue
    "white": (255, 255, 255),
    "established": (34, 139, 34),    # Green
    "reputable": (70, 130, 180),     # Blue
    "emerging": (218, 165, 32),      # Gold
    "opinion": (205, 92, 92),        # Red
}

# Layout types
LAYOUTS = {
    "title": {
        "title_top": 2.5,
        "title_left": 1.0,
        "title_width": 11.333,
        "title_height": 2.0,
    },
    "content": {
        "title_top": 0.3,
        "title_left": 0.5,
        "title_width": 12.333,
        "title_height": 1.0,
        "body_top": 1.5,
        "body_left": 0.5,
        "body_width": 12.333,
        "body_height": 5.5,
    },
    "two_column": {
        "title_top": 0.3,
        "title_left": 0.5,
        "title_width": 12.333,
        "title_height": 1.0,
        "left_top": 1.5,
        "left_left": 0.5,
        "left_width": 5.5,
        "left_height": 5.5,
        "right_top": 1.5,
        "right_left": 6.5,
        "right_width": 6.333,
        "right_height": 5.5,
    },
}

"""Enhanced UI System for SEGUNDA VITA Alpha Testing"""

class Colors:
    RESET = '\033[0m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_RED = '\033[91m'

class EnhancedUI:
    def __init__(self):
        self.enable_colors = True
        self.screen_width = 80
        
    def colorize(self, text, color):
        if self.enable_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
        
    def draw_box(self, title, content):
        lines = []
        width = 60
        lines.append(f"╭─ {title} " + "─" * (width - len(title) - 4) + "╮")
        for line in content:
            lines.append(f"│ {line:<{width-4}} │")
        lines.append("╰" + "─" * (width - 2) + "╯")
        return lines

enhanced_ui = EnhancedUI()

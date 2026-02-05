from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os

class AttendancePDF(FPDF):
    def __init__(self):
        # Landscape orientation (297mm wide)
        super().__init__(orientation='L', unit='mm', format='A4')
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.base_dir, "assets", "bcblogo.png")

    def generate_combined_report(self, day_name, clean_data):
        self.add_page()
        
        # Header
        self.set_font("Arial", 'B', 40)
        self.cell(0, 10, f"ATTENDANCE: {day_name}", ln=True, align='C')

        if os.path.exists(self.logo_path):
            self.image(self.logo_path, x=10, y=8, w=30)
            self.image(self.logo_path, x=257, y=8, w=30)
        
        total = len(clean_data)
        present_count = sum(1 for i in clean_data if i["status"] == "P")
        percent = (present_count / total * 100) if total > 0 else 0
        
        self.set_font("Arial", '', 12)
        header_stats = f"Total Strength: {total}  |  Present: {present_count}  |  Accountability: {percent:.1f}%"
        self.cell(0, 8, header_stats, ln=True, align='C')
        self.ln(5)

        # Store this Y position so the table and graph align at the same height
        start_y = self.get_y()

        # Left Side: Attendance Table
        self.set_xy(10, start_y + 30)
        # We narrowed the widths slightly to fit the left half (~140mm total)
        widths = [15, 15, 27, 27, 27, 27] 
        cols = ["MS", "Pres", "Excused", "Absent", "Uncon", "Late"]
        
        self.set_fill_color(200, 200, 200)
        self.set_font("Arial", 'B', 8)
        for i, col in enumerate(cols):
            self.cell(widths[i], 8, col, border=1, align='C', fill=True)
        self.ln()

        self.set_font("Arial", '', 8)
        for level in [1, 2, 3, 4]:
            level_items = [i for i in clean_data if str(i["ms"]) == str(level)]
            p_count = str(sum(1 for i in level_items if i["status"] == "P"))

            def format_cell(status_filter=None, late_only=False):
                if late_only:
                    names = [i["name"].split()[-1] for i in level_items if i["is_late"]]
                else:
                    names = [i["name"].split()[-1] for i in level_items if i["status"] == status_filter]
                if not names: return "0"
                return f"{len(names)} ({', '.join(names)})"

            # Render Row (Set X to 10 for each row to keep it on the left)
            self.set_x(10)
            self.cell(widths[0], 10, f"MS{level}", border=1, align='C')
            self.cell(widths[1], 10, p_count, border=1, align='C')
            # Truncating names to ensure they stay within the left column
            self.cell(widths[2], 10, format_cell(status_filter="E")[:25], border=1)
            self.cell(widths[3], 10, format_cell(status_filter="A")[:25], border=1)
            self.cell(widths[4], 10, format_cell(status_filter="UN")[:25], border=1)
            self.cell(widths[5], 10, format_cell(late_only=True)[:25], border=1)
            self.ln()

        # Right Side: Attendance Graph
        self.render_graph_to_page(clean_data, day_name, x_pos=155, y_pos=start_y + 30)

    def render_graph_to_page(self, clean_data, day_name, x_pos, y_pos):
        ms_levels = ["1", "2", "3", "4"]
        statuses = ["P", "A", "E"]
        colors = {"P": "#2ecc71", "A": "#e74c3c", "E": "#f1c40f"}
        labels = {"P": "Present", "A": "Absent", "E": "Excused"}
        
        counts = {status: [0, 0, 0, 0] for status in statuses}
        for item in clean_data:
            if item["status"] in statuses:
                ms_idx = int(item["ms"]) - 1
                counts[item["status"]][ms_idx] += 1

        x = range(len(ms_levels))
        fig, ax = plt.subplots(figsize=(5, 3.5)) # Slightly smaller figure
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        bottom = [0] * len(ms_levels)

        for status in statuses:
            ax.bar(x, counts[status], 0.6, bottom=bottom, label=labels[status], color=colors[status])
            bottom = [b + c for b, c in zip(bottom, counts[status])]

        ax.set_title(f'Attendance Overview', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels([f"MS{m}" for m in ms_levels])
        ax.legend(fontsize=8)

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        img_buf.seek(0)
        
        # Place image on the right side
        self.image(img_buf, x=x_pos, y=y_pos, w=130)
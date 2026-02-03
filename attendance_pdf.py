from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io

class AttendancePDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')

    def generate_report_page(self, day_name, clean_data):
        self.add_page()
        
        # Header
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, f"ATTENDANCE: {day_name}", ln=True, align='C')
        
        total = len(clean_data)
        present_count = sum(1 for i in clean_data if i["status"] == "P")
        percent = (present_count / total * 100) if total > 0 else 0
        
        self.set_font("Arial", '', 12)
        self.cell(0, 10, f"Total Strength: {total}  |  Present: {present_count}  |  Accountability: {percent:.1f}%", ln=True, align='C')
        self.ln(5)

        # Table Headers
        widths = [20, 20, 59, 59, 59, 59]
        cols = ["MSLVL", "Present", "Excused", "Unaccounted For", "Uncontracted", "Late"]
        
        self.set_fill_color(200, 200, 200)
        self.set_font("Arial", 'B', 10)
        for i, col in enumerate(cols):
            self.cell(widths[i], 10, col, border=1, align='C', fill=True)
        self.ln()

        # Data Rows
        self.set_font("Arial", '', 9)
        for level in [1, 2, 3, 4]:
            level_items = [i for i in clean_data if str(i["ms"]) == str(level)]
            
            p_count = str(sum(1 for i in level_items if i["status"] == "P"))
            
            # Formatter
            def format_cell(status_filter=None, late_only=False):
                if late_only:
                    names = [i["name"] for i in level_items if i["is_late"]]
                else:
                    names = [i["name"] for i in level_items if i["status"] == status_filter]
                
                if not names: return "0"
                return f"{len(names)} ({', '.join(names)})"

            e_str = format_cell(status_filter="E")
            a_str = format_cell(status_filter="A")
            un_str = format_cell(status_filter="UN")
            l_str = format_cell(late_only=True)

            # We use multi_cell to handle long lists of names within the table
            x_start = self.get_x()
            y_start = self.get_y()
            row_height = 10 # Minimum height

            # MS Level and Present count
            self.cell(widths[0], row_height, f"MS{level}", border=1, align='C')
            self.cell(widths[1], row_height, p_count, border=1, align='C')
            
            # Remaining data cells (Truncated here for simplicity, or use multi_cell for full lists)
            self.cell(widths[2], row_height, e_str[:45], border=1)
            self.cell(widths[3], row_height, a_str[:45], border=1)
            self.cell(widths[4], row_height, un_str[:45], border=1)
            self.cell(widths[5], row_height, l_str[:45], border=1)
            self.ln()

    def generate_graph(self, clean_data, day_name):
    # Prepare Data (Omit UN)
        ms_levels = ["1", "2", "3", "4"]
        statuses = ["P", "A", "E"]
        colors = {"P": "green", "A": "red", "E": "orange"}
        labels = {"P": "Present", "A": "Absent", "E": "Excused"}
        
        # Filter data to exclude 'UN' and group counts
        counts = {status: [0, 0, 0, 0] for status in statuses}
        for item in clean_data:
            if item["status"] in statuses:
                ms_idx = int(item["ms"]) - 1
                counts[item["status"]][ms_idx] += 1

        # Create Plot
        x = range(len(ms_levels))
        width = 0.5  # Increased width for better visibility in stacked format
        fig, ax = plt.subplots(figsize=(6, 4))

        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        # Initialize the bottom of the stacks at zero
        bottom = [0] * len(ms_levels)

        for status in statuses:
            # Create the bar with the current 'bottom' offset
            ax.bar(x, counts[status], width, bottom=bottom, 
                label=labels[status], color=colors[status])
            
            # Update the 'bottom' for the next status in the stack
            bottom = [b + c for b, c in zip(bottom, counts[status])]

        max_height = max(bottom) if any(bottom) else 5
        ax.set_ylim(0, max_height * 1.2)

        ax.set_ylabel('Number of Cadets')
        ax.set_xlabel('MS Level')
        ax.set_title(f'{day_name} Attendance by MS class')
        ax.set_xticks(x)
        ax.set_xticklabels([f"MS{m}" for m in ms_levels])
        ax.legend()

        # Save to Buffer
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150)
        plt.close(fig)
        img_buf.seek(0)
        
        # Add to PDF
        self.add_page()
        # Centers the image on the landscape page
        self.image(img_buf, x=60, y=40, w=180)
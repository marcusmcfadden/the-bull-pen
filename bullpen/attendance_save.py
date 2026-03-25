import os
import io
import csv
from fpdf import FPDF
import matplotlib.pyplot as plt

class AttendancePDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.base_dir, "..", "assets", "bcblogo.png")
        self.logo_path = os.path.abspath(self.logo_path)
        self.reports_dir = os.path.join(self.base_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        self.names_col_idx = 3

    def wrap_to_width(self, text, col_width, padding=2):
        if text is None or str(text).strip() == "":
            return ["0"]
        words = str(text).split()
        lines = []
        cur = ""
        avail = max(col_width - padding, 1)
        for w in words:
            trial = (cur + " " + w).strip()
            if self.get_string_width(trial) <= avail:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines or ["0"]

    def generate_combined_report(self, day_name, clean_data):
        self.add_page()
        self.set_font("Arial", 'B', 40)
        self.cell(0, 20, f"ATTENDANCE: {day_name}", ln=True, align='C')

        if os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, x=10, y=8, w=30)
                self.image(self.logo_path, x=self.w - 40, y=8, w=30)
            except Exception:
                pass

        total = len(clean_data)
        present_count = sum(1 for i in clean_data if i.get("status") == "P")
        percent = (present_count / total * 100) if total > 0 else 0

        self.set_font("Arial", 'B', 12)
        header_stats = f"Total Strength: {total}  |  Present: {present_count}  |  Accountability: {percent:.1f}%"
        self.cell(0, 10, header_stats, ln=True, align='C')
        self.ln(5)

        left_margin = 10
        right_margin = 10
        spacing_between = 8
        graph_width = 90
        graph_height = 90
        page_inner_width = self.w - left_margin - right_margin

        left_col_width = page_inner_width - graph_width - spacing_between
        if left_col_width < 60:
            left_col_width = page_inner_width * 0.65
            graph_width = page_inner_width - left_col_width - spacing_between

        self.set_font("Arial", size=9)
        line_height = 6
        logical_col_widths = [15, 15, 27, 27, 27, 27]
        total_logical = sum(logical_col_widths)
        col_w_scaled = [(w / total_logical) * left_col_width for w in logical_col_widths]

        x_table = left_margin
        y_table = self.get_y()
        self.set_xy(x_table, y_table)

        headers = ("MS", "Present", "Excused", "Absent", "Uncon.", "Late")
        self.set_font("Arial", 'B', 9)
        for w, h in zip(col_w_scaled, headers):
            self.cell(w, line_height, h, border=1, ln=0, align='C')
        self.ln(line_height)
        self.set_font("Arial", size=9)

        for level in [1, 2, 3, 4]:
            level_items = [i for i in clean_data if str(i.get("ms")) == str(level)]
            p_count = str(sum(1 for i in level_items if i.get("status") == "P"))

            def get_status_str(status_filter=None, late_only=False):
                if late_only:
                    names = [i.get("name", "").split()[-1] for i in level_items if i.get("is_late")]
                else:
                    names = [i.get("name", "").split()[-1] for i in level_items if i.get("status") == status_filter]

                count = len(names)

                if count == 0:
                    return "0"

                return f"{count}: {', '.join(names)}"

            row_values = [
                f"MS{level}",
                p_count,
                get_status_str(status_filter="E"),
                get_status_str(status_filter="A"),
                get_status_str(status_filter="UN"),
                get_status_str(late_only=True)
            ]

            wrapped_lines = self.wrap_to_width(
                row_values[self.names_col_idx],
                col_w_scaled[self.names_col_idx]
            )

            n_lines = max(1, len(wrapped_lines))
            row_h = line_height * n_lines

            y_start = self.get_y()
            x = x_table

            for idx, (w, val) in enumerate(zip(col_w_scaled, row_values)):
                if idx == self.names_col_idx:
                    x += w
                    continue
                self.set_xy(x, y_start)
                self.cell(w, row_h, str(val), border=1, ln=0, align='LEFT')
                x += w

            x_names = x_table + sum(col_w_scaled[:self.names_col_idx])
            inner_pad = 1
            self.set_xy(x_names + inner_pad, y_start)
            self.multi_cell(
                col_w_scaled[self.names_col_idx] - 2 * inner_pad,
                line_height,
                "\n".join(wrapped_lines),
                border=0,
                align='LEFT'
            )
            self.rect(x_names, y_start, col_w_scaled[self.names_col_idx], row_h)
            self.set_xy(x_table, y_start + row_h)

        self.ln(10)

        graph_x = x_table + left_col_width + spacing_between
        graph_y = y_table
        try:
            self.render_graph_to_page(clean_data, graph_x, graph_y, w=graph_width, h=graph_height)
        except Exception:
            pass

    def render_graph_to_page(self, clean_data, x_pos, y_pos, w=90, h=90):
        ms_levels = ["1", "2", "3", "4"]
        statuses = ["P", "A", "E"]
        counts = {status: [0]*4 for status in statuses}

        for item in clean_data:
            st = item.get("status")
            if st in statuses:
                try:
                    ms_idx = max(0, min(3, int(item.get("ms", 1)) - 1))
                except Exception:
                    ms_idx = 0
                counts[st][ms_idx] += 1

        x = range(len(ms_levels))
        fig_w = max(1.0, w / 25.4)
        fig_h = max(0.8, h / 25.4)

        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        bottom = [0]*len(ms_levels)
        colors = {"P": "#2ecc71", "A": "#e74c3c", "E": "#f1c40f"}
        labels = {"P": "Present", "A": "Absent", "E": "Excused"}

        for status in statuses:
            ax.bar(x, counts[status], 0.6, bottom=bottom, label=labels[status], color=colors[status])
            bottom = [b + c for b, c in zip(bottom, counts[status])]

        ax.set_xticks(x)
        ax.set_xticklabels([f"MS{m}" for m in ms_levels], fontsize=8)
        ax.set_title('Attendance by MS Level', fontsize=9)
        ax.legend(fontsize=7, loc='upper right')

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        img_buf.seek(0)

        try:
            self.image(img_buf, x=x_pos, y=y_pos, w=w)
        except Exception:
            tmp_path = os.path.join(self.reports_dir, "tmp_graph.png")
            with open(tmp_path, "wb") as f:
                f.write(img_buf.getbuffer())
            self.image(tmp_path, x=x_pos, y=y_pos, w=w)
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def generate_squad_summary_page(self, squad_totals):
        self.add_page()

        self.set_font("Arial", 'B', 28)
        self.cell(0, 15, "ATTENDANCE BY SQUAD", ln=True, align='C')

        margin = 10
        top_offset = 30

        col_w = (self.w - 3 * margin) / 2
        row_h = (self.h - top_offset - 3 * margin) / 2

        positions = [
            ("1st Squad", margin, top_offset),
            ("2nd Squad", margin * 2 + col_w, top_offset),
            ("3rd Squad", margin, top_offset + row_h + margin),
            ("MS4", margin * 2 + col_w, top_offset + row_h + margin),
        ]

        for squad_name, x, y in positions:
            self.set_xy(x, y)

            self.set_font("Arial", 'B', 12)
            self.cell(col_w, 8, squad_name, border=1, ln=1)

            self.set_x(x)
            self.set_font("Arial", 'B', 9)
            self.cell(col_w * 0.5, 6, "Name", border=1)
            self.cell(col_w * 0.25, 6, "Absent", border=1)
            self.cell(col_w * 0.25, 6, "Late", border=1)
            self.ln()

            self.set_font("Arial", size=9)

            squad_data = squad_totals.get(squad_name, {})

            sorted_rows = sorted(
                squad_data.items(),
                key=lambda x: (-x[1]["absent"], -x[1]["late"])
            )

            for name, stats in sorted_rows:
                if stats["absent"] == 0 and stats["late"] == 0:
                    continue

                self.set_x(x)
                self.cell(col_w * 0.5, 6, name.split()[-1], border=1)
                self.cell(col_w * 0.25, 6, str(stats["absent"]), border=1)
                self.cell(col_w * 0.25, 6, str(stats["late"]), border=1)
                self.ln()

                if self.get_y() > y + row_h:
                    break

async def generate_csv(attendance_registry):
    if not attendance_registry:
        return

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name", "MS Level", "Squad", "School",
        "TUE PT Status", "TUE PT Late",
        "WED PT Status", "WED PT Late",
        "THU PT Status", "THU PT Late",
        "LAB Status", "LAB Late"
    ])

    day_map = {
        "TUEPT": "TUE PT", "TUE PT": "TUE PT", "TUE": "TUE PT",
        "WEDPT": "WED PT", "WED PT": "WED PT", "WED": "WED PT",
        "THUPT": "THU PT", "THU PT": "THU PT", "THU": "THU PT",
        "LAB": "LAB", "LAB PT": "LAB"
    }
    canonical_days = ["TUE PT", "WED PT", "THU PT", "LAB"]

    grouped = {}
    for item in attendance_registry:
        name = item.get("name", "").strip()
        if not name:
            continue

        ms = item.get("ms", "")
        squad = item.get("squad", "") or ""
        school = item.get("school", "") or ""

        raw_day = item.get("col", "")
        day = day_map.get(raw_day.strip(), raw_day.strip())

        status_ctrl = item.get("status")
        late_ctrl = item.get("late")

        try:
            status_val = status_ctrl.value if status_ctrl is not None else None
        except Exception:
            status_val = None

        try:
            late_bool = bool(late_ctrl.value) if late_ctrl is not None else False
        except Exception:
            late_bool = False

        status = status_val if status_val else "N/A"
        late = "Yes" if late_bool else "No"

        if name not in grouped:
            grouped[name] = {
                "ms": ms,
                "squad": squad,
                "school": school,
                "TUE PT": ("N/A", "No"),
                "WED PT": ("N/A", "No"),
                "THU PT": ("N/A", "No"),
                "LAB": ("N/A", "No"),
            }

        if day in canonical_days:
            grouped[name][day] = (status, late)

    def sort_key(item):
        name, data = item
        try:
            ms_key = int(data.get("ms")) if data.get("ms") not in (None, "") else 99
        except Exception:
            ms_key = 99
        return (ms_key, name.lower())

    for name, data in sorted(grouped.items(), key=sort_key):
        writer.writerow([
            name,
            data.get("ms", ""),
            data.get("squad", ""),
            data.get("school", ""),
            data["TUE PT"][0], data["TUE PT"][1],
            data["WED PT"][0], data["WED PT"][1],
            data["THU PT"][0], data["THU PT"][1],
            data["LAB"][0], data["LAB"][1],
        ])

    writer.writerow([])
    writer.writerow(["SQUAD SUMMARY"])
    writer.writerow(["Squad", "Name", "Unexcused Absences", "Unexcused Lates"])

    squad_summary = {}

    for item in attendance_registry:
        name = item.get("name", "")
        squad = item.get("squad", "")

        status_ctrl = item.get("status")
        late_ctrl = item.get("late")

        try:
            status_val = status_ctrl.value if status_ctrl else None
        except:
            status_val = None

        try:
            is_late = bool(late_ctrl.value) if late_ctrl else False
        except:
            is_late = False

        if squad not in squad_summary:
            squad_summary[squad] = {}

        if name not in squad_summary[squad]:
            squad_summary[squad][name] = {
                "absent": 0,
                "late": 0
            }

        if status_val == "A":
            squad_summary[squad][name]["absent"] += 1

        if is_late:
            squad_summary[squad][name]["late"] += 1

    # write it out
    for squad, cadets in squad_summary.items():
        for name, stats in sorted(
            cadets.items(),
            key=lambda x: (-x[1]["absent"], -x[1]["late"])
        ):
            writer.writerow([
                squad,
                name,
                stats["absent"],
                stats["late"]
            ])

    csv_text = output.getvalue()
    output.close()

    csv_bytes = csv_text.encode("utf-8")
    return csv_bytes
import flet as ft
from database import init_db, get_filtered_cadets, update_cadet, register_cadet, delete_cadet

def main(page: ft.Page):
    init_db()
    
    # Page Configuration
    page.title = "THE BULL PEN"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # State Management
    active_schools = set()
    active_squads = set()
    active_ms = set()
    sort_ascending = True

    # Logic Functions
    def update_roster(e=None):
        query = search_field.value if search_field.value else ""
        direction = "ASC" if sort_ascending else "DESC"
        cadets = get_filtered_cadets(query, list(active_schools), list(active_squads), list(active_ms), direction)
        
        roster_list.controls.clear()

        for cadet in cadets:
            c_id, c_name, c_ms, c_school, c_squad, c_tier = cadet
                
            school_color = "#012169" if c_school == "D" else "#8B2331"
                
            roster_list.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        leading=ft.CircleAvatar(content=ft.Text(c_name[0]), bgcolor=school_color),
                        title=ft.Text(c_name),
                        subtitle=ft.Text(f"MS{c_ms} | {c_squad}"),
                        trailing=ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            items=[
                                ft.PopupMenuItem(
                                    content=ft.Text("Edit"), 
                                    icon=ft.Icons.EDIT,
                                    on_click=lambda _, data=cadet: open_cadet_modal(data)
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Text("Delete"), 
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    on_click=lambda _, id=c_id, name=c_name: confirm_delete(id, name)
                                ),
                                ]
                            )
                        )
                    )
                )
        page.update()

    def open_cadet_modal(cadet_data=None):
        is_edit = cadet_data is not None
        
        full_name = cadet_data[1] if is_edit else ""
        name_parts = full_name.split(" ", 1)
        f_name_val = name_parts[0] if len(name_parts) > 0 else ""
        l_name_val = name_parts[1] if len(name_parts) > 1 else ""

        first_name = ft.TextField(label="First Name", value=f_name_val, expand=True)
        last_name = ft.TextField(label="Last Name", value=l_name_val, expand=True)
        
        school_dropdown = ft.Dropdown(
            label="School",
            value = cadet_data[3] if is_edit else "D",
            options=[ft.dropdown.Option("D", "Duke"), ft.dropdown.Option("N", "NCCU")],
            width=150
        )

        ms_level = ft.Dropdown(
            label="MS Level",
            value=str(cadet_data[2]) if is_edit else "1",
            options=[ft.dropdown.Option(str(i)) for i in range(1, 5)],
            width=100
        )
        
        squad_dropdown = ft.Dropdown(
            label="Squad",
            value=cadet_data[4] if is_edit else "1st Squad",
            expand=True,
            options=[
                ft.dropdown.Option("1st Squad"),
                ft.dropdown.Option("2nd Squad"),
                ft.dropdown.Option("3rd Squad"),
                ft.dropdown.Option("4th Squad"),
                ft.dropdown.Option("MS4")
            ]
        )

        def save_clicked(e):
            combined_name = f"{first_name.value} {last_name.value}".strip()
            if is_edit:
                update_cadet(cadet_data[0], combined_name, int(ms_level.value), 
                             school_dropdown.value, squad_dropdown.value, cadet_data[5])
            else:
                register_cadet(combined_name, int(ms_level.value), 
                               school_dropdown.value, squad_dropdown.value, 3, "password123")
            
            dialog.open = False
            update_roster()
            page.update()

        # 3. Build the UI Structure
        dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Cadet Profile"),
                    content=ft.Container(
                        width=600, height=250,
                        content=ft.Row([
                            ft.Column([
                                ft.CircleAvatar(
                                    content=ft.Icon(ft.Icons.PERSON, size=50),
                                    radius=60,
                                    bgcolor="#012169" if school_dropdown.value == "D" else "#8B2331"
                                ),
                                ft.Text("PHOTO", weight="bold", size=10)
                            ], horizontal_alignment="center", width=150),
                            ft.VerticalDivider(width=1, color="white24"),
                            ft.Column([
                                ft.Row([first_name, last_name]),
                                school_dropdown,
                                ft.Row([ms_level, squad_dropdown]),
                            ], expand=True, spacing=15)
                        ])
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _: [setattr(dialog, "open", False), page.update()]),
                        ft.Button("Save", bgcolor="#012169", color="white", on_click=save_clicked),
                    ],
                )

        # 4. Show the Dialog
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def confirm_delete(cadet_id, cadet_name):
            def finalize_delete(e):
                # 1. Execute the database logic
                delete_cadet(cadet_id)
                # 2. Close the specific dialog
                confirm_dialog.open = False 
                # 3. Refresh the UI
                update_roster()
                page.update()

            # Define the dialog
            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Confirm Deletion"),
                content=ft.Text(f"Are you sure you want to delete {cadet_name}? This action cannot be undone."),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: [setattr(confirm_dialog, "open", False), page.update()]),
                    ft.Button("Delete", bgcolor=ft.Colors.RED_700, color="white", on_click=finalize_delete),
                ],
            )
            page.overlay.append(confirm_dialog)
            confirm_dialog.open = True
            page.update()

    def toggle_sort(e):
        nonlocal sort_ascending
        sort_ascending = not sort_ascending
        sort_dir_btn.icon = ft.Icons.ARROW_UPWARD if sort_ascending else ft.Icons.ARROW_DOWNWARD
        sort_dir_btn.tooltip = "Sort Ascending" if sort_ascending else "Sort Descending"
        update_roster()

    def on_filter_change(e):
        val, category = e.control.label, e.control.data
        if category == "school":
            val_to_add = "D" if "Duke" in val else "N"
        elif category == "squad":
            val_to_add = f"{val} Squad" if val != "MS4" else val
        else:
            val_to_add = val

        target_set = {"school": active_schools, "squad": active_squads, "ms": active_ms}[category]
        if e.control.value:
            target_set.add(val_to_add)
        else:
            target_set.discard(val_to_add)
        update_roster()

    def toggle_filter_box(e):
        if page.width > 800:
            filter_sidebar.visible = not filter_sidebar.visible
        else:
            filter_anchor.visible = not filter_anchor.visible
        page.update()

    def show_view(is_roster):
        filter_anchor.visible = False
        roster_view.visible, task_org_view.visible = is_roster, not is_roster
        btn_roster.bgcolor = "#012169" if is_roster else ft.Colors.GREY_900
        btn_task_org.bgcolor = "#8B2331" if not is_roster else ft.Colors.GREY_900
        page.update()

    # UI Builders
    def build_filters():
        return ft.Column([
            ft.Text("FILTERS", size=14, weight="bold", color="blue400"),
            ft.Divider(height=1, color="white10"),
            ft.Text("SCHOOL:", size=11, weight="bold", color="grey500"),
            ft.Checkbox(label="Duke", data="school", on_change=on_filter_change, scale=0.9),
            ft.Checkbox(label="NCCU", data="school", on_change=on_filter_change, scale=0.9),
            ft.Divider(height=1, color="white10"),
            ft.Text("SQUAD:", size=11, weight="bold", color="grey500"),
            ft.Checkbox(label="1st", data="squad", on_change=on_filter_change, scale=0.9),
            ft.Checkbox(label="2nd", data="squad", on_change=on_filter_change, scale=0.9),
            ft.Checkbox(label="3rd", data="squad", on_change=on_filter_change, scale=0.9),
            ft.Checkbox(label="4th", data="squad", on_change=on_filter_change, scale=0.9),
            ft.Divider(height=1, color="white10"),
            ft.Text("MS LEVEL:", size=11, weight="bold", color="grey500"),
            ft.Row([
                ft.Checkbox(label="1", data="ms", on_change=on_filter_change, scale=0.8),
                ft.Checkbox(label="2", data="ms", on_change=on_filter_change, scale=0.8),
                ft.Checkbox(label="3", data="ms", on_change=on_filter_change, scale=0.8),
                ft.Checkbox(label="4", data="ms", on_change=on_filter_change, scale=0.8),
            ], wrap=True, spacing=0)
        ], tight=True, spacing=5, scroll=ft.ScrollMode.AUTO)

    # Search and Filter Components
    search_field = ft.TextField(
        hint_text="Search Name...", 
        prefix_icon=ft.Icons.SEARCH, 
        expand=True, 
        on_change=update_roster,
        border_radius=10,
        height=45,
        text_size=14
    )
    
    sort_dir_btn = ft.IconButton(ft.Icons.ARROW_UPWARD, on_click=toggle_sort, icon_size=20)
    
    filter_toggle_btn = ft.IconButton(
        icon=ft.Icons.FILTER_ALT_OUTLINED,
        on_click=toggle_filter_box,
        icon_size=20
    )

    roster_list = ft.ListView(expand=True, spacing=5)

    # UPDATED NAV DRAWER
    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(
                content=ft.Text("Hello World", size=24, weight="bold", color="white"),
                padding=40
            )
        ],
    )

    # Sidebar for Desktop
    filter_sidebar = ft.Container(
        content=build_filters(),
        width=250,
        bgcolor=ft.Colors.BLACK,
        padding=20,
        border=ft.border.only(left=ft.border.BorderSide(1, "white10")),
        visible=page.width > 800
    )

    # Floating Filter Anchor for Mobile
    filter_anchor = ft.TransparentPointer(
        content=ft.Container(
            content=ft.Container(
                content=build_filters(),
                padding=15,
                bgcolor=ft.Colors.GREY_900,
                border=ft.border.all(1, "white10"),
                border_radius=12,
                width=240,
                height=400,
                shadow=ft.BoxShadow(blur_radius=20, color="black")
            ),
            alignment=ft.Alignment(1, -1),
            padding=ft.padding.only(top=140, right=15), 
        ),
        visible=False
    )

    # Main Layouts
    roster_main_col = ft.Container(
        content=ft.Column([
            ft.Row([search_field, sort_dir_btn, filter_toggle_btn], spacing=5),
            roster_list 
        ], spacing=15),
        expand=True,
        padding=15
    )

    roster_view = ft.Stack([
        ft.Row([roster_main_col, filter_sidebar], expand=True, spacing=0),
        filter_anchor
    ], expand=True)

    task_org_view = ft.Container(
        content=ft.Text("Task Organization View (Placeholder)", color="white"),
        bgcolor="black", padding=20, expand=True, visible=False,
    )
    
    page.appbar = ft.AppBar(
        title=ft.Text("THE BULL PEN", weight="bold"), 
        bgcolor=ft.Colors.BLACK,
        center_title=True
    )

    # Bottom Nav
    rect_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0))
    btn_roster = ft.Button(
        "ROSTER", bgcolor="#012169", color="white", 
        on_click=lambda _: show_view(True), 
        expand=True, height=60, style=rect_style
    )
    btn_task_org = ft.Button(
        "TASK ORG", bgcolor="grey900", color="white", 
        on_click=lambda _: show_view(False), 
        expand=True, height=60, style=rect_style
    )

    def on_page_resize(e):
        if page.width > 800:
            filter_sidebar.visible = True
            filter_anchor.visible = False
            page.appbar.leading = None
        else:
            filter_sidebar.visible = False
            page.appbar.leading = hamburger_btn
        page.update()

    page.on_resize = on_page_resize

    page.floating_action_button = ft.FloatingActionButton(
    icon=ft.Icons.ADD,
    bgcolor="#012169",
    on_click=lambda _: open_cadet_modal()
    )
    
    page.add(
        ft.Column([
            ft.Container(content=ft.Stack([roster_view, task_org_view], expand=True), expand=True), 
            ft.Row([btn_roster, btn_task_org], spacing=0)
        ], expand=True, spacing=0)
    )
    
    update_roster()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
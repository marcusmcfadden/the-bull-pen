import flet as ft
import os
import asyncio
import datetime
import base64
import json
from database import (
    init_db,
    upsert_attendance_current,
    get_filtered_cadets,
    update_cadet,
    register_cadet,
    create_auth_user,
    delete_cadet,
    create_attendance_export,
    clear_attendance_for_new_week,
    _conn
)
import attendance_save
from rbac import (
    authenticate_user,
    can_edit,
    can_delete,
    get_user_by_id
)
from log_service import (
    log_event,
    get_logs
)

async def main(page: ft.Page):

    current_user = {
        "id": None,
        "tier": None,
        "name": None,
        "squad": None,
    }

    viewing_cadet_id = None

    def past_n_weeks_range(weeks: int) -> tuple:
        now = datetime.datetime.now()
        end_ts = int(now.timestamp())
        start_ts = int((now - datetime.timedelta(days=weeks*7)).timestamp())
        return start_ts, end_ts

    search_task = None
    flush_task = None
    update_lock = asyncio.Lock()

    init_db()

    from seed import seed_data
    from database import DB_PATH

    def is_db_empty():
        conn = _conn()
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) FROM cadets")
            count = cur.fetchone()[0]
            return count == 0
        except:
            return True  # table doesn't exist yet
        finally:
            conn.close()

    if is_db_empty():
        print("Seeding database...")
        seed_data()
    else:
        print("Database already initialized.")

    # Page Configuration
    page.title = "THE BULL PEN"
    page.theme_mode = ft.ThemeMode.DARK

    page.fonts = {
        "custom": "Marathon.otf",
        "standard": "Proxima Nova Semibold.ttf"
    }
    page.padding = 0

    active_schools = set()
    active_squads = set()
    active_ms = set()
    sort_ascending = True
    current_route = "roster"
    ip_address = None

    attendance_registry = []

    task_org_dirty = True
    auto_refresh_running = False

    version = "v1.0.0-beta"
    version_label = ft.TransparentPointer(
        content=ft.Container(
            content=ft.Text(
                version,
                size=10,
                color="white70",
                weight="bold"
            ),
            alignment=ft.Alignment.TOP_RIGHT,
            padding=ft.Padding.only(top=10, right=10)
        ),
    )

    def build_login_view():

        def handle_login(e):
            user = authenticate_user(username.value, password.value)

            if user:
                current_user.update(user)

                log_event(
                    actor_id=user["id"],
                    actor_role=user["tier"],
                    action="LOGIN",
                    status="SUCCESS",
                    location="auth"
                )

                nonlocal auto_refresh_running
                if not auto_refresh_running:
                    page.run_task(auto_refresh)
                    auto_refresh_running = True

                if user.get("reset_required"):
                    page.controls.clear()
                    open_change_password_dialog(force=True)
                    return

                page.controls.clear()

                page.drawer = build_drawer()

                roster_view.visible = True
                task_org_view.visible = False

                btn_roster.bgcolor = "#012169"
                btn_task_org.bgcolor = ft.Colors.GREY_900

                page.appbar = ft.AppBar(
                    title=ft.Text("ROSTER", font_family="standard"),
                    bgcolor="#012169",
                    center_title=True
                )

                page.add(
                    ft.Column([
                        ft.Container(
                            ft.Stack([roster_view, 
                                      task_org_view, 
                                      profile_view, 
                                      logs_view,
                                      version_label], 
                            expand=True),
                            expand=True
                        ),
                        ft.Row([btn_roster, btn_task_org], spacing=0)
                    ], expand=True)
                )

                page.appbar = ft.AppBar(
                    title=ft.Text("THE BULL PEN", font_family="standard"),
                    bgcolor=ft.Colors.BLACK,
                    center_title=True
                )

                if current_user["tier"] <= 1:
                    page.floating_action_button = ft.FloatingActionButton(
                        icon=ft.Icons.ADD,
                        bgcolor="#012169",
                        on_click=lambda _: open_cadet_modal()
                    )
                else:
                    page.floating_action_button = None

                page.update()
                page.run_task(update_roster_ui)

                async def preload_attendance():
                    nonlocal task_org_dirty
                    task_org_view.content = await build_task_org()
                    task_org_dirty = False

                page.run_task(preload_attendance)
            else:
                status_text.value = "Incorrect username or password"

                log_event(
                    actor_id=None,
                    action="LOGIN",
                    status="FAILED",
                    location="auth"
                )

                page.update()

        username = ft.TextField(
            label="username",
            width=300,
            border_radius=8,
            bgcolor="#1e1e1e",
            on_submit=handle_login
        )

        password = ft.TextField(
            label="password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_radius=8,
            bgcolor="#1e1e1e",
            on_submit=handle_login
        )

        status_text = ft.Text(color="red", size=12)

        btn_text = ft.Text("ENTER", weight="bold", color="white")

        def on_hover(e):
            if e.data == "true":
                e.control.bgcolor = "white"
                btn_text.color = "black"
            else:
                e.control.bgcolor = "transparent"
                btn_text.color = "white"

            e.control.update()

        login_button = ft.Container(
            content=btn_text,
            width=300,
            height=45,
            alignment=ft.Alignment.CENTER,
            border=ft.Border.all(1, "white"),
            border_radius=8,
            bgcolor="transparent",
            ink=True,
            on_click=handle_login,
            on_hover=on_hover
        )

        # Main Header
        card = ft.Container(
            width=380,
            height=500,
            padding=10,
            border_radius=20,
            bgcolor="#121212",
            border=ft.Border.all(1, "white10"),
            content=ft.Column(
                [
                    ft.Container(height=10),
                    ft.Text("Welcome To", 
                            size=30,
                            text_align=ft.TextAlign.CENTER,
                            font_family="custom"),
                    ft.Text("THE BULL PEN", 
                            size=100,
                            text_align=ft.TextAlign.CENTER,
                            font_family="custom"),

                    ft.Container(height=5),

                    ft.Divider(color="white12"),

                    ft.Container(height=10),

                    username,
                    password,

                    login_button,

                    status_text
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Stack(
                expand=True,
                alignment=ft.Alignment.CENTER,
                controls=[    

                    ft.Image(           
                        src="bcblogo.png",                           
                        fit=ft.BoxFit.CONTAIN,
                        opacity=0.10,
                        width=1000,
                        height=1000            
                    ),
                    card,
                    version_label
                ]
            )
        )
    
    page.appbar = None
    page.floating_action_button = None

    splash = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing()
    )

    page.add(splash)

    async def load_ui():
        await asyncio.sleep(0.3)
        page.controls.clear()
        page.add(build_login_view())
        page.update()

    page.run_task(load_ui)

    def handle_logout(e=None):

        nonlocal search_task, flush_task

        if search_task and not search_task.done():
            search_task.cancel()

        if flush_task and not flush_task.done():
            flush_task.cancel()

        page.drawer.open = False

        log_event(
            actor_id=current_user["id"],
            actor_role=current_user["tier"],
            action="LOGOUT",
            status="SUCCESS",
            location="auth"
        )

        current_user["id"] = None
        current_user["tier"] = None
        current_user["name"] = None
        current_user["squad"] = None

        roster_view.visible = True
        task_org_view.visible = False

        page.controls.clear()
        page.overlay.clear()
        page.appbar = None
        page.drawer = None
        page.floating_action_button = None

        page.add(build_login_view())

        page.update()

    def go_home(e=None):
        nonlocal current_route

        page.drawer.open = False

        if current_route == "roster":
            return

        current_route = "roster"
        asyncio.create_task(show_view(True))

    def go_profile(e=None, cadet_data=None):
        nonlocal current_route, viewing_cadet_id

        page.drawer.open = False
        current_route = "profile"

        if cadet_data:
            c_id, c_name, c_ms, c_school, c_squad, c_tier = cadet_data
            viewing_cadet_id = c_id
            profile_username.value = "N/A"
        else:
            user_data = get_user_by_id(current_user["id"])
            if not user_data:
                return

            c_id = user_data["id"]
            c_name = user_data["name"]
            c_ms = user_data["ms_level"]
            c_school = user_data["school"]
            c_squad = user_data["squad"]

            viewing_cadet_id = c_id

            profile_username.value = user_data.get("username", "N/A")

        name_parts = c_name.split(" ", 1)

        profile_first_name.value = name_parts[0]
        profile_last_name.value = name_parts[1] if len(name_parts) > 1 else ""
        profile_ms.value = f"MS{c_ms}"
        profile_squad.value = c_squad
        profile_school.value = "Duke" if c_school == "D" else "NCCU"
        if cadet_data:
            profile_email.value = "N/A"
            profile_phone.value = "N/A"
        else:
            profile_email.value = user_data.get("email", "N/A")
            profile_phone.value = user_data.get("phone", "N/A")

        edit_profile_btn.visible = (viewing_cadet_id == current_user["id"])

        roster_view.visible = False
        task_org_view.visible = False
        profile_view.visible = True
        logs_view.visible = False

        page.update()

    # Real-time PubSub

    def on_broadcast(msg):

        if not current_user["id"]:
            return

        if msg in ["roster_updated", "attendance_updated"]:
            page.run_task(update_roster_ui)

            nonlocal task_org_dirty
            task_org_dirty = True

            if current_route == "attendance":
                async def refresh_attendance():
                    task_org_view.content = await build_task_org()
                    page.update()

                page.run_task(refresh_attendance)
            else:
                page.update()

    page.pubsub.subscribe(on_broadcast)

    async def update_roster_ui():

        if not current_user["id"]:
            return

        query = search_field.value if search_field.value else ""
        direction = "ASC" if sort_ascending else "DESC"

        cadets = await asyncio.to_thread(
            get_filtered_cadets, 
            query, list(active_schools), list(active_squads), list(active_ms), direction
        )

        total_text.value = f"Total: {len(cadets)} cadets"
        
        roster_list.controls.clear()

        tier_names = {
            0: "COMMAND",
            1: "OFFICER",
            2: "SL",
            3: "CDT"
        }

        for cadet in cadets:
            c_id, c_name, c_ms, c_school, c_squad, c_tier = cadet
            name_parts = c_name.split(" ", 1)
            display_name = f"{name_parts[1]}, {name_parts[0]}" if len(name_parts) > 1 else c_name
            school_color = "#012169" if c_school == "D" else "#8B2331"

            target = {
                "id":c_id,
                "tier":c_tier,
                "squad":c_squad,
            }

            menu_items =[]

            if current_user["tier"] <= 1:

                if can_edit(current_user, target):
                    menu_items.append(
                        ft.PopupMenuItem(
                            "Edit",
                            icon=ft.Icons.EDIT,
                            on_click=lambda _, d=cadet: open_cadet_modal(d)
                        )
                    )

                if can_delete(current_user, target):
                    menu_items.append(
                        ft.PopupMenuItem(
                            "Delete",
                            icon=ft.Icons.DELETE_OUTLINE,
                            on_click=lambda _, i=c_id, n=c_name: confirm_delete(i, n)
                        )
                    )

            roster_list.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        leading=ft.CircleAvatar(
                            content=ft.Text(display_name[0]),
                            bgcolor=school_color
                        ),
                        title=ft.Text(display_name),
                        subtitle=ft.Text(f"MS{c_ms} | {c_squad} | {tier_names.get(c_tier, 'UNK')}"),
                        trailing=ft.PopupMenuButton(items=menu_items) if menu_items else None,
                        on_click=lambda e, d=cadet: go_profile(cadet_data=d)
                    )
                )
            )
        page.update()

    async def debounce_search(e):

        if not current_user["id"]:
            return

        nonlocal search_task
        if search_task and not search_task.done():
            search_task.cancel()

        async def search_logic():
            nonlocal search_task
            try:
                await asyncio.sleep(0.35)
                await update_roster_ui()
            except asyncio.CancelledError:
                return
            finally:
                search_task = None

        search_task = asyncio.create_task(search_logic())

    async def handle_save_csv(e):
        nonlocal task_org_dirty

        if current_user["tier"] > 1:
            return

        if not attendance_registry:
            return

        log_event(
            actor_id=current_user["id"],
            actor_role=current_user["tier"],
            action="EXPORT_ATTENDANCE",
            status="SUCCESS",
            location="export_csv"
        )

        try:
            csv_bytes = await attendance_save.generate_csv(attendance_registry)

            if not csv_bytes:
                raise Exception("CSV generation returned empty data")

            b64 = base64.b64encode(csv_bytes).decode()

            await page.launch_url(
                url=f"data:text/csv;base64,{b64}"
            )

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="EXPORT_ATTENDANCE",
                status="SUCCESS",
                location="export_csv"
            )

            page.snack_bar = ft.SnackBar(
                ft.Text("CSV xported successfullyy"),
                bgcolor="green"
            )
            page.snack_bar.open = True

            start_ts, end_ts = past_n_weeks_range(2)

            clear_attendance_for_new_week(
                clear_events_in_range=(start_ts, end_ts),
                reset_current=True,
                backup=True
            )

            attendance_registry.clear()
            task_org_dirty = True

            await show_view(False)

        except Exception as exc:
            import traceback
            traceback.print_exc()

            page.snack_bar = ft.SnackBar(
                ft.Text(f"PDF export failed: {str(exc)}"),
                bgcolor="red"
            )
            page.snack_bar.open = True

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="EXPORT_ATTENDANCE",
                status="FAILED",
                location="export_csv",
                metadata=json.dumps({"error": str(exc)})
            )

        finally:
            if hasattr(page, 'update_async'):
                await page.update_async()
            else:
                page.update()

    async def handle_save(e):
        nonlocal task_org_dirty

        if current_user["tier"] > 1:
            return

        if not attendance_registry:
            page.snack_bar = ft.SnackBar(ft.Text("No attendance data to export"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        try:
            day_order = {"TUE PT": 0, "WED PT": 1, "THU PT": 2, "LAB": 3}
            target_days = list(set(item["col"] for item in attendance_registry))
            target_days.sort(key=lambda d: day_order.get(d, 99))

            pdf_gen = attendance_save.AttendancePDF()

            for day in target_days:
                day_data = []

                for item in attendance_registry:
                    if item["col"] == day:
                        status_val = getattr(item["status"], "value", None)
                        late_val = getattr(item["late"], "value", False)

                        day_data.append({
                            "name": item["name"],
                            "ms": item["ms"],
                            "status": status_val if status_val else "N/A",
                            "is_late": bool(late_val)
                        })

                pdf_gen.generate_combined_report(day, day_data)

            pdf_bytes = pdf_gen.output(dest='S')
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode('latin-1')

            b64 = base64.b64encode(pdf_bytes).decode()

            await page.launch_url(
                url=f"data:application/pdf;base64,{b64}"
            )

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="EXPORT_PDF",
                status="SUCCESS",
                location="export_pdf"
            )

            start_ts, end_ts = past_n_weeks_range(2)

            clear_attendance_for_new_week(
                clear_events_in_range=(start_ts, end_ts),
                reset_current=True,
                backup=True
            )

            attendance_registry.clear()
            task_org_dirty = True

            await show_view(False)

            try:
                page.pubsub.send_all("attendance_updated")
            except:
                pass

            page.snack_bar = ft.SnackBar(
                ft.Text("PDF exported successfully"),
                bgcolor="green"
            )
            page.snack_bar.open = True

        except Exception as ex:
            import traceback
            traceback.print_exc()

            page.snack_bar = ft.SnackBar(
                ft.Text(f"PDF export failed: {str(ex)}"),
                bgcolor="red"
            )
            page.snack_bar.open = True

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="EXPORT_PDF",
                status="FAILED",
                location="export_pdf",
                metadata=json.dumps({"error": str(ex)})
            )

        finally:
            if hasattr(page, 'update_async'):
                await page.update_async()
            else:
                page.update()

    def open_change_password_dialog(force=False):

        status_text = ft.Text(color="red", size=12)

        def handle_change(e):

            if not new_password.value or not confirm_password.value:
                status_text.value = "All fields required"
                page.update()
                return

            if new_password.value != confirm_password.value:
                status_text.value = "Passwords do not match"
                page.update()
                return

            if len(new_password.value) < 4:
                status_text.value = "Password too short"
                page.update()
                return

            from database import update_user_password

            update_user_password(current_user["id"], new_password.value)

            conn = _conn(write=True)
            cur = conn.cursor()
            cur.execute("UPDATE auth_users SET reset_required = 0 WHERE id = %s", (current_user["id"],))
            conn.commit()
            conn.close()

            dialog.open = False

            page.snack_bar = ft.SnackBar(
                ft.Text("Password updated successfully"),
                bgcolor="green"
            )
            page.snack_bar.open = True

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="PASSWORD_CHANGE",
                status="SUCCESS",
                target_id=current_user["id"],
                target_type="cadet"
            )

            if not force:
                profile_view.visible = True
                page.update()

            if force:
                page.controls.clear()
                page.add(build_login_view())
                page.update()
                return

            page.update()

        new_password = ft.TextField(
            label="New Password",
            password=True,
            can_reveal_password=True,
            on_submit=handle_change
        )

        confirm_password = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            on_submit=handle_change
        )

        dialog = ft.AlertDialog(
            modal=True,
            barrier_color="black54",
            title=ft.Text("Reset Password" if force else "Change Password"),
            content=ft.Column([
                new_password,
                confirm_password,
                status_text
            ], tight=True),
            actions=[] if force else [
                ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, "open", False)),
                ft.Button("Save", on_click=handle_change)
            ],
        )

        if force:
            dialog.actions = [
                ft.Button("Set Password", on_click=handle_change)
            ]

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # Logic Functions
    def update_roster(e=None):
        query = search_field.value if search_field.value else ""
        direction = "ASC" if sort_ascending else "DESC"
    
        async def fetch_and_update():
            cadets = await asyncio.to_thread(
                get_filtered_cadets, 
                query, list(active_schools), list(active_squads), list(active_ms), direction)
            roster_list.controls.clear()
            for cadet in cadets:
                c_id, c_name, c_ms, c_school, c_squad, c_tier = cadet
                name_parts = c_name.split(" ", 1)
                display_name = f"{name_parts[1]}, {name_parts[0]}" if len(name_parts) > 1 else c_name
                school_color = "#012169" if c_school == "D" else "#8B2331"
                
                roster_list.controls.append(
                    ft.Card(
                        content=ft.ListTile(
                            leading=ft.CircleAvatar(content=ft.Text(display_name[0]), bgcolor=school_color),
                            title=ft.Text(display_name),
                            subtitle=ft.Text(f"MS{c_ms} | {c_squad}"),
                            trailing=ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                items=[
                                    ft.PopupMenuItem("Edit", icon=ft.Icons.EDIT, on_click=lambda _, d=cadet: open_cadet_modal(d)),
                                    ft.PopupMenuItem("Delete", icon=ft.Icons.DELETE_OUTLINE, on_click=lambda _, i=c_id, n=c_name: confirm_delete(i, n)),
                                ]
                            )
                        )
                    )
                )
        page.update()

        asyncio.create_task(fetch_and_update())

    def open_cadet_modal(cadet_data=None):

        if cadet_data:
            target = {
                "id": cadet_data[0],
                "tier": cadet_data[5],
                "squad": cadet_data[4],
            }

            if not can_edit(current_user, target):
                log_event(
                    actor_id=current_user["id"],
                    actor_role=current_user["tier"],
                    action="ACCESS_ATTEMPT",
                    status="DENIED",
                    target_type="cadet_edit",
                    target_id=target["id"]
                )
                return
            
        is_edit = cadet_data is not None
        
        full_name = cadet_data[1] if is_edit else ""
        name_parts = full_name.split(" ", 1)
        f_name_val = name_parts[0] if len(name_parts) > 0 else ""
        l_name_val = name_parts[1] if len(name_parts) > 1 else ""

        first_name = ft.TextField(label="First Name", value=f_name_val, expand=True)
        last_name = ft.TextField(label="Last Name", value=l_name_val, expand=True)
        email_field = ft.TextField(label="Email", value="", expand=True)
        phone_field = ft.TextField(label="Phone", value="", expand=True)

        if is_edit:
            email_field.value = cadet_data[6] if len(cadet_data) > 6 else ""
            phone_field.value = cadet_data[7] if len(cadet_data) > 7 else ""
        
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

        if current_user["tier"] == 0:  # superadmin
            tier_options = [
                ft.dropdown.Option("0", "Command"),
                ft.dropdown.Option("1", "Officer"),
                ft.dropdown.Option("2", "Leader"),
                ft.dropdown.Option("3", "Cadet"),
            ]
        elif current_user["tier"] == 1:  # admin
            tier_options = [
                ft.dropdown.Option("2", "Leader"),
                ft.dropdown.Option("3", "Cadet"),
            ]
        else:
            tier_options = []

        tier_dropdown = ft.Dropdown(
            label="Tier",
            value=str(cadet_data[5]) if is_edit else "3",
            options=tier_options,
            width=120,
            visible=current_user["tier"] <= 1
        )

        if current_user["tier"] > 1:
            first_name.disabled = True
            last_name.disabled = True
            school_dropdown.disabled = True
            ms_level.disabled = True
            squad_dropdown.disabled = True
            tier_dropdown.disabled = True

        def close_dialog(dialog):
            dialog.open = False
            page.update()

        def check_no_leader_dialog(squad):
            conn = _conn()
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM cadets
                WHERE squad = %s AND tier = 2
            """, (squad,))

            count = cur.fetchone()[0]
            conn.close()

            if count == 0:
                show_no_leader_dialog(squad)

        def show_no_leader_dialog(squad):

            dialog = ft.AlertDialog(
                modal=True,
                barrier_color="black54",
                title=ft.Text("Warning"),
                content=ft.Text(f"{squad} currently has no squad leader"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: close_dialog(dialog))
                ]
            )

            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def save_clicked(e):

            combined_name = f"{first_name.value} {last_name.value}".strip()
            new_tier = int(tier_dropdown.value) if current_user["tier"] <= 1 else cadet_data[5]

            cadet_id = cadet_data[0] if is_edit else None
            old_tier = cadet_data[5] if is_edit else None
            squad = squad_dropdown.value

            def continue_save():

                if is_edit:

                    # enforce single leader
                    if new_tier == 2:
                        conn = _conn(write=True)
                        cur = conn.cursor()

                        cur.execute("""
                            UPDATE cadets
                            SET tier = 3
                            WHERE squad = %s AND tier = 2 AND id != %s
                        """, (squad, cadet_id))

                        conn.commit()
                        conn.close()

                    update_cadet(
                        cadet_id,
                        combined_name,
                        int(ms_level.value),
                        school_dropdown.value,
                        squad_dropdown.value,
                        new_tier,
                        email_field.value,
                        phone_field.value
                    )

                    if old_tier != new_tier:
                        log_event(
                            actor_id=current_user["id"],
                            actor_role=current_user["tier"],
                            action="UPDATE_ROLE",
                            status="SUCCESS",
                            target_id=cadet_id,
                            target_type="cadet",
                            metadata={"old": old_tier, "new": new_tier}
                        )

                    # check missing leader
                    if old_tier == 2 and new_tier != 2:
                        check_no_leader_dialog(squad)

                else:
                    cadet_id_new = register_cadet(
                        combined_name,
                        int(ms_level.value),
                        school_dropdown.value,
                        squad_dropdown.value,
                        new_tier,
                        email_field.value,
                        phone_field.value
                    )

                    log_event(
                        actor_id=current_user["id"],
                        actor_role=current_user["tier"],
                        action="CREATE_CADET",
                        status="SUCCESS",
                        target_id=cadet_id_new,
                        target_type="cadet"
                    )

                    username = combined_name.lower().replace(" ", "")
                    password = "password123"

                    create_auth_user(cadet_id_new, username, password)

                dialog.open = False
                page.pubsub.send_all("roster_updated")
                page.update()

            if current_user["tier"] == 1 and new_tier <= 1:

                dialog_block = ft.AlertDialog(
                    modal=True,
                    barrier_color="black54",
                    title=ft.Text("Access Denied"),
                    content=ft.Text("You cannot assign Admin or Superadmin roles"),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: close_dialog(dialog_block))
                    ]
                )

                page.overlay.append(dialog_block)
                dialog_block.open = True
                page.update()
                return

            if current_user["tier"] == 1 and new_tier == 2:

                def confirm_promote(e):
                    dialog_confirm.open = False
                    page.update()
                    continue_save()

                def cancel_promote(e):
                    dialog_confirm.open = False
                    page.update()

                dialog_confirm = ft.AlertDialog(
                    modal=True,
                    barrier_color="black54",
                    title=ft.Text("Confirm Promotion"),
                    content=ft.Text(
                        "Are you sure you want to promote this cadet to Leader?\n\n"
                        "This action cannot be undone with your authority."
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=cancel_promote),
                        ft.TextButton("Confirm", on_click=confirm_promote),
                    ]
                )

                page.overlay.append(dialog_confirm)
                dialog_confirm.open = True
                page.update()
                return

            continue_save()

        # Build the UI Structure
        dialog = ft.AlertDialog(
                    modal=True,
                    barrier_color="black54",
                    title=ft.Text("Cadet Profile"),
                    content=ft.Container(
                        width=600,
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
                                ft.Text("Contact Info", weight="bold", color="blue200"),
                                ft.Row([
                                    email_field,
                                    phone_field
                                ], spacing=10),
                            ],
                            expand=True,
                            spacing=15,
                            scroll=ft.ScrollMode.AUTO
                            )
                        ])
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _: [setattr(dialog, "open", False), page.update()]),
                        ft.Button("Save", bgcolor="#012169", color="white", on_click=save_clicked),
                    ],
                )

        # Show the Dialog
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def confirm_delete(cadet_id, cadet_name):

        target = get_user_by_id(cadet_id)

        if not can_delete(current_user, target):
            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="ACCESS_ATTEMPT",
                status="DENIED",
                target_type="cadet_delete",
                target_id=target["id"]
            )
            return

        def finalize_delete(e):
            delete_cadet(cadet_id)
            confirm_dialog.open = False 
            page.pubsub.send_all("roster_updated")

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="DELETE_CADET",
                status="SUCCESS",
                target_type="cadet_delete",
                target_id=cadet_id
            )

            page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to delete {cadet_name}?"),
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
        asyncio.create_task(update_roster_ui())

    def toggle_filter_box(e):
        if page.width > 800:
            filter_sidebar.visible = not filter_sidebar.visible
        else:
            filter_anchor.visible = not filter_anchor.visible
        page.update()

    def confirm_export(action_callback):

        def do_confirm(e):
            dialog.open = False
            page.update()
            asyncio.create_task(action_callback(e))

        def cancel(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            barrier_color="black54",
            title=ft.Text("Confirm Export"),
            content=ft.Text(
                "Are you sure you would like to save?\n\n"
                "Current Attendance will be cleared."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Confirm", on_click=do_confirm),
            ],
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    async def build_task_org():

        if not current_user["id"]:
            return

        attendance_registry.clear()
        cadets = await asyncio.to_thread(get_filtered_cadets, "", [], [], [], "ASC")

        if current_user["tier"] == 2:
            cadets = [c for c in cadets if c[4] == current_user["squad"]]
        
        conn = _conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cadet_id, day, status, is_late
            FROM attendance_current
        """)
        attendance_data = {
            (row[0], row[1]): (row[2], row[3]) 
            for row in cursor.fetchall()
        }
        conn.close()

        squad_groups = {}
        for c in cadets:
            squad_name = c[4] 
            if squad_name not in squad_groups:
                squad_groups[squad_name] = []
            squad_groups[squad_name].append(c)

        days = ["TUE PT", "WED PT", "THU PT", "LAB"]

        def create_attendance_cell(cadet_id, cadet_name, cadet_ms, cadet_school, cadet_squad, column_label, current_status, current_late):

            async def sync_status(e):
                if status_dropdown.value != "P":
                    late_checkbox.value = False

                late_checkbox.disabled = status_dropdown.value != "P"

                status_val = status_dropdown.value if status_dropdown.value else None
                late_val = 1 if late_checkbox.value else 0

                try:
                    await asyncio.to_thread(
                        upsert_attendance_current,
                        cadet_id,
                        column_label,
                        status_val,
                        late_val
                    )
                except Exception as e:
                    import traceback
                    traceback.print_exc()

                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Attendance error: {str(e)}"),
                        bgcolor="red"
                    )
                    page.snack_bar.open = True
                    page.update()

                    return

                log_event(
                    actor_id=current_user["id"],
                    actor_role=current_user["tier"],
                    action="UPDATE_ATTENDANCE",
                    status="SUCCESS",
                    location="attendance",
                    target_id=cadet_id,
                    target_type="cadet",
                    metadata={
                        "column": column_label,
                        "status": status_val,
                        "late": late_val
                    }
                )

                status_dropdown.value = status_val
                late_checkbox.value = bool(late_val)
                page.update()

                try:
                    page.pubsub.send_all("attendance_updated")
                except:
                    pass

            status_dropdown = ft.Dropdown(
                value=current_status,
                options=[
                    ft.dropdown.Option("P", "Present"),
                    ft.dropdown.Option("A", "Absent"),
                    ft.dropdown.Option("E", "Excused"),
                    ft.dropdown.Option("UN", "Uncontracted"),
                ],
                expand=True, dense=True, text_size=11, border_color="white24",
            )

            late_checkbox = ft.Checkbox(
                value=True if current_late == 1 else False,
                label="L",
            )

            status_dropdown.on_change = sync_status
            late_checkbox.on_change = sync_status

            attendance_registry.append({
                "name": cadet_name,
                "ms": cadet_ms,
                "squad": cadet_squad,
                "school": cadet_school,
                "col": column_label,
                "status": status_dropdown,
                "late": late_checkbox
            })
            return ft.Row([status_dropdown, late_checkbox], spacing=0, alignment=ft.MainAxisAlignment.CENTER)


        squad_containers = []
        for squad in sorted(squad_groups.keys()):
            squad_total = len(squad_groups[squad])
            rows = []
            for cadet in squad_groups[squad]:
                c_id, c_name, c_ms, c_school, c_squad, c_tier = cadet
                is_lead = c_tier in [1, 2]

                cells = [ft.DataCell(ft.Text(c_name, weight="bold" if is_lead else "normal", color="blue400" if is_lead else "white"))]
                for day in days:
                    state = attendance_data.get((c_id, day), (None, 0))
                    cells.append(ft.DataCell(create_attendance_cell(c_id, c_name, c_ms, c_school, c_squad, day, state[0], state[1])))
                rows.append(ft.DataRow(cells=cells))

            squad_containers.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(squad.upper(), weight="bold", size=16, color="blue200"),
                            ft.Container(expand=True),
                            ft.Text(f"Total: {squad_total}", size=12, color="grey")
                        ]),
                        ft.DataTable(
                            column_spacing=15,
                            columns=[ft.DataColumn(ft.Text("NAME"))] + [ft.DataColumn(ft.Text(d)) for d in days],
                            rows=rows,
                            border=ft.Border.all(1, "white10"),
                            border_radius=8,
                        )
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.WHITE10,
                    border_radius=10,
                )
            )

        export_button = (
            ft.PopupMenuButton(
                content=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DOWNLOAD, color="white"),
                        ft.Text("EXPORT REPORT", color="white", weight="bold"),
                    ]),
                    bgcolor="#00D118",
                    padding=ft.Padding.all(10),
                    border_radius=8,
                ),
                items=[
                    ft.PopupMenuItem(
                        content=ft.Text("Export as PDF"),
                        icon=ft.Icons.PICTURE_AS_PDF,
                        on_click=lambda e: confirm_export(handle_save)
                    ),
                    ft.PopupMenuItem(
                        content=ft.Text("Export as CSV (Excel)"),
                        icon=ft.Icons.TABLE_CHART,
                        on_click=lambda e: confirm_export(handle_save_csv)
                    ),
                ],
            )
            if current_user["tier"] <= 1 else None
        )

        return ft.Stack([
            # Background image
            ft.Container(
                content=ft.Image(
                    src="bcblogo.png",
                    fit=ft.BoxFit.CONTAIN,
                    opacity=0.08,
                    width=800,
                    height=800,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            ),

            # Foreground content
            ft.Column([
                ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Text("MULTI-DAY ATTENDANCE", size=20, weight="bold"),
                        export_button or ft.Container()
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ),
                ft.Row(
                    controls=squad_containers,
                    scroll=ft.ScrollMode.ALWAYS,
                    vertical_alignment="start",
                    spacing=20
                )
            ], expand=True, scroll=ft.ScrollMode.AUTO)
        ])

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
        on_change=debounce_search,
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

    def build_drawer():
        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "WELCOME TO THE BULL PEN",
                        size=24,
                        weight="bold",
                        color="white"
                    ),
                    padding=40
                ),

                ft.Divider(),

                ft.ListTile(
                    leading=ft.Icon(ft.Icons.HOME),
                    title=ft.Text("Home"),
                    on_click=go_home
                ),

                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PERSON),
                    title=ft.Text("Profile"),
                    on_click=go_profile
                ),

                ft.Divider(),

                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LOGOUT),
                    title=ft.Text("Logout"),
                    on_click=handle_logout
                ),

                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LIST),
                    title=ft.Text("Activity"),
                    on_click=lambda e: asyncio.create_task(show_logs())
                )
            ],
        )
        drawer.open = False
        return drawer

    # Sidebar for Desktop
    filter_sidebar = ft.Container(
        content=build_filters(),
        width=250,
        bgcolor=ft.Colors.BLACK,
        padding=20,
        border=ft.Border.only(left=ft.border.BorderSide(1, "white10")),
        visible=page.width > 800
    )

    # Floating Filter Anchor for Mobile
    filter_anchor = ft.TransparentPointer(
        content=ft.Container(
            content=ft.Container(
                content=build_filters(),
                padding=15,
                bgcolor=ft.Colors.GREY_900,
                border=ft.Border.all(1, "white10"),
                border_radius=12,
                width=240,
                height=400,
                shadow=ft.BoxShadow(blur_radius=20, color="black")
            ),
            alignment=ft.Alignment(1, -1),
            padding=ft.Padding.only(top=140, right=15), 
        ),
        visible=False
    )

    # Main Layouts
    total_text = ft.Text(size=12, color="grey")

    roster_main_col = ft.Container(
        content=ft.Column([
            ft.Row([search_field, sort_dir_btn, filter_toggle_btn], spacing=5),
            total_text,
            roster_list
        ], spacing=10),
        expand=True,
        padding=15
    )

    roster_view = ft.Stack([
        ft.Container(
            content=ft.Image(
                src="bcblogo.png",
                fit=ft.BoxFit.CONTAIN,
                opacity=0.08,
                width=800,
                height=800,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
        ),

        # Main content
        ft.Row([roster_main_col, filter_sidebar], expand=True, spacing=0),

        filter_anchor
    ], expand=True)

    task_org_view = ft.Container(
        content=None,
        expand=True,
        visible=False,
        padding=10
    )

    profile_first_name = ft.Text(size=20, weight="bold")
    profile_last_name = ft.Text(size=20, weight="bold")
    profile_username = ft.Text()
    profile_ms = ft.Text()
    profile_squad = ft.Text()
    profile_school = ft.Text()
    profile_email = ft.Text()
    profile_phone = ft.Text()

    def open_edit_profile(e):
        open_cadet_modal((
            current_user["id"],
            current_user["name"],
            1,
            "D",
            current_user["squad"],
            current_user["tier"]
        ))

    edit_profile_btn = ft.Button(
        "Edit Profile",
        icon=ft.Icons.EDIT,
        on_click=open_edit_profile,
    )

    profile_view = ft.Container(
        expand=True,
        padding=20,
        visible=False,
        content=ft.Column([
            ft.Row([
                ft.Text("PROFILE", size=30, weight="bold"),
                ft.Container(expand=True),
                edit_profile_btn
            ]),

            ft.Divider(),

            ft.Row([
                ft.Column([
                    ft.CircleAvatar(
                        content=ft.Icon(ft.Icons.PERSON, size=60),
                        radius=80,
                        bgcolor="#012169"
                    ),
                    ft.Text("PHOTO", size=10)
                ], width=200, horizontal_alignment="center"),

                ft.VerticalDivider(width=1),

                ft.Column([
                    ft.Row([ft.Text("First Name:", weight="bold"), profile_first_name]),
                    ft.Row([ft.Text("Last Name:", weight="bold"), profile_last_name]),
                    ft.Row([ft.Text("Username:", weight="bold"), profile_username]),
                    ft.Row([ft.Text("MS Level:", weight="bold"), profile_ms]),
                    ft.Row([ft.Text("Squad:", weight="bold"), profile_squad]),
                    ft.Row([ft.Text("School:", weight="bold"), profile_school]),
                    ft.Row([ft.Text("Email:", weight="bold"), profile_email]),
                    ft.Row([ft.Text("Phone:", weight="bold"), profile_phone]),

                    ft.Container(height=10),
                    ft.Button(
                        "Change Password",
                        icon=ft.Icons.LOCK,
                        on_click=lambda e: open_change_password_dialog()
                    ),
                ], spacing=15, expand=True)
            ], expand=True)
        ])
    )

    log_list = ft.ListView(expand=True, spacing=5)

    logs_view = ft.Container(
        content=ft.Column([
            ft.Text("ACTIVITY LOG", size=20, weight="bold"),
            log_list
        ]),
        expand=True,
        padding=10,
        visible=False
    )

    async def auto_refresh():
        while True:
            await asyncio.sleep(3)

            if not current_user["id"]:
                break

            if logs_view.visible:
                await load_logs()

            elif task_org_view.visible:
                pass

    async def show_view(is_roster):
        nonlocal task_org_dirty, current_route

        filter_anchor.visible = False

        profile_view.visible = False
        logs_view.visible = False

        roster_view.visible = is_roster
        task_org_view.visible = not is_roster

        if is_roster:
            current_route = "roster"
        else:
            current_route = "attendance"

        if not is_roster:
            if not task_org_view.content or task_org_dirty:
                task_org_view.content = await build_task_org()
                task_org_dirty = False

        btn_roster.bgcolor = "#012169" if is_roster else ft.Colors.GREY_900
        btn_task_org.bgcolor = "#8B2331" if not is_roster else ft.Colors.GREY_900

        page.update()

    async def load_logs():
        logs = await asyncio.to_thread(get_logs, 50)

        log_list.controls.clear()

        for log in logs:
            ts = log["timestamp"]
            time_str = ts.strftime("%H:%M") if ts else "??:??"
            actor_id = log.get("actor_id")
            actor = f"cadet_{actor_id}" if actor_id is not None else "unknown"

            action = log["action"]
            action_readable = action.lower().replace("_", " ")

            if action == "UPDATE_ATTENDANCE":
                target = log.get("target_id")
                text = f"[{time_str}] {actor} updated cadet_{target} attendance"

            elif action == "LOGIN":
                text = f"[{time_str}] {actor} logged in"

            elif action == "LOGOUT":
                text = f"[{time_str}] {actor} logged out"

            elif action == "ACCESS_ATTEMPT" and log["status"] == "DENIED":
                text = f"[{time_str}] {actor} attempted restricted access"

            else:
                text = f"[{time_str}] {actor} {action_readable}"

            log_list.controls.append(ft.Text(text, size=12))

        page.update()


    # Bottom Nav
    rect_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        text_style=ft.TextStyle(font_family="standard")
    )

    btn_roster = ft.Button(
        "ROSTER", 
        bgcolor="#012169", 
        color="white", 
        on_click=lambda e: asyncio.create_task(show_view(True)),
        expand=True, 
        height=60, 
        style=rect_style
    )

    async def show_logs():
        roster_view.visible = False
        task_org_view.visible = False
        profile_view.visible = False
        logs_view.visible = True

        await load_logs()

    def handle_attendance_click(e):
        if current_user["tier"] is not None and current_user["tier"] > 2:

            log_event(
                actor_id=current_user["id"],
                actor_role=current_user["tier"],
                action="ACCESS_ATTEMPT",
                status="DENIED",
                target_type="attendance_view"
            )

            def close_dialog(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                barrier_color="black54",
                title=ft.Text("Access Denied"),
                content=ft.Text("You don't have permission to access this section"),
                actions=[
                    ft.TextButton(
                        "OK",
                        on_click=lambda _: close_dialog(dialog)
                    )
                ]
            )

            page.overlay.append(dialog)
            dialog.open = True
            page.update()

            return

        asyncio.create_task(show_view(False))

    rect_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=0),
        text_style=ft.TextStyle(font_family="standard")
    )

    btn_task_org = ft.Button(
        "ATTENDANCE",
        bgcolor="grey900",
        color="white",
        on_click=handle_attendance_click,
        expand=True,
        height=60,
        style=rect_style
    )

    def on_page_resize(e):
        if page.width > 800:
            filter_sidebar.visible = True
            filter_anchor.visible = False

            if page.appbar:
                page.appbar.leading = None
        else:
            filter_sidebar.visible = False

        page.update()

    page.on_resize = on_page_resize

if __name__ == "__main__":
    ft.run(
       main,
       assets_dir="../assets",
       view=ft.AppView.WEB_BROWSER,
       host="0.0.0.0",
       port=int(os.environ.get("PORT", 8080))
   )
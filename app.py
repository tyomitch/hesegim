import calendar
from datetime import date
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for


DATA_FILES = {
    "courses": ("Courses", "courses.txt"),
    "branches": ("Branches", "branches.txt"),
    "teachers": ("Teachers", "teachers.txt"),
    "coordinators": ("Coordinators", "coordinators.txt"),
}


def read_nonempty_lines(file_path):
    if not file_path.exists():
        return []
    return [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def generate_schedule(source, coordinators, teachers):
    entries = []
    active_branches = 0
    total_courses = 0

    for line_number, line in enumerate(source.splitlines(), start=1):
        if not line.strip():
            continue
        branch, separator, activity = line.partition(":")
        branch, activity = branch.strip(), activity.strip()
        if not separator or not branch or not activity:
            raise ValueError(f"Line {line_number} must contain a branch and activity separated by a colon.")
        if activity == "אין פעילות":
            entries.append((branch, []))
            continue
        courses = [course.strip() for course in activity.split(",") if course.strip()]
        if not courses:
            raise ValueError(f"Line {line_number} does not contain any courses.")
        entries.append((branch, courses))
        active_branches += 1
        total_courses += len(courses)

    if active_branches > len(coordinators):
        raise ValueError("There are not enough coordinators for all active branches.")
    if total_courses > len(teachers):
        raise ValueError("There are not enough teachers for all courses.")

    blocks = []
    coordinator_index = 0
    teacher_index = 0
    for branch, courses in entries:
        if not courses:
            blocks.append(f"{branch}: אין פעילות")
            continue
        lines = [
            f"{branch}: (מרכז: {coordinators[coordinator_index]})",
            f"מתקיימים {len(courses)} קורסים:",
        ]
        coordinator_index += 1
        for course in courses:
            lines.append(f"{course} (מנחה: {teachers[teacher_index]})")
            teacher_index += 1
        blocks.append("\n".join(lines))

    blocks.append("\n".join(["מנחים בחופש:", *teachers[teacher_index:]]))
    blocks.append("\n".join(["מרכזים בחופש:", *coordinators[coordinator_index:]]))
    return "\n\n".join(blocks)


def parse_schedule(schedule):
    branch_lines = []
    blocks = [block for block in schedule.split("\n\n") if block.strip()]

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0] in ("מנחים בחופש:", "מרכזים בחופש:"):
            break

        branch, separator, _ = lines[0].partition(":")
        if len(lines) > 2:
            courses = []
            for course_line in lines[2:]:
                course, separator, _ = course_line.partition(" ")
                courses.append(course)
        else:
            courses = ['אין פעילות']

        branch_lines.append(f"{branch}: {', '.join(courses)}")

    return "\n\n".join(branch_lines)


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        today = date.today()
        calendar_builder = calendar.Calendar(firstweekday=6)
        schedule_directory = Path(app.root_path) / "data" / "schedule"
        existing_schedules = {path.stem for path in schedule_directory.iterdir()}
        months = []
        for offset in range(3):
            month_index = today.month - 1 + offset
            year = today.year + month_index // 12
            month_number = month_index % 12 + 1
            months.append(
                {
                    "year": year,
                    "number": month_number,
                    "name": date(year, month_number, 1).strftime("%B %Y"),
                    "weeks": calendar_builder.monthdatescalendar(year, month_number),
                }
            )
        return render_template(
            "index.html",
            today=today,
            months=months,
            existing_schedules=existing_schedules,
        )

    @app.route("/edit/<list>", methods=["GET", "POST"])
    def edit_data(list):
        if list not in DATA_FILES:
            abort(404)
        title, filename = DATA_FILES[list]
        file_path = Path(app.root_path) / "data" / filename

        if request.method == "POST":
            file_path.write_text(request.form.get("content", ""), encoding="utf-8")
            flash(f"{title} saved successfully.")
            return redirect(url_for("edit_data", list=list))

        lines = read_nonempty_lines(file_path)
        return render_template(
            "editor.html",
            title=title,
            lines=lines,
        )

    @app.get("/schedule/<date_string>")
    def schedule(date_string):
        try:
            selected_date = date.fromisoformat(date_string)
        except ValueError:
            abort(404)
        file_path = Path(app.root_path) / "data" / "schedule" / f"{selected_date:%Y%m%d}.txt"
        if not file_path.is_file():
            abort(404)
        return render_template(
            "schedule.html",
            title=f"Schedule for {selected_date:%B %d, %Y}",
            content=file_path.read_text(encoding="utf-8"),
            date_string=date_string,
        )

    @app.route("/generate/<date_string>", methods=["GET", "POST"])
    def generate(date_string):
        try:
            selected_date = date.fromisoformat(date_string)
        except ValueError:
            abort(404)
        if selected_date < date.today():
            abort(404)
        file_path = Path(app.root_path) / "data" / "schedule" / f"{selected_date:%Y%m%d}.txt"
        exists = file_path.is_file()
        data_directory = Path(app.root_path) / "data"
        error = None

        if request.method == "POST":
            content = request.form.get("content", "")
            try:
                generated_content = generate_schedule(
                    content,
                    read_nonempty_lines(data_directory / "coordinators.txt"),
                    read_nonempty_lines(data_directory / "teachers.txt"),
                )
            except ValueError as exception:
                error = str(exception)
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(generated_content, encoding="utf-8")
                return redirect(url_for("schedule", date_string=date_string))
        else:
            if exists:
                try:
                    content = parse_schedule(file_path.read_text(encoding="utf-8"))
                except ValueError as exception:
                    error = str(exception)
                    content = ""
            else:
                branches = read_nonempty_lines(data_directory / "branches.txt")
                content = "\n\n".join(f"{branch}: אין פעילות" for branch in branches)
            return render_template(
                "generate.html",
                title=f"Generate schedule for {selected_date:%B %d, %Y}",
                content=content,
                error=error,
            )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

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


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        today = date.today()
        calendar_builder = calendar.Calendar(firstweekday=6)
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
        return render_template("index.html", today=today, months=months)

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

        content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")
        line_count = sum(1 for line in normalized_content.split("\n") if line.strip())
        return render_template(
            "editor.html",
            title=title,
            content=content,
            filename=f"data/{filename}",
            line_count=line_count,
        )

    @app.get("/schedule/<date_string>")
    def schedule(date_string):
        try:
            selected_date = date.fromisoformat(date_string)
        except ValueError:
            abort(404)
        if selected_date < date.today():
            abort(404)
        return render_template("schedule.html", title=f"Schedule for {selected_date:%B %d, %Y}")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

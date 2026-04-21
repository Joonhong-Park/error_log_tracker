from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime
import io
import os
import sys
import webbrowser
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import db
import pg_sync

# PyInstaller 번들 실행 시 templates 경로 보정
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_base, "templates"))
app.secret_key = "error_logging_secret"

db.init_db()


@app.route("/")
def index():
    show_resolved = request.args.get("show_resolved", "0") == "1"
    rows = db.get_list(show_resolved=show_resolved)
    return render_template("index.html", rows=rows, show_resolved=show_resolved)


@app.route("/sync")
def sync():
    try:
        total, added = pg_sync.sync()
        flash(f"동기화 완료 — 전체 {total}건 중 신규 {added}건 추가", "success")
    except Exception as e:
        flash(f"동기화 실패: {e}", "error")
    return redirect(url_for("index"))


@app.route("/error/<file_uuid_id>", methods=["GET", "POST"])
def detail(file_uuid_id):
    row = db.get_one(file_uuid_id)
    if row is None:
        flash("해당 오류 건을 찾을 수 없습니다.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        root_cause = request.form.get("root_cause", "").strip()
        action_required = request.form.get("action_required", "").strip()
        resolved = request.form.get("resolved") == "1"
        db.update_memo(file_uuid_id, root_cause, action_required, resolved)
        flash("저장되었습니다.", "success")
        return redirect(url_for("index"))

    return render_template("detail.html", row=row)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        db.set_config({
            "PG_HOST":     request.form.get("PG_HOST", "").strip(),
            "PG_PORT":     request.form.get("PG_PORT", "5432").strip(),
            "PG_DBNAME":   request.form.get("PG_DBNAME", "").strip(),
            "PG_USER":     request.form.get("PG_USER", "").strip(),
            "PG_PASSWORD": request.form.get("PG_PASSWORD", "").strip(),
        })
        flash("설정이 저장되었습니다.", "success")
        return redirect(url_for("index"))
    cfg = db.get_config()
    return render_template("settings.html", cfg=cfg)


@app.route("/export")
def export():
    show_resolved = request.args.get("show_resolved", "0") == "1"
    rows = db.get_list(show_resolved=show_resolved)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "오류 목록"

    # 헤더 스타일
    header_font    = Font(bold=True, color="FFFFFF", size=10)
    header_fill    = PatternFill("solid", fgColor="1E3A5F")
    header_align   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border    = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    cell_align     = Alignment(vertical="top", wrap_text=True)

    headers = ["발생 시각", "파일명", "테이블명", "오류 내용", "원인 파악", "조치 필요 내용", "조치 여부", "완료 일시"]
    col_widths = [20, 30, 20, 50, 35, 35, 12, 20]

    for col_idx, (header, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font    = header_font
        cell.fill    = header_fill
        cell.alignment = header_align
        cell.border  = thin_border
        ws.column_dimensions[cell.column_letter].width = width

    ws.row_dimensions[1].height = 22

    # 데이터 행
    resolved_fill   = PatternFill("solid", fgColor="D4EDDA")
    unresolved_fill = PatternFill("solid", fgColor="FFF3CD")

    for row_idx, r in enumerate(rows, start=2):
        resolved_text = "완료" if r["resolved"] else "미완료"
        values = [
            r["create_ts"],
            r["file_name"],
            r["table_name"],
            r["error"],
            r["root_cause"] or "",
            r["action_required"] or "",
            resolved_text,
            r["resolved_at"] or "",
        ]
        row_fill = resolved_fill if r["resolved"] else unresolved_fill

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = cell_align
            cell.border    = thin_border
            # 조치여부 컬럼만 배경색 적용
            if col_idx == 7:
                cell.fill = row_fill

    # 첫 행 고정
    ws.freeze_panes = "A2"

    # 파일명에 날짜 포함
    filename = f"nifi_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    webbrowser.open("http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000)

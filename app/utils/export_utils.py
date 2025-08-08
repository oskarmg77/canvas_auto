from pathlib import Path
import csv

def rubric_to_csv(rubric_obj, dest: Path):
    """Recibe un objeto rubric de canvasapi y guarda CSV compatible Canvas."""
    max_ratings = max(len(c.ratings) for c in rubric_obj.data)
    headers = ["Rubric Name", "Criteria Name", "Criteria Description", "Criteria Points"]
    for i in range(max_ratings):
        headers += [f"Rating {i+1} Name", f"Rating {i+1} Description", f"Rating {i+1} Points"]

    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(headers)
        for c in rubric_obj.data:
            row = [rubric_obj.title, c["description"], c.get("long_description", ""), c["points"]]
            for r in c["ratings"]:
                row += [r["description"], r.get("long_description", ""), r["points"]]
            w.writerow(row)

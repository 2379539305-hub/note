import os, json

NOTE_DIRS = ["软件", "硬件"]

# collect all notes
notes = []
for d in NOTE_DIRS:
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        path = os.path.join(d, f)
        with open(path, "r", encoding="utf-8-sig") as fh:
            md = fh.read()
        title = f.replace(".md", "")
        notes.append({"cat": d, "title": title, "md": md})

# escape for JS single-quoted string
def js_escape(s):
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")

# build JS array
entries = []
for n in notes:
    entries.append('    {{ cat: "{}", title: "{}", md: \'{}\' }}'.format(
        n["cat"], n["title"], js_escape(n["md"])
    ))
learn_notes_js = "var learnNotes = [\n" + ",\n".join(entries) + "\n  ];"

# read template
with open("index_template.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("/* LEARNNOTES_PLACEHOLDER */", learn_notes_js)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Built with {} notes: {}".format(len(notes), [n["title"] for n in notes]))
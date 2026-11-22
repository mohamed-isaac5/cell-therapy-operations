from pathlib import Path
import sqlite3,html
R=Path(__file__).resolve().parent
with sqlite3.connect(R/'gtm.db') as c:rows=c.execute('select name from companies order by name').fetchall()
s='<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Fictional research workspace</title><link rel="stylesheet" href="/ui.css"><main><h1>Fictional research workspace</h1><p>This public candidate contains only invented sponsor and hospital records. No external research, verified roles, buyer intent or medical readiness is established.</p><p><a href="/home">Open the main workspace</a></p>'
for row in rows:s+='<section><h2>'+html.escape(row[0])+'</h2><p>Unknown evidence. Practice planning in Accounts.</p></section>'
(R/'index.html').write_text(s+'</main></html>')

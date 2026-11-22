"""Shared presentation-only shell. Does not access data or change workflows."""
import re
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parent
PAGES=[('/operations','Work & accounts'),('/dashboard','Overview'),('/','Company research'),('/hospitals','Hospital evidence'),('/committee','Buying committee'),('/crm','Account pipeline'),('/reviews','Message review'),('/report','Weekly review'),('/replies','Fictional replies')]
def polish_html(raw,path):
 text=raw.decode('utf-8')
 # All fonts remain local and deterministic, including the generated radar.
 text=re.sub(r'<link\b[^>]*fonts\.googleapis\.com[^>]*>','',text)
 assets='<link rel="stylesheet" href="/ui.css"><script defer src="/ui.js"></script><script defer src="/form-safety.js"></script><script defer src="/context-links.js"></script>'
 text=text.replace('</style>','</style>'+assets,1)
 links=''.join('<a href="'+url+'"'+(' aria-current="page"' if path==url else '')+'>'+label+'</a>' for url,label in PAGES)
 shell='<div style="padding:12px;background:#fff0cb;color:#333;text-align:center">FICTIONAL PUBLIC DEMO. All sponsor and hospital records are invented.</div><a class="ui-skip" href="#workspace-main">Skip to workspace</a><div class="ui-shell" role="banner"><div class="ui-mast"><a class="ui-brand" href="/home"><span class="ui-mark" aria-hidden="true">C</span><span>Cell Therapy <b>Operations</b></span></a><span class="ui-local">ADVANCED SOURCE TOOL <span aria-hidden="true">/</span> <a href="/home">Return to workspace →</a></span></div><nav class="ui-nav" aria-label="Workspaces">'+links+'</nav></div>'
 shell=shell.replace('<nav class="ui-nav"','<button class="ui-menu" type="button" aria-expanded="false" aria-controls="workspace-nav">Workspaces</button><nav id="workspace-nav" class="ui-nav"')
 # Some legacy documents omit body. Insert before the first visible element.
 if '<body' in text:
  text=re.sub(r'(<body[^>]*>)',lambda m:m[0]+shell,text,count=1)
 else:
  end=text.find('</style>')+len('</style>')+len(assets)
  text=text[:end]+'<body>'+shell+text[end:]
  text=text.replace('</html>','</body></html>')
 text=re.sub(r'<body([^>]*)>',lambda m:'<body data-workspace="'+escape(path,quote=True)+'"'+m[1]+'>',text,count=1)
 text=re.sub(r'<main\b([^>]*)>',r'<main id="workspace-main" tabindex="-1"\1>',text,count=1)
 return text.encode('utf-8')

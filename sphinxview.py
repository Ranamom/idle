"""
Text widget specialized to display the HTML formatted Python documentation
as generated by Sphinx.

The renderer is fragile enough that you won't likely get very far if you
feed it anything but the IDLE help file.
"""

from tkinter import *
from tkinter import ttk
import tkinter.font
from html.parser import HTMLParser
from os.path import abspath, dirname, join, isfile


class SphinxHTMLViewer(Text):

    def __init__(self, parent, filename):
        Text.__init__(self, parent, wrap='word', highlightthickness=0, 
                      padx=10, spacing1='2', spacing2='2', borderwidth=0)
        self.p = SphinxHTMLParser(self)
        with open(filename, encoding='utf-8') as f:
            contents = f.read()
        self.p.feed(contents)
        normalfont = self.findfont(['TkDefaultFont', 'arial', 'helvetica'])
        fixedfont = self.findfont(['TkFixedFont', 'monaco', 'courier'])
        self['font'] = (normalfont, 12)
        self.tag_configure('em', font=(normalfont, 12, 'italic'))
        self.tag_configure('h1', font=(normalfont, 20, 'bold'))
        self.tag_configure('h2', font=(normalfont, 18, 'bold'))
        self.tag_configure('h3', font=(normalfont, 15, 'bold'))
        self.tag_configure('pre', font=(fixedfont, 12))
        self.tag_configure('preblock', font=(fixedfont, 12), lmargin1=25,
                borderwidth=1, relief='solid', background='#eeffcc')
        self.tag_configure('l1', lmargin1=25, lmargin2=25)
        self.tag_configure('l2', lmargin1=50, lmargin2=50)
        self.tag_configure('l3', lmargin1=75, lmargin2=75)
        self.tag_configure('l4', lmargin1=100, lmargin2=100)
        self['state'] = 'disabled'

    def findfont(self, names):
        for f in names:
            if f.lower() in [x.lower() for x in tkinter.font.names(root=self)]:
                font = tkinter.font.Font(name=f, exists=True, root=self)
                return font.actual()['family']
            elif f.lower() in [x.lower() for x in tkinter.font.families()]:
                return f
                
    def contents_widget(self, parent=None):
        try:
            w = ttk.Menubutton(self if parent is None else parent, text='TOC')
        except Exception:
            w = Menubutton(self if parent is None else parent, text='TOC')
        m = Menu(w, tearoff=False)
        for x in self.p.contents:
            tag, lbl = x
            m.add_command(label=lbl, command=lambda mark=tag:self.see(mark))
        w['menu'] = m
        return w


class SphinxHTMLParser(HTMLParser):
    def __init__(self, t):
        HTMLParser.__init__(self)
        self.t = t               # text widget we're rendering into
        self.tags = ''           # current text tags to apply
        self.show = False        # used so we exclude page navigation
        self.hdrlink = False     # used so we don't show header links
        self.level = 0           # indentation level
        self.pre = False         # displaying preformatted text
        self.hprefix = ''        # strip e.g. '25.5' from headings
        self.nested_dl = False   # if we're in a nested <dl>
        self.simplelist = False  # simple list (no double spacing)
        self.tocid = 1           # used to generate table of contents entries
        self.contents = []       # map toc ids to titles
        self.data = ''           # to record data within header tags for toc

    def indent(self, amt=1):
        self.level += amt
        self.tags = '' if self.level == 0 else 'l'+str(self.level)

    def handle_starttag(self, tag, attrs):
        class_ = ''
        for a, v in attrs:
            if a == 'class':
                class_ = v
        s = ''
        if tag == 'div' and class_ == 'section':
            self.show = True    # start of main content
        elif tag == 'div' and class_ == 'sphinxsidebar':
            self.show = False   # end of main content
        elif tag == 'p' and class_ != 'first':
            s = '\n\n'
        elif tag == 'span' and class_ == 'pre':
            self.tags = 'pre'
        elif tag == 'span' and class_ == 'versionmodified':
            self.tags = 'em'
        elif tag == 'em':
            self.tags = 'em'
        elif tag in ['ul', 'ol']:
            if class_.find('simple') != -1:
                s = '\n'
                self.simplelist = True
            else:
                self.simplelist = False
            self.indent()
        elif tag == 'dl':
            if self.level > 0:
                self.nested_dl = True
        elif tag == 'li':
            s = '\n* ' if self.simplelist else '\n\n* '
        elif tag == 'dt':
            s = '\n\n' if not self.nested_dl else '\n'  # avoid extra line
            self.nested_dl = False
        elif tag == 'dd':
            self.indent()
            s = '\n'
        elif tag == 'pre':
            self.pre = True
            if self.show:
                self.t.insert('end', '\n\n')
            self.tags = 'preblock'
        elif tag == 'a' and class_ == 'headerlink':
            self.hdrlink = True
        elif tag == 'h1':
            self.tags = tag
        elif tag in ['h2', 'h3']:
            if self.show:
                self.data = ''
                self.t.mark_set('toc'+str(self.tocid),
                                self.t.index('end-1line'))
                self.t.insert('end', '\n\n')
            self.tags = tag
        if self.show:
            self.t.insert('end', s, self.tags)

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'span', 'em']:
            self.indent(0)  # clear tag, reset indent
            if self.show and tag in ['h2', 'h3']:
                title = self.data
                self.contents.append(('toc'+str(self.tocid), title))
                self.tocid += 1
        elif tag == 'a':
            self.hdrlink = False
        elif tag == 'pre':
            self.pre = False
            self.tags = ''
        elif tag in ['ul', 'dd', 'ol']:
            self.indent(amt=-1)

    def handle_data(self, data):
        if self.show and not self.hdrlink:
            d = data if self.pre else data.replace('\n', ' ')
            if self.tags == 'h1':
                self.hprefix = d[0:d.index(' ')]
            if self.tags in ['h1', 'h2', 'h3'] and self.hprefix != '':
                if d[0:len(self.hprefix)] == self.hprefix:
                    d = d[len(self.hprefix):].strip()
                self.data += d
            self.t.insert('end', d, self.tags)


class SphinxHTMLViewerWindow(Toplevel):

    def __init__(self, parent, filename, title, show_contents=True):
        Toplevel.__init__(self, parent)
        self.wm_title(title)        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        v = SphinxHTMLViewer(self, filename)
        s = Scrollbar(self, command=v.yview)
        v['yscrollcommand'] = s.set
        v.grid(column=1, row=0, sticky='nsew')
        s.grid(column=2, row=0, sticky='ns')
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        if show_contents:
            self['background'] = v['background']
            toc = v.contents_widget(parent=self)
            toc.grid(column=0, row=0, sticky='nw', pady=5, padx=[5,0])


if __name__ == '__main__':
    root = Tk()
    dir = abspath(dirname(__file__))
    if not isfile(join(dir, 'idle.html')):
        dir = join(abspath(dirname(dirname(dirname(__file__)))), 
                   'Doc', 'build', 'html', 'library')
    w = SphinxHTMLViewerWindow(root, join(dir, 'idle.html'), 'IDLE Help')
    root.mainloop()
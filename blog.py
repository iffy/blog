"""
Blogger publisher that processes files with Jinja and Pygments
(for syntax highlighting).
"""
import gdata
from gdata import service
from twisted.python import usage
from twisted.python.filepath import FilePath
import atom
import sys
import getpass
import re
import subprocess
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


from jinja2 import nodes, Environment, FileSystemLoader
from jinja2.ext import Extension

class ShellExtension(Extension):
    """
    Executes shell commands and gets output.
    """
    
    tags = set(['shell'])
    
    def __init__(self, environment):
        super(ShellExtension, self).__init__(environment)


    def parse(self, parser):
        lineno = parser.stream.next().lineno
        args = [parser.parse_expression()]
        body = parser.parse_statements(['name:endshell'], drop_needle=True)
        return nodes.CallBlock(self.call_method('_shell', args),
                               [], [], body).set_lineno(lineno)

    def _shell(self, args, caller):
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd='.')
        stdin = caller()
        stdout, _ = p.communicate(stdin)
        return stdout



class PygmentsExtension(Extension):
    """
    http://larrymyers.com/articles/3/creating-a-jinja-pygments-extension-for-code-highlighting
    """

    tags = set(['code'])
    
    def __init__(self, environment):
        super(PygmentsExtension, self).__init__(environment)
        
    
    def parse(self, parser):
        lineno = parser.stream.next().lineno
        args = [parser.parse_expression()]
        
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.List([]))
        body = parser.parse_statements(['name:endcode'], drop_needle=True)
        return nodes.CallBlock(self.call_method('_highlight', args),
                               [], [], body).set_lineno(lineno)

    def _highlight(self, language, hl_lines, caller):
        lexer = get_lexer_by_name(language, stripall=False)
        formatter = HtmlFormatter(linenos=False, cssclass="code " + language, hl_lines=hl_lines)
        result = highlight(caller(), lexer, formatter)
        return result


jenv = Environment(extensions=[PygmentsExtension, ShellExtension])

def getPosts(bservice, blog_id, title=None):
    """
    Get a list of posts
    
    @param title: If given, only return posts with this title.
    """
    query = service.Query()
    query.feed = '/feeds/' + blog_id + '/posts/default'
    feed = bservice.Get(query.ToUri())
    ret = []
    for entry in feed.entry:
        if not title or (title and entry.title.text == title):
            ret.append({
                'title': entry.title.text,
                'content': entry.content.text,
                'updated': entry.updated.text,
                'entry': entry,
            })
    return ret


def makePost(bservice, blog_id, title, content, draft=False):
    entry = gdata.GDataEntry()
    entry.title = atom.Title('xhtml', title)
    entry.content = atom.Content(content_type='html', text=content)
    
    if draft:
        control = atom.Control()
        control.draft = atom.Draft(text='yes')
        entry.control = control
    
    return bservice.Post(entry, '/feeds/%s/posts/default' % blog_id)


def updatePost(bservice, post, title=None, content=None, draft=None):
    if title is not None:
        post.title = atom.Title('xhtml', title)
    if content is not None:
        post.content = atom.Content(content_type='html', text=content)
    if draft is not None:
        if draft:
            draft = 'yes'
        else:
            draft = 'no'
        post.control.draft = atom.Draft(text=draft)
    return bservice.Put(post, post.GetEditLink().href)


def getBlogs(bservice):
    query = service.Query()
    query.feed = '/feeds/default/blogs'
    feed = bservice.Get(query.ToUri())
    
    ret = []
    for entry in feed.entry:
        ret.append({
            'title': entry.title.text,
            'id': entry.GetSelfLink().href.split('/')[-1],
            'entry': entry,
        })
    return ret


def makeService(username=None):
    if not username:
        username = raw_input('username? ')
    password = getpass.getpass('%s password? ' % username)
    bservice = service.GDataService(username, password)
    bservice.source = 'clBlogger-0.1'
    bservice.service = 'blogger'
    bservice.account_type = 'GOOGLE'
    bservice.server = 'www.blogger.com'
    bservice.ProgrammaticLogin()
    return bservice



class FormatError(Exception):
    pass


def renderFile(filename, include_dirs=None):
    """
    Render a file for posting.  Everything until the first --- on a line by
    itself is configuration (title, tags, etc...)
    """
    include_dirs = include_dirs or []
    jenv.loader = FileSystemLoader(include_dirs)
    fh = open(filename, 'r')
    chunks = fh.read().split('\n---\n', 1)
    if len(chunks) == 1:
        raise FormatError('There must be a --- separating header data '
                          'from the content of the post')
    
    # extract headers
    headers = {}
    for line in chunks[0].split('\n'):
        key, value = line.strip().split(':', 1)
        headers[key] = value
    
    # render body
    body = chunks[1]
    
    # blogger adds all kinds of line breaks, so we're going to
    # remove extra spaces.  XXX this may cause problems for code
    # blocks.  There's supposedly a configuration option for 
    # blogger that turns off the proliferation of <br /> tags,
    # but I haven't found it yet.
    template = jenv.from_string(body)
    body = template.render()
    r_pre = re.compile('(<pre(?:\s.*?)?>|</pre>|'
                       '<code(?:\s.*?)?>|</code>)')
    parts = r_pre.split(body)
    stack = []
    body_parts = []
    for part in parts:
        if stack:
            body_parts.append(part)
        else:
            body_parts.append(part.replace('\n',''))
        if part.startswith('<pre') or part.startswith('<code'):
            stack.append(part)
        elif part.startswith('</pre') or part.startswith('</code'):
            stack.pop()
    body = ''.join(body_parts)
    return {
        'headers': headers,
        'body': body,
    }



class ListBlogsOptions(usage.Options):

    optParameters = [
        ['username', 'u', None, "Blogger username"],
    ]


class RenderOptions(usage.Options):


    synopsis = '[options] sourcefile'


    optParameters = [
        ['template', 't', None, "Base template to insert rendered"
                                "page into.  The base template "
                                "will be passed title and "
                                "content variables."],
    ]
    
    def __init__(self):
        usage.Options.__init__(self)
        self['include'] = []


    def opt_include(self, path):
        """
        Path from which to load sourced templates.  May be specified multiple
        times.  The directory containing the source file will always be
        available.
        """
        self['include'].append(path)
    opt_i = opt_include


    def parseArgs(self, source):
        self['source'] = source


    def postOptions(self):
        self['include'].append(FilePath(self['source']).parent().path)



class PostOptions(usage.Options):


    synopsis = '[options] sourcefile'

    optFlags = [
        ['draft', 'd', "This post is a draft only"],
        ['update', None, "Update a post with the same name"],
    ]
    
    optParameters = [
        ['username', 'u', None, "Blogger username"],
        ['blog', 'b', None, "Blog title; if not given, blogs will be listed"],
    ]

    def __init__(self):
        usage.Options.__init__(self)
        self['include'] = []


    def opt_include(self, path):
        """
        Path from which to load sourced templates.  May be specified multiple
        times.
        """
        self['include'].append(path)
    opt_i = opt_include


    def parseArgs(self, source):
        self['source'] = source


    def postOptions(self):
        self['include'].append(FilePath(self['source']).parent().path)



class Options(usage.Options):

    optParameters = [
        ['config', 'c', '.blogrc', "Config file to read parameters from"],
    ]

    subCommands = [
        ['render', None, RenderOptions, "Render a file"],
        ['post', None, PostOptions, "Render a file and post to "
                                    "blogger"],
        ['ls-blogs', None, ListBlogsOptions, "List user's blogs"],
    ]

    def postOptions(self):
        """
        Fill in values from the config file if there is one.
        """
        sub = self.subOptions
        flags = []
        if getattr(sub, 'optFlags', None):
            flags = [x[0] for x in sub.optFlags]
        config = FilePath(self['config'])
        if config.exists():
            for line in config.getContent().strip().split('\n'):
                if not line:
                    continue
                parts = line.split(':')
                name = parts[0]
                value = ':'.join(parts[1:])
                if name in flags:
                    sub[name] = 1
                elif name in sub and sub[name] is None:
                    sub[name] = value
        


def render(options):
    """
    Renders a file to stdout surrounding it by a base template
    if supplied
    """
    rendered = renderFile(options['source'], options['include'])
    
    # mimick blogger's overuse of <br />
    rendered['body'] = rendered['body'].replace('\n', '<br />')
    if options['template']:
        base = FilePath(options['template'])
        t = jenv.from_string(base.getContent())
        print t.render({
            'title': rendered['headers']['title'],
            'content': rendered['body'],
        })
    else:
        print rendered['body']


def renderAndPost(options):
    """
    Renders a file and posts it to blogger.
    """
    rendered = renderFile(options['source'], options['include'])
    title = rendered['headers']['title']

    s = makeService(options['username'])
    
    # convert blog title to id
    blog = [x for x in getBlogs(s) if x['title'] == options['blog']][0]
    blog_id = blog['id']
    
    # compare title to check for dupes
    posts = getPosts(s, blog_id, title=title)
    if len(posts) > 1 or (posts and not options['update']):
       print 'Posts with that title already exist.  Use --update if you want'
       sys.exit(2)
    
    if posts:
        # update it
        print 'updating...'
        result = updatePost(s, posts[0]['entry'], title, rendered['body'],
                            options['draft'])
        print 'Updated'
    else:
        # post it
        print 'posting...'
        result = makePost(s, blog_id, title, rendered['body'], options['draft'])
        print 'Posted'


def listBlogs(options):
    s = makeService(options['username'])
    blogs = getBlogs(s)
    for blog in blogs:
        print '  ' + blog['title']



if __name__ == '__main__':
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError, e:
        print '%s  Use --help' % e
        sys.exit(2)
    
    if options.subCommand == 'post':
        renderAndPost(options.subOptions)
    elif options.subCommand == 'render':
        render(options.subOptions)
    elif options.subCommand == 'ls-blogs':
        listBlogs(options.subOptions)
    else:
        print options
        sys.exit(1)
    

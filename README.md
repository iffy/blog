blog
====

Script to render code snippets and publish to Blogger

Depends on these libraries (you can probably install them with `pip`):

    gdata
    Twisted
    pygments
    jinja2

Usage:

    python blog.py --help
    python blog.py ls-blogs
    python blog.py render myfile.html > rendered.html
    python blog.py post myfile.html


All the commands read options from a config file (default `./.blogrc`).  My config file looks like this:

    username:mygmailusername
    template:base.html
    blog:My Blog Name
    draft:true


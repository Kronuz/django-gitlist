# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import patterns, url


# A Git branch name can not:
#   1. They can include slash / for hierarchical (directory) grouping,
#      but no slash-separated component can begin with a dot . or end
#      with the sequence .lock
#   2. They must contain at least one /. This enforces the presence of a
#      category like heads/, tags/ etc. but the actual names are not
#      restricted. If the --allow-onelevel option is used, this rule is
#      waived
#   3. They cannot have two consecutive dots .. anywhere
#   4. They cannot have ASCII control characters (i.e. bytes whose
#      values are lower than \040, or \177 DEL), space, tilde ~, caret
#      ^, or colon : anywhere
#   5. They cannot have question-mark ?, asterisk *, or open bracket [
#      anywhere. See the --refspec-pattern option below for an exception
#      to this rule
#   6. They cannot begin or end with a slash / or contain multiple
#      consecutive slashes (see the --normalize option below for an
#      exception to this rule)
#   7. They cannot end with a dot .
#   8. They cannot contain a sequence @{
#   9. They cannot contain a \
BRANCH_PATTERN = r'''(?P<branch>(?!/|.*(?:[/.]\.|//|@\{|\\))[%s]+(?<!\.lock)(?<![/.]))''' % '^\040\177 ~^:?*['

FORMATS = {
    'repo': r'(?P<repo>[-_\w]+)',
    'branch': BRANCH_PATTERN,
    'commitishPath': r'(?P<commitishPath>.+)',
    'commit': r'(?P<commit>[a-f0-9^]+)',
    'format': r'(?P<format>(zip|tar))',
    'page': r'(?P<page>\d+)',
}

urlpatterns = patterns('gitlist.views',
    # Main
    url(r'^$', 'homepage', name='homepage'),
    url(r'^{repo}/stats/$'.format(**FORMATS), 'stats', name='stats'),
    url(r'^{repo}/stats/{branch}/$'.format(**FORMATS), 'stats', name='stats'),
    url(r'^{repo}/rss/$'.format(**FORMATS), 'rss', name='rss'),
    url(r'^{repo}/{branch}/rss/$'.format(**FORMATS), 'rss', name='rss'),
    # Network
    url(r'^{repo}/network/{commitishPath}/{page}.json$'.format(**FORMATS), 'network_data', name='network_data'),
    url(r'^{repo}/network/$'.format(**FORMATS), 'network', name='network'),
    url(r'^{repo}/network/{commitishPath}$'.format(**FORMATS), 'network', name='network'),
    # Blob
    url(r'^{repo}/blob/{commitishPath}$'.format(**FORMATS), 'blob', name='blob'),
    url(r'^{repo}/raw/{commitishPath}$'.format(**FORMATS), 'blob_raw', name='blob_raw'),
    # Commit
    url(r'^{repo}/commits/search/$'.format(**FORMATS), 'search', name='search'),
    url(r'^{repo}/commits/$'.format(**FORMATS), 'commits', name='commits'),
    url(r'^{repo}/commits/{branch}/search/$'.format(**FORMATS), 'searchcommits', name='searchcommits'),
    url(r'^{repo}/commits/{commitishPath}$'.format(**FORMATS), 'commits', name='commits'),
    url(r'^{repo}/commit/{commitishPath}$'.format(**FORMATS), 'commit', name='commit'),
    url(r'^{repo}/blame/{commitishPath}$'.format(**FORMATS), 'blame', name='blame'),
    # Tree
    url(r'^{repo}/tree/$'.format(**FORMATS), 'tree', name='tree'),
    url(r'^{repo}/tree/{branch}/search/$'.format(**FORMATS), 'searchbranch', name='searchbranch'),
    url(r'^{repo}/tree/{commitishPath}/$'.format(**FORMATS), 'tree', name='tree'),
    url(r'^{repo}/{format}ball/{branch}/$'.format(**FORMATS), 'archive', name='archive'),
    url(r'^{repo}/{branch}/$'.format(**FORMATS), 'branch', name='branch'),
    url(r'^{repo}/$'.format(**FORMATS), 'repository', name='repository'),
)

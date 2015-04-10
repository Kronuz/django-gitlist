# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
import re
import json
import datetime
import warnings
from hashlib import md5
from cStringIO import StringIO

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, CompatibleStreamingHttpResponse, Http404
from django.shortcuts import render

from .const import DEFAULT_FILE_TYPES, DEFAULT_BINARY_TYPES
from .utils import get_repository_from_name, parse_commitish_path, get_readme

COMMITS_PER_PAGE = 15
SEARCH_PER_PAGE = 50
STREAM_CHUNK_SIZE = 4096


class WrappedDiff(object):
    CHUNK_RE = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, diff, encoding):
        self.diff = diff
        self.encoding = encoding

    def __getattr__(self, attr):
        return getattr(self.diff, attr)

    @property
    def file(self):
        if self.diff.b_blob:
            return self.diff.b_blob.path
        if self.diff.a_blob:
            return self.diff.a_blob.path
        return 'unknown'

    @property
    def index(self):
        return "index %s..%s" % (self.diff.a_blob.hexsha[:7], self.diff.b_blob.hexsha[:7])

    def getLines(self):
        lines = []
        if self.diff.new_file:
            lines.append(dict(
                getType='chunk',
                getNumOld='',
                getNumNew='',
                getLine="new file, mode %o" % (self.diff.b_mode,)
            ))
        elif self.diff.deleted_file:
            lines.append(dict(
                getType='chunk',
                getNumOld='',
                getNumNew='',
                getLine="file deleted"
            ))
        elif self.diff.renamed:
            lines.append(dict(
                getType='chunk',
                getNumOld='',
                getNumNew='',
                getLine="file renamed from %s to %s" % (self.diff.rename_from, self.diff.rename_to,)
            ))

        for line in self.diff.diff.decode(self.encoding).split('\n'):
            if line[:4] in ('', '--- ', '+++ '):
                continue
            chunk = self.CHUNK_RE.match(line)
            if chunk:
                getType = 'chunk'
                num_old = int(chunk.group(1))
                num_new = int(chunk.group(3))
                getNumOld = '...'
                getNumNew = '...'
            elif line[0] == '-':
                getType = 'old'
                getNumOld = num_old
                getNumNew = ''
                num_old += 1
            elif line[0] == '+':
                getType = 'new'
                getNumOld = ''
                getNumNew = num_new
                num_new += 1
            elif line[0] == ' ':
                getType = None
                getNumOld = num_old
                getNumNew = num_new
                num_old += 1
                num_new += 1
            else:
                continue
            lines.append(dict(
                getType=getType,
                getNumOld=getNumOld,
                getNumNew=getNumNew,
                getLine=line,
            ))
        return lines


class WrappedCommit(object):
    def __init__(self, commit, paths=None):
        self.commit = commit
        self.paths = paths

    def __getattr__(self, attr):
        return getattr(self.commit, attr)

    @property
    def commiterDate(self):
        return datetime.datetime.fromtimestamp(self.commit.committed_date)

    @property
    def commiter(self):
        return self.commit.committer

    @property
    def date(self):
        return datetime.datetime.fromtimestamp(self.commit.authored_date)

    @property
    def shortHash(self):
        return self.commit.hexsha[:7]

    @property
    def hash(self):
        return self.commit.hexsha

    @property
    def changedFiles(self):
        return self.commit.stats.total['files']

    @property
    def diffs(self):
        if self.commit.parents:
            parent = self.commit.parents[0]
            diffs = parent.diff(self.commit, paths=self.paths, create_patch=True)
            diffs = [WrappedDiff(diff, self.commit.encoding) for diff in diffs]
        else:
            diffs = []
        return diffs

    @property
    def message(self):
        return self.commit.summary

    @property
    def body(self):
        return self.commit.message.split('\n', 1)[1].strip()


# Main
def homepage(request):
    repositories = []
    for repo in settings.GITLIST_REPOSITORIES:
        try:
            repository = get_repository_from_name(repo)
        except Http404 as e:
            warnings.warn("Repository error: %s" % e)
            continue
        repositories.append(dict(
            name=repo,
            description=repository.description
        ))
    return render(request, 'index.html', {
        'repositories': repositories,
    })


def stats(request, repo, branch=''):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(branch, repository)
    branches = repository.branches
    tags = repository.tags

    authors = {}
    for c in repository.iter_commits(branch, paths=path):
        try:
            authors[c.author] += 1
        except KeyError:
            authors[c.author] = 1

    extensions = {}
    total_files = 0
    total_size = 0
    for blob in repository.tree().traverse():
        if blob.type == 'blob':
            total_files += 1
            total_size += blob.size
            _, ext = os.path.splitext(blob.name)
            if ext:
                try:
                    extensions[ext] += 1
                except KeyError:
                    extensions[ext] = 1

    stats = dict(
        extensions=sorted(extensions.items(), key=lambda o: o[1], reverse=True),
        files=total_files,
        size=total_size,
    )

    authors = sorted((dict(
        email=a.email,
        name=a.name,
        commits=c,
    ) for a, c in authors.items()), key=lambda o: o['commits'], reverse=True)

    breadcrumbs = [{'dir': 'Statistics', 'path': ''}]
    return render(request, 'stats.html', {
        'page': 'stats',
        'repo': repo,
        'branch': branch,
        'branches': branches,
        'tags': tags,
        'stats': stats,
        'authors': authors,
        'breadcrumbs': breadcrumbs,
    })


def rss(request, repo, branch=None):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(branch, repository)

    try:
        page = int(request.GET.get('page', 0))
    except ValueError:
        page = 0

    commits = []
    for commit in repository.iter_commits(branch, paths=path, max_count=COMMITS_PER_PAGE, skip=page * COMMITS_PER_PAGE):
        commit = WrappedCommit(commit)
        commits.append(commit)

    response = render(request, 'rss.html', {
        'repo': repo,
        'branch': branch,
        'commits': commits,
    }, content_type='application/rss+xml')
    return response


# Blob
def blob(request, repo, commitishPath):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    branches = repository.branches
    tags = repository.tags

    tree = repository.tree(branch)
    if path:
        split_path = path.split('/')
        for part in split_path:
            tree = tree[part]
    else:
        split_path = []

    blob = tree.data_stream.read
    file = tree.name
    fileType = DEFAULT_FILE_TYPES.get(os.path.splitext(tree.name)[1], '')

    breadcrumbs = []
    for i, b in enumerate(split_path):
        path = '/'.join(split_path[:i + 1])
        breadcrumbs.append({
            'dir': b,
            'path': reverse('tree', kwargs=dict(repo=repo, commitishPath=commitishPath)),
        })

    return render(request, 'file.html', {
        'page': 'files',
        'file': file,
        'fileType': fileType,
        'blob': blob,
        'repo': repo,
        'branch': branch,
        'branches': branches,
        'tags': tags,
        'breadcrumbs': breadcrumbs,
    })


def blob_raw(request, repo, commitishPath):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    tree = repository.tree()

    blob = tree[path]
    f = blob.data_stream
    response = CompatibleStreamingHttpResponse(iter(lambda: f.read(STREAM_CHUNK_SIZE), b''),
                                               content_type=blob.mime_type)

    _, ext = os.path.splitext(blob.name)
    if ext in DEFAULT_BINARY_TYPES:
        response["Content-Disposition"] = 'attachment; filename="{file}"'.format(file=blob.name)
        response["Content-Type"] = 'application/octet-stream'
    else:
        response["Content-Type"] = 'text/plain'
    response["Content-Length"] = blob.size
    return response


# Commit
def search(request, repo):
    url = reverse('searchcommits', kwargs=dict(repo=repo, branch='master'))
    return HttpResponseRedirect(url)


def commits(request, repo, commitishPath=None):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    branches = repository.branches
    tags = repository.tags

    try:
        page = int(request.GET.get('page', 0))
    except ValueError:
        page = 0

    total_commits = sum(1 for _ in repository.iter_commits(branch, paths=path))
    last = (total_commits + COMMITS_PER_PAGE - 1) / COMMITS_PER_PAGE - 1
    pager = dict(previous=max(0, page - 1), current=page, next=min(page + 1, last), last=last)

    categorized = {}
    commits = []
    for commit in repository.iter_commits(branch, paths=path, max_count=COMMITS_PER_PAGE, skip=page * COMMITS_PER_PAGE):
        commit = WrappedCommit(commit)
        date = commit.commiterDate
        grouped_date = datetime.datetime(year=date.year, month=date.month, day=date.day)
        try:
            dated_commits = categorized[grouped_date]
        except KeyError:
            dated_commits = []
            categorized[grouped_date] = dated_commits
            commits.append((grouped_date, dated_commits))
        dated_commits.append(commit)

    if request.is_ajax():  # FIXME: This should be is_xml()
        template = 'commits_list.html'
    else:
        template = 'commits.html'

    return render(request, template, {
        'page': 'commits',
        'pager': pager,
        'repo': repo,
        'branch': branch,
        'branches': branches,
        'tags': tags,
        'commits': commits,
        'file': path,
        'breadcrumbs': [{'dir': 'Commit history', 'path': ''}],
    })


def searchcommits(request, repo, branch):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(branch, repository)
    branches = repository.branches
    tags = repository.tags

    query = request.REQUEST.get('query', '')
    try:
        page = int(request.GET.get('page', 0))
    except ValueError:
        page = 0

    total = 0
    total_commits = 0
    categorized = {}
    commits = []
    for commit in repository.iter_commits(branch, paths=path):
        if query in commit.message:
            if total >= page * SEARCH_PER_PAGE:
                commit = WrappedCommit(commit)
                date = commit.commiterDate
                grouped_date = datetime.datetime(year=date.year, month=date.month, day=date.day)
                try:
                    dated_commits = categorized[grouped_date]
                except KeyError:
                    dated_commits = []
                    categorized[grouped_date] = dated_commits
                    commits.append((grouped_date, dated_commits))
                dated_commits.append(commit)
                total_commits += 1
            if total_commits > SEARCH_PER_PAGE:
                break
            total += 1

    file = None
    return render(request, 'searchcommits.html', {
        'page': 'searchcommits',
        'repo': repo,
        'branch': branch,
        'file': file,
        'commits': commits,
        'branches': branches,
        'tags': tags,
        'query': query,
        'breadcrumbs': [{'dir': 'Commits search results for: {query}'.format(query=query), 'path': ''}],
    })


def commit(request, repo, commitishPath=None):
    branch = 'master'
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)

    commit = WrappedCommit(repository.commit(branch), paths=path)

    breadcrumbs = [{'dir': "{commit}".format(commit=commit.hash), 'path': reverse('commit', kwargs=dict(repo=repo, commitishPath=branch))}]
    if path:
        breadcrumbs.append({'dir': path, 'path': ''})

    return render(request, 'commit.html', {
        'page': 'commits',
        'branch': branch,
        'repo': repo,
        'commit': commit,
        'breadcrumbs': breadcrumbs,
    })


def blame(request, repo, commitishPath):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    branches = repository.branches
    tags = repository.tags

    blames = []
    for blame in repository.blame(branch, path):
        blames.append(dict(
            line='\n'.join(blame[1]),
            commit=blame[0].hexsha,
            commitShort=blame[0].hexsha[:8],
        ))

    return render(request, 'blame.html', {
        'page': 'commits',
        'file': path,
        'repo': repo,
        'branch': branch,
        'branches': branches,
        'tags': tags,
        'blames': blames,
        'breadcrumbs': [{'dir': 'Blame', 'path': ''}],
    })


# Tree
def tree(request, repo, commitishPath=''):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    branches = repository.branches
    tags = repository.tags

    readme = None
    tree = repository.tree(branch)
    readme = get_readme(tree)
    if path:
        split_path = path.split('/')
        for part in split_path:
            tree = tree[part]
            readme = get_readme(tree) or readme
        parent = '/'.join(split_path[:-1])
    else:
        split_path = []
        parent = None
    files = tree.trees + tree.blobs

    breadcrumbs = []
    for i, b in enumerate(split_path):
        path = '/'.join(split_path[:i + 1])
        breadcrumbs.append({
            'dir': b,
            'path': reverse('tree', kwargs=dict(repo=repo, commitishPath=commitishPath)),
        })

    return render(request, 'tree.html', {
        'page': 'files',
        'files': files,
        'repo': repo,
        'branch': branch,
        'path': path,
        'parent': parent,
        'branches': branches,
        'tags': tags,
        'readme': readme,
        'breadcrumbs': breadcrumbs,
    })


def searchbranch(request, repo, branch):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(branch, repository)
    branches = repository.branches
    tags = repository.tags

    query = request.REQUEST.get('query', '')
    try:
        page = int(request.GET.get('page', 0))
    except ValueError:
        page = 0

    total = 0
    total_results = 0
    results = []
    for blob in repository.tree().traverse():
        if blob.type == 'blob':
            content = blob.data_stream.read()
            if query.encode('utf-8') in content:
                content = b'\n'.join(b'%d - %s' % (i + 1, c) for i, c in enumerate(content.split(b'\n')))
                if total >= page * SEARCH_PER_PAGE:
                    regex = r'((?:.*\n){0,2})(\d+)(.*)(%s)(.*(?:\n.*){0,2})' % query
                    for m in re.findall(regex.encode('utf-8'), content):
                        results.append(dict(
                            file=blob.path,
                            line=int(m[1]),
                            match=(m[0] + m[1] + m[2], m[3], m[4]),
                        ))
                total_results += 1
            if total_results > SEARCH_PER_PAGE:
                break
            total += 1

    path = None
    breadcrumbs = None
    return render(request, 'search.html', {
        'page': 'files',
        'results': results,
        'repo': repo,
        'branch': branch,
        'path': path,
        'branches': branches,
        'tags': tags,
        'query': query,
        'breadcrumbs': breadcrumbs,
    })


def archive(request, repo, format, branch):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(branch, repository)

    commit = repository.commit(branch)
    file = "%s-%s.%s" % (repo, commit.hexsha, format)

    f = StringIO()
    repository.archive(f, branch, format=format)
    size = f.tell()
    f.seek(0)
    response = CompatibleStreamingHttpResponse(iter(lambda: f.read(STREAM_CHUNK_SIZE), b''),
                                               content_type='application/%s' % format)

    response["Content-Disposition"] = 'attachment; filename="{file}"'.format(file=file)
    response["Content-Type"] = 'application/octet-stream'
    response["Content-Length"] = size
    return response


def branch(request, repo, branch):
    return tree(request, repo, branch)


def repository(request, repo):
    return tree(request, repo)


# Network
def network_data(request, repo, commitishPath, page):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)
    page = int(page)

    commits = []  # Get repository commits
    for commit in repository.iter_commits(branch, paths=path, max_count=COMMITS_PER_PAGE, skip=page * COMMITS_PER_PAGE):
        commit = WrappedCommit(commit)
        commits.append(commit)

    formatted_commits = {}
    if commits:
        for commit in commits:
            formatted_commits[commit.hash] = {
                'hash': commit.hash,
                'parentsHash': [p.hexsha for p in commit.parents],
                'date': commit.authored_date,
                'message': commit.summary,
                'details': reverse('commit', kwargs=dict(repo=repo, commitishPath=commit.hash)),
                'author': {
                    'name': commit.author.name,
                    'email': commit.author.email,
                    'image': 'http://gravatar.com/avatar/{md5}?s=40'.format(md5=md5(commit.author.email.lower()).hexdigest())
                }
            }

        next_page_url = None
        next_page_url = reverse('network_data', kwargs=dict(repo=repo, commitishPath=commitishPath, page=page + 1))

        result = {
            'repo': repo,
            'commitishPath': commitishPath,
            'nextPage': next_page_url,
            'start': commits[0].hash,
            'commits': formatted_commits,
        }
    else:
        result = {
            'repo': repo,
            'commitishPath': commitishPath,
            'nextPage': None,
            'start': None,
            'commits': formatted_commits,
        }
    return HttpResponse(json.dumps(result), content_type='application/json')


def network(request, repo, commitishPath=None):
    repository = get_repository_from_name(repo)
    branch, path = parse_commitish_path(commitishPath, repository)

    return render(request, 'network.html', {
        'page': 'network',
        'repo': repo,
        'branch': branch,
        'commitishPath': commitishPath,
        'breadcrumbs': [{'dir': 'Network', 'path': ''}],
    })

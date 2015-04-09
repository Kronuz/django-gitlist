# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
import re
import git

from django.conf import settings
from django.http import Http404


def get_repository_from_name(repo):
    path = settings.GITLIST_REPOSITORIES.get(repo)
    if not path:
        raise Http404("Repository %s is not configured" % repo)
    path = os.path.expanduser(path)
    try:
        repository = git.Repo(path)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
        raise Http404("Invalid Git Repository: %s" % e)
    return repository


# @brief Return commitish, path parsed from commitishPath, based on
# what's in repo. Raise a 404 if $branchpath does not represent a
# valid branch and path.
#
# A helper for parsing routes that use commit-ish names and paths
# separated by /, since route regexes are not enough to get that right.
#
def parse_commitish_path(commitishPath, repository):
    try:
        slash_position = commitishPath.index('/')
        commitish = commitishPath[:slash_position]
        path = commitishPath[slash_position + 1:]
    except ValueError:
        commitish = commitishPath
        path = ''

    try:
        commit = repository.commit(commitish)
    except git.BadName as e:
        if not path:
            commitish, path = '', commitish
            try:
                commit = repository.commit(commitish)
            except git.BadName as e:
                raise ValueError("%s" % e)
        raise ValueError("%s" % e)

    if not commitish:
        commitish = commit.name_rev.split()[-1]

    return commitish, path


def get_readme(tree):
    for blob in tree.blobs:
        if re.match(r'readme.*', blob.name, re.I):
            return {
                'filename': blob.name,
                'content': blob.data_stream.read,
            }

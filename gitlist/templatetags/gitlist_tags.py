# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import hashlib

from django import template
from django.utils.encoding import force_text
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter
def intformat(value, format):
    return format % value


@register.filter(name='md5')
@stringfilter
def do_md5(value, encoding='utf-8'):
    value = hashlib.md5(value.encode(encoding)).hexdigest()
    return value


@register.assignment_tag(name='join')
def do_join(*args, **kwargs):
    sep = kwargs.pop('sep', " ")
    return sep.join(force_text(a) for a in args)

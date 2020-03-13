# -*- coding: utf8 -*-
import os, subprocess, logging, lxml.html, tempfile, traceback
from StringIO import StringIO
from .common import PreprocError, remove_word_divisions
import docker

logger = logging.getLogger('preprocessing')


def get_formatted_html(filename, window_width = 1000):
    try:
        with tempfile.NamedTemporaryFile(delete = True) as f:
            pdf_fname = f.name
        # subprocess.check_call(['pdf2htmlEX',
        #                        '--fit-width', str(window_width),
        #                        filename,
        #                        os.path.relpath(pdf_fname, os.getcwd())])
        # https://hub.docker.com/r/bwits/pdf2htmlex/
        #src_filepath = os.path.join(settings.MEDIA_ROOT, )
        src_dirpath = os.path.dirname(os.path.join(os.getcwd(), filename))
        volumes = dict()
        volumes[src_dirpath] = {'bind': '/pdf', 'mode': 'rw'}
        justfile = os.path.basename(filename)
        c = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=100)
        ctr = c.containers.run('bwits/pdf2htmlex',
                               command="pdf2htmlEX --fit-width " + str(window_width) + " " + justfile,
                               volumes=volumes,
                               detach=True)
        logs = ctr.logs(stream=True)
        for line in logs:
            print(line)
        ctr.remove();
        pre, ext = os.path.splitext(justfile)
        result_file = os.path.join(src_dirpath, pre + '.html')
        with open(result_file, 'r') as f:
            html_content = f.read().decode('utf8')
        return html_content

        with open(pdf_fname, 'r') as f:
            html_content = f.read().decode('utf8')
        return html_content
    except subprocess.CalledProcessError as err:
        logger.error('pdf2htmlEX failed to convert "%s" because of %s\n%s' % (filename, err, traceback.format_exc()))
        raise PreprocError()
    finally:
        if pdf_fname and os.path.exists(pdf_fname):
            os.remove(pdf_fname)


_BLOCK_TAGS = frozenset(['div'])
def get_node_text(node):
    children_text = u''.join(map(get_node_text, node))
    fmt = ' %s%s\n%s' if node.tag.lower() in _BLOCK_TAGS else '%s%s%s'
    return fmt % (node.text or '', children_text, node.tail or '')


def get_plain_text(formatted_html):
    tree = lxml.html.parse(StringIO(formatted_html))
    line_nodes = tree.xpath('/html/body/div[@id="page-container"]/div/div/div')
    plain_text = ''.join(map(get_node_text, line_nodes))
#     with open('/tmp/11111111.txt', 'w') as f:
#         f.write(plain_text.encode('utf8'))
    return remove_word_divisions(plain_text)


def parse(filename, window_width = 1000):
    formatted_html = get_formatted_html(filename, window_width)
    return formatted_html, get_plain_text(formatted_html)

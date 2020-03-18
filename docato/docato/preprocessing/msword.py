# -*- coding: utf8 -*-
import subprocess, pdf, tempfile, logging, html, os
from django.conf import settings
import docker

logger = logging.getLogger('preprocessing')

def parse(filename, window_width = 1000):
    try:
        with tempfile.NamedTemporaryFile(delete = False) as f:
            tmp_fname = f.name
            #subprocess.check_call([settings.TIKA_PREFIX + 'tika', '--encoding=utf-8', '--html', filename],  #old Todo remove
            #                      stdout = f)
            #
            src_dirpath = os.path.dirname(os.path.join(os.getcwd(), filename))
            volumes = []
            volumes.append( src_dirpath+':/uploads' )
            volumes.append( src_dirpath+':/out' )
            justfile = os.path.basename(filename)
            # https://hub.docker.com/r/aslubsky/docker-unoconv/
            c = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=100)
            ctr = c.containers.run('aslubsky/docker-unoconv',
                                   command='/bin/bash -c  "unoconv --listener & sleep 10 && unoconv -v -f pdf  -o /out    /uploads/'+justfile+'"',
                                   volumes=volumes,
                                   detach=True)
            logs = ctr.logs(stream=True)
            for line in logs:
                print(line)
            ctr.remove();
            #
            pre, ext = os.path.splitext(justfile)
            result_file = os.path.join(src_dirpath, pre + '.pdf')
            return pdf.parse(result_file, window_width)
    except Exception as err:
        logger.warning('Could not convert MSOffice file "%s" using tika because of %s, trying unoconv...' % (filename, err))
        try:
            subprocess.check_call(['unoconv', '-fpdf', '-o', tmp_fname, filename])
            return pdf.parse(tmp_fname, window_width)
        except subprocess.CalledProcessError as err:
            logger.error('Could not convert MSOffice file "%s" using unoconv because of %s' % (filename, err))
            raise PreprocError()
    finally:
        if tmp_fname and os.path.exists(tmp_fname):
            os.remove(tmp_fname)

# -*- coding: utf8 -*-
import tempfile, os, logging, shutil, subprocess, traceback
import pdf
from BeautifulSoup import UnicodeDammit
import docker

logger = logging.getLogger('preprocessing')


def parse(filename, window_width = 1000):
    logger.info('Got HTML to parse: %s' % filename)
    try:
        # with tempfile.NamedTemporaryFile(suffix = '.html', delete = False) as f: # todo clean this old code
        #     copy_fname = f.name
        # with tempfile.NamedTemporaryFile(delete = False) as f:
        #     conv_fname = f.name
        # shutil.copy2(filename, copy_fname)
        # # try to determine encoding and decode
        # with open(copy_fname, 'rb') as f:
        #     converted = UnicodeDammit(f.read(), isHTML = True)
        # if converted.unicode:
        #     with open(copy_fname, 'wb') as f:
        #         f.write(converted.unicode.encode('utf8'))
        # args = ['wkhtmltopdf', '--encoding', 'utf-8', copy_fname, conv_fname]
        # env = { 'DISPLAY' : ':99' }
        # logger.debug('Calling wkhtmltopdf with arguments %r' % args)
        # subprocess.check_call(args, env = env)
        # logger.debug('Wkhtmltopdf has done the job')
        #
        # docker run -it --rm -v /home/mp/Загрузки/:/pdf openlabs/docker-wkhtmltopdf "/pdf/asvfsd.html"  "/pdf/Twist Help.pdf"
        src_dirpath = os.path.dirname(os.path.join(os.getcwd(), filename))
        volumes = []
        volumes.append( src_dirpath+':/pdf' )
        justfile = os.path.basename(filename)
        c = docker.DockerClient(base_url='unix://var/run/docker.sock', timeout=100)
        ctr = c.containers.run('openlabs/docker-wkhtmltopdf',
                               command='"/pdf/'+justfile+'"   "/pdf/'+justfile+'.pdf"',
                               volumes=volumes,
                               detach=True)
        logs = ctr.logs(stream=True)
        for line in logs:
            print(line)
        ctr.remove();
        #
        logger.debug('Wkhtmltopdf has done the job')
        result_file = os.path.join(src_dirpath, justfile + '.pdf')
        return pdf.parse(result_file, window_width)
    except Exception as err:
        logger.error('wkhtmltopdf failed to convert "%s" because of %s\n%s' % (filename, err, traceback.format_exc()))
        raise PreprocError()
    finally:
        # if copy_fname and os.path.exists(copy_fname):
        #     os.remove(copy_fname)
        # if conv_fname and os.path.exists(conv_fname):
        #     os.remove(conv_fname)
        pass

import subprocess
PATH_FOR_ZIP_DISCUSSION_ARCHIVE = ''


def wget_whole_page(MEDIA_DIR, slug,url):
	command = ' wget -E -H -k -K -p -P {0} "{1}"'.format(slug, url)
	print('run $ {0} # in dir={1}'.format(command, MEDIA_DIR))
	process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, cwd=MEDIA_DIR)
	process.wait()
